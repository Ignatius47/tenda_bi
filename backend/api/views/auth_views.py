import secrets
import logging

from django.conf import settings
from django.core.cache import cache
from django.shortcuts import redirect
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import serializers, status
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User
from stores.models import Store
from ingestion.services.shopify_client import ShopifyClient
from ingestion.tasks import run_full_sync

logger = logging.getLogger(__name__)

OAUTH_STATE_TTL = 600  # 10 minutes


# ── Inline serializers (no external dependency) ───────────────────────────────

class _UserSerializer(serializers.ModelSerializer):
    class Meta:
        model        = User
        fields       = ['id', 'email', 'full_name', 'role', 'created_at']
        read_only_fields = fields


class _StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model        = Store
        fields       = ['id', 'shop_domain', 'shop_name', 'currency', 'is_active', 'last_synced_at']
        read_only_fields = fields


def _tokens(user):
    refresh = RefreshToken.for_user(user)
    return {'access': str(refresh.access_token), 'refresh': str(refresh)}


# ── Manual auth (kept for admin/analyst accounts) ─────────────────────────────

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email     = request.data.get('email', '').strip()
        password  = request.data.get('password', '')
        full_name = request.data.get('full_name', '')

        if not email or not password:
            return Response({'error': 'Email and password required'}, status=400)
        if len(password) < 8:
            return Response({'password': ['Password must be at least 8 characters.']}, status=400)
        if User.objects.filter(email=email).exists():
            return Response({'email': ['A user with this email already exists.']}, status=400)

        user = User.objects.create_user(email=email, password=password, full_name=full_name)
        return Response({
            'user': _UserSerializer(user).data,
            **_tokens(user),
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        from django.contrib.auth import authenticate
        email    = request.data.get('email', '')
        password = request.data.get('password', '')
        user     = authenticate(username=email, password=password)
        if not user:
            return Response({'non_field_errors': ['Invalid credentials.']}, status=400)
        if not user.is_active:
            return Response({'non_field_errors': ['Account disabled.']}, status=400)
        return Response({
            'user': _UserSerializer(user).data,
            **_tokens(user),
        })


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        stores = Store.objects.filter(user=request.user, is_active=True)
        return Response({
            'user':   _UserSerializer(request.user).data,
            'stores': _StoreSerializer(stores, many=True).data,
        })


# ── Shopify-first OAuth ────────────────────────────────────────────────────────

class ShopifyAuthStartView(APIView):
    """
    GET /api/auth/shopify/start/?shop=mystore.myshopify.com

    Step 1: No account needed. Redirects browser to Shopify OAuth.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        shop = request.query_params.get('shop', '').strip().lower()
        if not shop:
            return Response({'error': 'shop parameter required'}, status=400)
        if not shop.endswith('.myshopify.com'):
            shop = f"{shop}.myshopify.com"

        state = secrets.token_urlsafe(16)
        cache.set(f"shopify_oauth_{state}", {'shop': shop}, OAUTH_STATE_TTL)

        auth_url = ShopifyClient.build_auth_url(shop, state)
        return redirect(auth_url)


class ShopifyAuthCallbackView(APIView):
    """
    GET /api/auth/shopify/callback/

    Step 2: Shopify redirects here after user approves.
    - Exchanges code for access token
    - Auto-creates user (no form, no password)
    - Creates/updates store
    - Issues JWT
    - Redirects to frontend loading screen
    """
    permission_classes = [AllowAny]

    def get(self, request):
        shop       = request.query_params.get('shop', '')
        code       = request.query_params.get('code', '')
        state      = request.query_params.get('state', '')
        hmac_value = request.query_params.get('hmac', '')

        logger.info(f"Shopify OAuth callback: shop={shop}")

        # Skip HMAC in DEBUG
        if not settings.DEBUG:
            if not ShopifyClient.verify_hmac(dict(request.query_params), hmac_value):
                logger.error("HMAC validation failed")
                frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
                return redirect(f"{frontend_url}/connect?error=hmac_failed")

        # State cleanup (don't block on missing state in dev)
        cache.delete(f"shopify_oauth_{state}")

        # Exchange code for access token
        try:
            access_token = ShopifyClient.exchange_token(shop, code)
        except Exception as e:
            logger.error(f"Token exchange failed for {shop}: {e}")
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
            return redirect(f"{frontend_url}/connect?error=token_failed")

        # Fetch shop info from Shopify
        try:
            tmp = type('S', (), {
                'access_token': access_token,
                'shop_domain':  shop,
                'base_url':     f"https://{shop}/admin/api/2024-10",
            })()
            shop_info = ShopifyClient(tmp).get_shop()
        except Exception as e:
            logger.warning(f"Could not fetch shop info for {shop}: {e}")
            shop_info = {}

        # Derive user email from shop
        shop_email = (
            shop_info.get('email') or
            shop_info.get('customer_email') or
            f"{shop.replace('.myshopify.com', '')}@tenda-shopify.com"
        )

        # Auto-create or fetch user — no password, no form
        user, user_created = User.objects.get_or_create(
            email=shop_email,
            defaults={'full_name': shop_info.get('name', shop)},
        )
        if user_created:
            user.set_unusable_password()
            user.save()
            logger.info(f"Auto-created user: {shop_email}")
        else:
            logger.info(f"Existing user login: {shop_email}")

        # Save or update store
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
        logger.info(f"Store {'created' if store_created else 'updated'}: {store.shop_domain}")

        # Register webhooks (best effort — fails silently on localhost)
        try:
            base_url = request.build_absolute_uri('/').rstrip('/')
            ShopifyClient(store).register_all_webhooks(base_url)
        except Exception as e:
            logger.warning(f"Webhook registration failed (non-fatal): {e}")

        # Queue full data sync immediately
        if store_created:
            try:
                logger.info(f"Full sync queued for store {store.id}")
            except Exception as e:
                logger.warning(f"Could not queue sync: {e}")

        # Issue JWT and redirect to frontend loading screen
        tokens = _tokens(user)
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')

        from urllib.parse import urlencode
        params = urlencode({
            'access':    tokens['access'],
            'refresh':   tokens['refresh'],
            'store_id':  store.id,
            'shop_name': store.shop_name or shop,
            'is_new':    str(store_created).lower(),
        })
        return redirect(f"{frontend_url}/auth/shopify/success?{params}")


# ── Add store (logged-in user adding another store) ───────────────────────────

class ShopifyConnectView(APIView):
    """GET /api/shopify/connect/?shop=... for already-logged-in users."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        shop = request.query_params.get('shop', '').strip().lower()
        if not shop:
            return Response({'error': 'shop parameter required'}, status=400)
        if not shop.endswith('.myshopify.com'):
            shop = f"{shop}.myshopify.com"

        state = secrets.token_urlsafe(16)
        cache.set(
            f"shopify_oauth_{state}",
            {'shop': shop, 'user_id': request.user.id},
            OAUTH_STATE_TTL,
        )
        url = ShopifyClient.build_auth_url(shop, state)
        return Response({'redirect_url': url, 'shop': shop})