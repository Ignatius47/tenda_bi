from datetime import date, timedelta
from decimal import Decimal

from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from stores.models import Store
from analytics.models import (
    KPISnapshot, DailyRevenue, ProductSalesSummary,
    CategoryRevenueSummary, LocationRevenueSummary,
)
from insights.models import Alert, Insight
from warehouse.models import Product, OrderItem, Order
from api.permissions import IsStoreOwner
from api.serializers.analytics_serializers import (
    KPISnapshotSerializer, DailyRevenueSerializer,
    ProductSalesSerializer, CategoryRevenueSerializer,
    LocationRevenueSerializer, AlertSerializer, InsightSerializer,
)

CACHE_TTL = 300  # 5 minutes


def _get_store_or_404(store_id, user):
    try:
        return Store.objects.get(id=store_id, user=user, is_active=True)
    except Store.DoesNotExist:
        return None


class DashboardKPIView(APIView):
    """
    GET /api/dashboard/{store_id}/kpis/
    Returns precomputed KPI snapshot. Sub-millisecond after first compute.
    """
    permission_classes = [IsAuthenticated, IsStoreOwner]

    def get(self, request, store_id):
        store = _get_store_or_404(store_id, request.user)
        if not store:
            return Response({'error': 'Store not found'}, status=404)

        cache_key = f"kpis:{store_id}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        try:
            kpi = KPISnapshot.objects.get(store=store)
            data = KPISnapshotSerializer(kpi).data
        except KPISnapshot.DoesNotExist:
            # No snapshot yet — trigger calculation and return empty
            from analytics.tasks import calculate_kpi_snapshot
            calculate_kpi_snapshot.delay(store_id)
            data = {
                'revenue_30d': 0, 'revenue_change_pct': 0,
                'profit_30d': 0, 'profit_change_pct': 0,
                'orders_30d': 0, 'orders_change_pct': 0,
                'aov_30d': 0, 'aov_change_pct': 0,
                'total_customers': 0, 'repeat_purchase_rate': 0,
            }

        cache.set(cache_key, data, CACHE_TTL)
        return Response(data)


class RevenueTrendView(APIView):
    """
    GET /api/dashboard/{store_id}/revenue-trend/?days=30
    Returns daily revenue + profit data for the trend chart.
    """
    permission_classes = [IsAuthenticated, IsStoreOwner]

    def get(self, request, store_id):
        store = _get_store_or_404(store_id, request.user)
        if not store:
            return Response({'error': 'Store not found'}, status=404)

        days = min(int(request.query_params.get('days', 30)), 365)
        since = date.today() - timedelta(days=days)

        cache_key = f"revenue_trend:{store_id}:{days}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        qs = (
            DailyRevenue.objects
            .filter(store=store, date__gte=since)
            .order_by('date')
        )
        data = DailyRevenueSerializer(qs, many=True).data
        cache.set(cache_key, data, CACHE_TTL)
        return Response(data)


class TopProductsView(APIView):
    """
    GET /api/dashboard/{store_id}/top-products/?days=30&limit=10
    Returns top products by revenue for the current period.
    """
    permission_classes = [IsAuthenticated, IsStoreOwner]

    def get(self, request, store_id):
        store = _get_store_or_404(store_id, request.user)
        if not store:
            return Response({'error': 'Store not found'}, status=404)

        days = min(int(request.query_params.get('days', 30)), 365)
        limit = min(int(request.query_params.get('limit', 10)), 100)
        period_start = date.today() - timedelta(days=days)

        cache_key = f"top_products:{store_id}:{days}:{limit}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        # Current period (precomputed)
        current = list(
            ProductSalesSummary.objects
            .filter(store=store, period_start=period_start)
            .select_related('product')
            .order_by('-total_revenue')[:limit]
        )

        # Fallback: build directly from warehouse tables if summaries are not ready yet.
        if not current:
            paid_items = (
                OrderItem.objects
                .filter(
                    order__store=store,
                    order__financial_status=Order.STATUS_PAID,
                    order__cancelled_at__isnull=True,
                    order__processed_at__date__gte=period_start,
                    product__isnull=False,
                )
                .values('product_id')
                .annotate(
                    total_revenue=Sum('line_total'),
                    units_sold=Sum('quantity'),
                )
                .order_by('-total_revenue')[:limit]
            )
            product_map = {
                p.id: p for p in Product.objects.filter(
                    store=store,
                    id__in=[row['product_id'] for row in paid_items],
                )
            }
            dynamic_rows = []
            for row in paid_items:
                product = product_map.get(row['product_id'])
                if not product:
                    continue
                dynamic_rows.append({
                    'product_id': product.id,
                    'title': product.title,
                    'category': product.product_type or 'Uncategorized',
                    'total_revenue': row['total_revenue'] or Decimal('0'),
                    'total_profit': Decimal('0'),
                    'units_sold': row['units_sold'] or 0,
                    'margin_pct': 0.0,
                    'trend_pct': 0.0,
                })
            cache.set(cache_key, dynamic_rows, CACHE_TTL)
            return Response(dynamic_rows)

        # Previous period for trend
        prev_start = period_start - timedelta(days=days)
        previous = {
            p.product_id: p.total_revenue
            for p in ProductSalesSummary.objects.filter(
                store=store, period_start=prev_start,
            )
        }

        results = []
        for item in current:
            prev_rev = float(previous.get(item.product_id, 0))
            cur_rev = float(item.total_revenue)
            trend_pct = ((cur_rev - prev_rev) / prev_rev * 100) if prev_rev > 0 else 0.0
            item.trend_pct = round(trend_pct, 1)
            results.append(item)

        data = ProductSalesSerializer(results, many=True).data
        cache.set(cache_key, data, CACHE_TTL)
        return Response(data)


class CategoryRevenueView(APIView):
    """
    GET /api/dashboard/{store_id}/category-revenue/?days=30
    """
    permission_classes = [IsAuthenticated, IsStoreOwner]

    def get(self, request, store_id):
        store = _get_store_or_404(store_id, request.user)
        if not store:
            return Response({'error': 'Store not found'}, status=404)

        days = min(int(request.query_params.get('days', 30)), 365)
        period_start = date.today() - timedelta(days=days)

        cache_key = f"cat_revenue:{store_id}:{days}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        qs = (
            CategoryRevenueSummary.objects
            .filter(store=store, period_start=period_start)
            .order_by('-total_revenue')
        )
        data = CategoryRevenueSerializer(qs, many=True).data
        cache.set(cache_key, data, CACHE_TTL)
        return Response(data)


class LocationRevenueView(APIView):
    """
    GET /api/dashboard/{store_id}/location-revenue/?days=30
    """
    permission_classes = [IsAuthenticated, IsStoreOwner]

    def get(self, request, store_id):
        store = _get_store_or_404(store_id, request.user)
        if not store:
            return Response({'error': 'Store not found'}, status=404)

        days = min(int(request.query_params.get('days', 30)), 365)
        period_start = date.today() - timedelta(days=days)

        cache_key = f"loc_revenue:{store_id}:{days}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        qs = (
            LocationRevenueSummary.objects
            .filter(store=store, period_start=period_start)
            .order_by('-total_revenue')
        )
        data = LocationRevenueSerializer(qs, many=True).data
        cache.set(cache_key, data, CACHE_TTL)
        return Response(data)


class InsightsView(APIView):
    """
    GET /api/dashboard/{store_id}/insights/
    Returns natural language insights for the dashboard panel.
    """
    permission_classes = [IsAuthenticated, IsStoreOwner]

    def get(self, request, store_id):
        store = _get_store_or_404(store_id, request.user)
        if not store:
            return Response({'error': 'Store not found'}, status=404)

        qs = Insight.objects.filter(store=store).order_by('-created_at')[:10]
        return Response(InsightSerializer(qs, many=True).data)
