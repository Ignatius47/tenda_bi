from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from stores.models import Store
from analytics.models import InventoryMetric
from warehouse.models import Product, ProductVariant
from api.permissions import IsStoreOwner
from api.serializers.analytics_serializers import InventoryMetricSerializer


class InventoryOverviewView(APIView):
    """
    GET /api/inventory/{store_id}/
    Returns inventory health metrics for all variants.
    Reads from the precomputed analytics_inventory_metrics table.
    """
    permission_classes = [IsAuthenticated, IsStoreOwner]

    def get(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id, user=request.user, is_active=True)
        except Store.DoesNotExist:
            return Response({'error': 'Store not found'}, status=404)

        status_filter = request.query_params.get('status')
        qs = InventoryMetric.objects.filter(store=store)
        if status_filter:
            qs = qs.filter(status=status_filter)

        # Sort: critical first, then low, then dead stock, then ok
        STATUS_ORDER = {
            InventoryMetric.STATUS_CRITICAL: 0,
            InventoryMetric.STATUS_LOW: 1,
            InventoryMetric.STATUS_DEAD: 2,
            InventoryMetric.STATUS_OK: 3,
        }
        items = sorted(qs, key=lambda x: STATUS_ORDER.get(x.status, 99))

        summary = {
            'total_skus': qs.count(),
            'critical_count': qs.filter(status=InventoryMetric.STATUS_CRITICAL).count(),
            'low_count': qs.filter(status=InventoryMetric.STATUS_LOW).count(),
            'dead_stock_count': qs.filter(status=InventoryMetric.STATUS_DEAD).count(),
            'healthy_count': qs.filter(status=InventoryMetric.STATUS_OK).count(),
            # Live warehouse counts (not dependent on analytics summaries)
            'total_products_live': Product.objects.filter(store=store, status='active').count(),
            'total_variants_live': ProductVariant.objects.filter(product__store=store, product__status='active').count(),
        }

        # Average stock cover (exclude infinite)
        valid = [i.days_cover for i in items if i.days_cover < 999]
        summary['avg_days_cover'] = round(sum(valid) / len(valid), 1) if valid else 0

        return Response({
            'summary': summary,
            'items': InventoryMetricSerializer(items, many=True).data,
        })
