from decimal import Decimal
from django.db.models import Sum, Count, Avg
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from stores.models import Store
from warehouse.models import Customer
from analytics.models import RFMScore
from api.permissions import IsStoreOwner
from api.serializers.analytics_serializers import CustomerSerializer, RFMSegmentSummarySerializer


SEGMENT_COLORS = {
    'VIP':      '#22C55E',
    'Loyal':    '#3b82f6',
    'New':      '#8b5cf6',
    'At Risk':  '#f59e0b',
    'Lost':     '#ef4444',
}


class CustomerAnalyticsView(APIView):
    """
    GET /api/customers/{store_id}/analytics/
    Returns RFM segment breakdown and top-level customer KPIs.
    """
    permission_classes = [IsAuthenticated, IsStoreOwner]

    def get(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id, user=request.user, is_active=True)
        except Store.DoesNotExist:
            return Response({'error': 'Store not found'}, status=404)

        total = Customer.objects.filter(store=store).count()
        repeat = Customer.objects.filter(store=store, orders_count__gte=2).count()

        agg = Customer.objects.filter(store=store).aggregate(
            avg_ltv=Avg('total_spent'),
            avg_orders=Avg('orders_count'),
        )

        # Build segment summaries from RFMScore
        segment_rows = (
            RFMScore.objects
            .filter(store=store)
            .values('segment')
            .annotate(
                count=Count('id'),
                total_monetary=Sum('monetary'),
                avg_frequency=Avg('frequency'),
            )
            .order_by('-total_monetary')
        )

        total_monetary = sum(r['total_monetary'] or 0 for r in segment_rows)

        segments = []
        for row in segment_rows:
            seg = row['segment']
            count = row['count']
            monetary = float(row['total_monetary'] or 0)
            pct = round(monetary / float(total_monetary) * 100, 1) if total_monetary > 0 else 0
            avg_ltv = round(monetary / count, 2) if count > 0 else 0
            avg_orders = round(float(row['avg_frequency'] or 0), 1)
            segments.append({
                'segment': seg,
                'count': count,
                'revenue_pct': pct,
                'avg_ltv': avg_ltv,
                'avg_orders': avg_orders,
                'color': SEGMENT_COLORS.get(seg, '#8fa3b8'),
            })

        # Month-over-month new customers
        from datetime import date, timedelta
        this_month_start = date.today().replace(day=1)
        new_this_month = Customer.objects.filter(
            store=store,
            shopify_created_at__date__gte=this_month_start,
        ).count()

        at_risk_count = Customer.objects.filter(store=store, rfm_segment='At Risk').count()

        return Response({
            'total_customers': total,
            'repeat_purchase_rate': round(repeat / total * 100, 1) if total > 0 else 0,
            'avg_ltv': float(agg['avg_ltv'] or 0),
            'avg_orders': float(agg['avg_orders'] or 0),
            'new_this_month': new_this_month,
            'at_risk_count': at_risk_count,
            'segments': segments,
        })


class CustomerListView(APIView):
    """
    GET /api/customers/{store_id}/list/?segment=VIP&page=1&page_size=50
    Paginated, filterable customer list with RFM data.
    """
    permission_classes = [IsAuthenticated, IsStoreOwner]

    def get(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id, user=request.user, is_active=True)
        except Store.DoesNotExist:
            return Response({'error': 'Store not found'}, status=404)

        qs = Customer.objects.filter(store=store)

        segment = request.query_params.get('segment')
        if segment:
            qs = qs.filter(rfm_segment=segment)

        search = request.query_params.get('search')
        if search:
            qs = qs.filter(email__icontains=search) | qs.filter(first_name__icontains=search)

        sort_by = request.query_params.get('sort', '-total_spent')
        allowed_sorts = ['total_spent', '-total_spent', 'orders_count', '-orders_count',
                         'last_order_date', '-last_order_date']
        if sort_by in allowed_sorts:
            qs = qs.order_by(sort_by)
        else:
            qs = qs.order_by('-total_spent')

        page = max(1, int(request.query_params.get('page', 1)))
        page_size = min(200, int(request.query_params.get('page_size', 50)))
        total = qs.count()
        start = (page - 1) * page_size
        customers = qs[start:start + page_size]

        return Response({
            'count': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size,
            'results': CustomerSerializer(customers, many=True).data,
        })
