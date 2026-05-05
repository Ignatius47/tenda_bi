import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from stores.models import Store
from ingestion.tasks import run_incremental_sync, run_full_sync
from api.serializers.all_serializers import StoreSerializer, SyncLogSerializer
from raw_data.models import SyncLog

logger = logging.getLogger(__name__)


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

        from ingestion.tasks import handle_order_webhook, handle_product_webhook, handle_inventory_webhook
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
