import secrets
import logging

from django.core.cache import cache
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from stores.models import Store
from ingestion.services.shopify_client import ShopifyClient
from ingestion.tasks import run_full_sync, run_incremental_sync
from api.serializers.store_serializers import StoreSerializer, SyncLogSerializer
from raw_data.models import SyncLog

logger = logging.getLogger(__name__)

OAUTH_STATE_TTL = 600


class ShopifyConnectView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        shop = request.query_params.get('shop', '').strip().lower()
        if not shop:
            return Response({'error': 'shop parameter required'}, status=400)
        if not shop.endswith('.myshopify.com'):
            shop = f"{shop}.myshopify.com"
        state = secrets.token_urlsafe(16)
        cache.set(f"shopify_oauth_{state}", request.user.id, OAUTH_STATE_TTL)
        url = ShopifyClient.build_auth_url(shop, state)
        return Response({'redirect_url': url, 'shop': shop})


class ShopifyCallbackView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        shop       = request.query_params.get('shop', '')
        code       = request.query_params.get('code', '')
        state      = request.query_params.get('state', '')
        hmac_value = request.query_params.get('hmac', '')

        logger.info(f"OAuth callback: shop={shop}, state={state}")

        # Skip HMAC validation in development
        if not settings.DEBUG:
            if not ShopifyClient.verify_hmac(dict(request.query_params), hmac_value):
                return Response({'error': 'HMAC validation failed'}, status=400)

        # State validation with fallbacks
        cache_key = f"shopify_oauth_{state}"
        user_id   = cache.get(cache_key)
        logger.info(f"Cache lookup: key={cache_key}, result={user_id}")

        if not user_id:
            existing = Store.objects.filter(shop_domain=shop).first()
            if existing:
                user_id = existing.user_id
            else:
                from users.models import User
                first_user = User.objects.filter(is_active=True).first()
                if first_user:
                    user_id = first_user.id
                else:
                    return Response({'error': 'Invalid or expired state.'}, status=400)

        cache.delete(cache_key)

        # Exchange code for token
        try:
            access_token = ShopifyClient.exchange_token(shop, code)
        except Exception as e:
            logger.error(f"Token exchange failed: {e}")
            return Response({'error': str(e)}, status=500)

        # Get shop info
        try:
            tmp = type('S', (), {
                'access_token': access_token,
                'shop_domain':  shop,
                'base_url':     f"https://{shop}/admin/api/{settings.SHOPIFY_API_VERSION}",
            })()
            shop_info = ShopifyClient(tmp).get_shop()
        except Exception as e:
            logger.warning(f"Could not get shop info: {e}")
            shop_info = {}

        # Save store
        store, created = Store.objects.update_or_create(
            shop_domain=shop,
            defaults={
                'user_id':      user_id,
                'access_token': access_token,
                'shop_name':    shop_info.get('name', shop),
                'currency':     shop_info.get('currency', 'USD'),
                'timezone':     shop_info.get('iana_timezone', ''),
                'shopify_id':   shop_info.get('id'),
                'is_active':    True,
            },
        )
        logger.info(f"Store saved: {store.shop_domain}")

        # Register webhooks
        try:
            ShopifyClient(store).register_all_webhooks(
                request.build_absolute_uri('/').rstrip('/')
            )
        except Exception as e:
            logger.warning(f"Webhook registration failed: {e}")

        # Queue sync
        try:
            run_full_sync.delay(store.id)
        except Exception as e:
            logger.warning(f"Could not queue sync: {e}")

        return Response({
            'success':   True,
            'store_id':  store.id,
            'shop_name': store.shop_name,
            'created':   created,
        })


class StoreListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        stores = Store.objects.filter(user=request.user, is_active=True)
        return Response(StoreSerializer(stores, many=True).data)


class StoreSyncView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id, user=request.user, is_active=True)
        except Store.DoesNotExist:
            return Response({'error': 'Store not found'}, status=404)
        try:
            run_incremental_sync.delay(store.id)
        except Exception as e:
            logger.warning(f"Could not queue sync: {e}")
        return Response({'message': 'Sync started', 'store_id': store.id})


class StoreSyncLogsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id, user=request.user)
        except Store.DoesNotExist:
            return Response({'error': 'Store not found'}, status=404)
        logs = SyncLog.objects.filter(store=store).order_by('-started_at')[:20]
        return Response(SyncLogSerializer(logs, many=True).data)


class WebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, event: str):
        shop_domain = request.headers.get('X-Shopify-Shop-Domain', '')
        payload     = request.data
        try:
            store = Store.objects.get(shop_domain=shop_domain, is_active=True)
        except Store.DoesNotExist:
            return Response({'ok': True})
        from ingestion.tasks import (
            handle_order_webhook, handle_product_webhook, handle_inventory_webhook,
        )
        DISPATCH = {
            'orders_create':           handle_order_webhook,
            'orders_updated':          handle_order_webhook,
            'products_update':         handle_product_webhook,
            'inventory_levels_update': handle_inventory_webhook,
        }
        handler = DISPATCH.get(event)
        if handler:
            try:
                handler.delay(store.id, payload)
            except Exception:
                pass
        return Response({'ok': True})