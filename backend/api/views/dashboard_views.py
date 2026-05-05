from datetime import date, timedelta

from django.core.cache import cache
from django.db.models import Max
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from stores.models import Store
from analytics.models import (
    KPISnapshot, DailyRevenue, ProductSalesSummary,
    CategoryRevenueSummary, LocationRevenueSummary,
)
from insights.models import Alert, Insight
from api.serializers.all_serializers import (
    KPISnapshotSerializer, DailyRevenueSerializer, ProductSalesSerializer,
    CategoryRevenueSerializer, LocationRevenueSerializer,
    AlertSerializer, InsightSerializer,
)

CACHE_TTL = 300  # 5 minutes


def _get_store(store_id, user):
    try:
        return Store.objects.get(id=store_id, user=user, is_active=True)
    except Store.DoesNotExist:
        return None


def _latest_product_period(store):
    return (
        ProductSalesSummary.objects
        .filter(store=store)
        .aggregate(latest=Max('period_start'))
        .get('latest')
    )


class DashboardSummaryView(APIView):
    """
    GET /api/dashboard/{store_id}/summary/
    Returns everything the dashboard needs in one request.
    Mobile-optimised: single call, cached 5 min.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, store_id):
        store = _get_store(store_id, request.user)
        if not store:
            return Response({'error': 'Store not found'}, status=404)

        days = int(request.query_params.get('days', 30))
        cache_key = f"dash_summary:{store_id}:{days}"
        cached    = cache.get(cache_key)
        if cached:
            return Response(cached)

        period_start = date.today() - timedelta(days=days)

        # KPIs
        try:
            kpi  = KPISnapshot.objects.get(store=store)
            kpis = KPISnapshotSerializer(kpi).data
        except KPISnapshot.DoesNotExist:
            from analytics.tasks import calculate_kpi_snapshot
            calculate_kpi_snapshot.delay(store_id)
            kpis = {}

        # Revenue trend
        trend = DailyRevenue.objects.filter(store=store, date__gte=period_start).order_by('date')
        trend_data = DailyRevenueSerializer(trend, many=True).data

        # Top products (with trend)
        latest_period = _latest_product_period(store)
        current = (
            ProductSalesSummary.objects
            .filter(store=store, period_start=latest_period)
            .select_related('product')
            .order_by('-total_revenue')[:10]
        ) if latest_period else []
        prev_period = (
            ProductSalesSummary.objects
            .filter(store=store, period_start__lt=latest_period)
            .aggregate(prev=Max('period_start'))
            .get('prev')
        ) if latest_period else None
        prev_map = {
            p.product_id: float(p.total_revenue)
            for p in ProductSalesSummary.objects.filter(store=store, period_start=prev_period)
        } if prev_period else {}
        products_data = []
        for item in current:
            prev_rev  = prev_map.get(item.product_id, 0)
            cur_rev   = float(item.total_revenue)
            item.trend_pct = round(((cur_rev - prev_rev) / prev_rev * 100) if prev_rev > 0 else 0, 1)
            products_data.append(ProductSalesSerializer(item).data)

        # Categories
        categories = CategoryRevenueSummary.objects.filter(
            store=store, period_start=period_start
        ).order_by('-total_revenue')
        categories_data = CategoryRevenueSerializer(categories, many=True).data

        # Locations
        locations = LocationRevenueSummary.objects.filter(
            store=store, period_start=period_start
        ).order_by('-total_revenue')
        locations_data = LocationRevenueSerializer(locations, many=True).data

        # Insights
        insights      = Insight.objects.filter(store=store).order_by('-created_at')[:8]
        insights_data = InsightSerializer(insights, many=True).data

        # Active alerts (summary counts)
        alerts_qs     = Alert.objects.filter(store=store, is_resolved=False)
        alert_summary = {
            'total':         alerts_qs.count(),
            'critical':      alerts_qs.filter(severity='critical').count(),
            'warning':       alerts_qs.filter(severity='warning').count(),
            'opportunities': alerts_qs.filter(severity='success').count(),
        }

        data = {
            'kpis':       kpis,
            'trend':      trend_data,
            'products':   products_data,
            'categories': categories_data,
            'locations':  locations_data,
            'insights':   insights_data,
            'alert_summary': alert_summary,
            'store': {
                'id':            store.id,
                'name':          store.shop_name,
                'domain':        store.shop_domain,
                'last_synced_at':store.last_synced_at.isoformat() if store.last_synced_at else None,
            },
        }
        cache.set(cache_key, data, CACHE_TTL)
        return Response(data)


class DashboardKPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, store_id):
        store = _get_store(store_id, request.user)
        if not store:
            return Response({'error': 'Store not found'}, status=404)
        try:
            kpi = KPISnapshot.objects.get(store=store)
            return Response(KPISnapshotSerializer(kpi).data)
        except KPISnapshot.DoesNotExist:
            from analytics.tasks import calculate_kpi_snapshot
            calculate_kpi_snapshot.delay(store_id)
            return Response({})


class RevenueTrendView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, store_id):
        store = _get_store(store_id, request.user)
        if not store:
            return Response({'error': 'Store not found'}, status=404)
        days         = min(int(request.query_params.get('days', 30)), 365)
        period_start = date.today() - timedelta(days=days)
        qs           = DailyRevenue.objects.filter(store=store, date__gte=period_start).order_by('date')
        return Response(DailyRevenueSerializer(qs, many=True).data)


class TopProductsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, store_id):
        store = _get_store(store_id, request.user)
        if not store:
            return Response({'error': 'Store not found'}, status=404)

        days         = min(int(request.query_params.get('days', 30)), 365)
        limit        = min(int(request.query_params.get('limit', 10)), 100)
        latest_period = _latest_product_period(store)
        current = (
            ProductSalesSummary.objects
            .filter(store=store, period_start=latest_period)
            .select_related('product')
            .order_by('-total_revenue')[:limit]
        ) if latest_period else []
        prev_period = (
            ProductSalesSummary.objects
            .filter(store=store, period_start__lt=latest_period)
            .aggregate(prev=Max('period_start'))
            .get('prev')
        ) if latest_period else None
        prev_map = {
            p.product_id: float(p.total_revenue)
            for p in ProductSalesSummary.objects.filter(store=store, period_start=prev_period)
        } if prev_period else {}
        results = []
        for item in current:
            prev_rev       = prev_map.get(item.product_id, 0)
            cur_rev        = float(item.total_revenue)
            item.trend_pct = round(((cur_rev - prev_rev) / prev_rev * 100) if prev_rev > 0 else 0, 1)
            results.append(item)
        return Response(ProductSalesSerializer(results, many=True).data)


class CategoryRevenueView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, store_id):
        store = _get_store(store_id, request.user)
        if not store:
            return Response({'error': 'Store not found'}, status=404)
        days         = min(int(request.query_params.get('days', 30)), 365)
        period_start = date.today() - timedelta(days=days)
        qs           = CategoryRevenueSummary.objects.filter(store=store, period_start=period_start).order_by('-total_revenue')
        return Response(CategoryRevenueSerializer(qs, many=True).data)


class LocationRevenueView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, store_id):
        store = _get_store(store_id, request.user)
        if not store:
            return Response({'error': 'Store not found'}, status=404)
        days         = min(int(request.query_params.get('days', 30)), 365)
        period_start = date.today() - timedelta(days=days)
        qs           = LocationRevenueSummary.objects.filter(store=store, period_start=period_start).order_by('-total_revenue')
        return Response(LocationRevenueSerializer(qs, many=True).data)


class InsightsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, store_id):
        store = _get_store(store_id, request.user)
        if not store:
            return Response({'error': 'Store not found'}, status=404)
        qs = Insight.objects.filter(store=store).order_by('-created_at')[:10]
        return Response(InsightSerializer(qs, many=True).data)
