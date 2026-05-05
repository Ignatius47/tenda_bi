import secrets
import logging

from django.conf import settings
from django.core.cache import cache
from django.shortcuts import redirect
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User
from stores.models import Store
from ingestion.services.shopify_client import ShopifyClient
from ingestion.tasks import run_full_sync
from api.serializers.all_serializers import (
    RegisterSerializer, LoginSerializer, UserSerializer, StoreSerializer,
)

logger = logging.getLogger(__name__)

OAUTH_STATE_TTL = 600  # 10 min


def _tokens(user):
    refresh = RefreshToken.for_user(user)
    return {'access': str(refresh.access_token), 'refresh': str(refresh)}


def _shopify_oauth_config_error():
    missing = []
    if not settings.SHOPIFY_API_KEY:
        missing.append('SHOPIFY_API_KEY')
    if not settings.SHOPIFY_API_SECRET:
        missing.append('SHOPIFY_API_SECRET')
    if not settings.SHOPIFY_REDIRECT_URI:
        missing.append('SHOPIFY_REDIRECT_URI')
    if not missing:
        return None
    return f"Missing Shopify config: {', '.join(missing)}"


# ── Manual auth (optional — for admin/analyst accounts) ───────────────────────

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        s = RegisterSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = s.save()
        return Response({
            'user': UserSerializer(user).data,
            **_tokens(user),
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        s = LoginSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = s.validated_data['user']
        return Response({
            'user': UserSerializer(user).data,
            **_tokens(user),
        })


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        stores = Store.objects.filter(user=request.user, is_active=True)
        return Response({
            'user':   UserSerializer(request.user).data,
            'stores': StoreSerializer(stores, many=True).data,
        })


# ── Shopify-first OAuth ────────────────────────────────────────────────────────

class ShopifyAuthStartView(APIView):
    """
    GET /api/auth/shopify/start/?shop=mystore.myshopify.com
    Step 1: Redirect user to Shopify OAuth.
    No account needed — Shopify is the identity provider.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        cfg_error = _shopify_oauth_config_error()
        if cfg_error:
            return Response({'error': cfg_error}, status=500)

        shop = request.query_params.get('shop', '').strip().lower()
        if not shop:
            return Response({'error': 'shop parameter required'}, status=400)
        if not shop.endswith('.myshopify.com'):
            shop = f"{shop}.myshopify.com"

        state = secrets.token_urlsafe(16)
        cache.set(f"shopify_oauth_{state}", {'shop': shop}, OAUTH_STATE_TTL)

        url = ShopifyClient.build_auth_url(shop, state)
        accepts_json = 'application/json' in request.headers.get('Accept', '')
        if accepts_json:
            return Response({'redirect_url': url, 'shop': shop})
        return redirect(url)


class ShopifyAuthCallbackView(APIView):
    """
    GET /api/auth/shopify/callback/
    Step 2: Exchange code → token → create/fetch user+store → return JWT.
    User is NEVER asked to fill a form. Account created automatically.
    After login, full data sync starts immediately.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        shop       = request.query_params.get('shop', '')
        code       = request.query_params.get('code', '')
        state      = request.query_params.get('state', '')
        hmac_value = request.query_params.get('hmac', '')

        logger.info(f"Shopify OAuth callback: shop={shop}")

        # HMAC validation (skip in DEBUG)
        if not settings.DEBUG:
            if not ShopifyClient.verify_hmac(dict(request.query_params), hmac_value):
                return Response({'error': 'HMAC validation failed'}, status=400)

        # State validation
        cached = cache.get(f"shopify_oauth_{state}")
        cache.delete(f"shopify_oauth_{state}")

        # Exchange code for token
        try:
            access_token = ShopifyClient.exchange_token(shop, code)
        except Exception as e:
            logger.error(f"Token exchange failed: {e}")
            return Response({'error': 'Token exchange failed'}, status=500)

        # Get shop info from Shopify
        try:
            tmp = type('S', (), {
                'access_token': access_token,
                'shop_domain':  shop,
                'base_url':     f"https://{shop}/admin/api/2024-10",
            })()
            shop_info = ShopifyClient(tmp).get_shop()
        except Exception as e:
            logger.warning(f"Could not get shop info: {e}")
            shop_info = {}

        shop_email = shop_info.get('email') or f"{shop.replace('.myshopify.com', '')}@tenda-store.com"

        # Create or fetch user — auto-created, no password needed
        user, user_created = User.objects.get_or_create(
            email=shop_email,
            defaults={
                'full_name':    shop_info.get('name', shop),
                'shopify_auth': True,
            }
        )
        if user_created:
            user.set_unusable_password()
            user.save()
            logger.info(f"Auto-created user for {shop}: {shop_email}")

        # Create or update store
        store, store_created = Store.objects.update_or_create(
            shop_domain=shop,
            defaults={
                'user_id':      user.id,
                'access_token': access_token,
                'shop_name':    shop_info.get('name', shop),
                'currency':     shop_info.get('currency', 'USD'),
                'timezone':     shop_info.get('iana_timezone', ''),
                'shopify_id':   shop_info.get('id'),
                'is_active':    True,
            },
        )

        # Register webhooks (best effort)
        try:
            base_url = request.build_absolute_uri('/').rstrip('/')
            ShopifyClient(store).register_all_webhooks(base_url)
        except Exception as e:
            logger.warning(f"Webhook registration failed: {e}")

        # Kick off immediate data sync
        try:
            run_full_sync.delay(store.id)
            logger.info(f"Full sync queued for store {store.id}")
        except Exception as e:
            logger.warning(f"Could not queue sync: {e}")

        # Issue JWT tokens
        tokens = _tokens(user)

        # Redirect frontend with token — frontend reads token from URL and stores it
        frontend_url = settings.FRONTEND_URL
        redirect_url = (
            f"{frontend_url}/auth/shopify/success"
            f"?access={tokens['access']}"
            f"&refresh={tokens['refresh']}"
            f"&store_id={store.id}"
            f"&shop_name={store.shop_name}"
            f"&is_new={str(store_created).lower()}"
        )

        return redirect(redirect_url)


class ShopifyConnectView(APIView):
    """
    GET /api/shopify/connect/?shop=... (authenticated — add additional store)
    For users who are already logged in and want to add another store.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cfg_error = _shopify_oauth_config_error()
        if cfg_error:
            return Response({'error': cfg_error}, status=500)

        shop = request.query_params.get('shop', '').strip().lower()
        if not shop:
            return Response({'error': 'shop parameter required'}, status=400)
        if not shop.endswith('.myshopify.com'):
            shop = f"{shop}.myshopify.com"

        state = secrets.token_urlsafe(16)
        cache.set(f"shopify_oauth_{state}", {'shop': shop, 'user_id': request.user.id}, OAUTH_STATE_TTL)

        url = ShopifyClient.build_auth_url(shop, state)
        return Response({'redirect_url': url, 'shop': shop})
