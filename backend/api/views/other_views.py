from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from stores.models import Store
from analytics.models import InventoryMetric, RFMScore
from insights.models import Alert
from warehouse.models import Customer
from api.serializers.all_serializers import (
    InventoryMetricSerializer, AlertSerializer, CustomerSerializer,
)


# ── Inventory ─────────────────────────────────────────────────────────────────

class InventoryOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id, user=request.user, is_active=True)
        except Store.DoesNotExist:
            return Response({'error': 'Store not found'}, status=404)

        status_filter = request.query_params.get('status')
        qs = InventoryMetric.objects.filter(store=store)
        if status_filter:
            qs = qs.filter(status=status_filter)

        STATUS_ORDER = {
            InventoryMetric.STATUS_CRITICAL: 0,
            InventoryMetric.STATUS_LOW:      1,
            InventoryMetric.STATUS_DEAD:     2,
            InventoryMetric.STATUS_OK:       3,
        }
        items = sorted(qs, key=lambda x: STATUS_ORDER.get(x.status, 99))

        valid_covers = [i.days_cover for i in items if i.days_cover < 999]
        avg_cover    = round(sum(valid_covers) / len(valid_covers), 1) if valid_covers else 0

        return Response({
            'summary': {
                'total_skus':       qs.count(),
                'critical_count':   qs.filter(status=InventoryMetric.STATUS_CRITICAL).count(),
                'low_count':        qs.filter(status=InventoryMetric.STATUS_LOW).count(),
                'dead_stock_count': qs.filter(status=InventoryMetric.STATUS_DEAD).count(),
                'healthy_count':    qs.filter(status=InventoryMetric.STATUS_OK).count(),
                'avg_days_cover':   avg_cover,
            },
            'items': InventoryMetricSerializer(items, many=True).data,
        })


# ── Customers ─────────────────────────────────────────────────────────────────

class CustomerAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id, user=request.user, is_active=True)
        except Store.DoesNotExist:
            return Response({'error': 'Store not found'}, status=404)

        from datetime import date
        from django.db.models import Sum, Count, Avg

        total  = Customer.objects.filter(store=store).count()
        repeat = Customer.objects.filter(store=store, orders_count__gte=2).count()
        agg    = Customer.objects.filter(store=store).aggregate(avg_ltv=Avg('total_spent'))

        this_month = date.today().replace(day=1)
        new_month  = Customer.objects.filter(store=store, shopify_created_at__date__gte=this_month).count()
        at_risk    = Customer.objects.filter(store=store, rfm_segment='At Risk').count()

        # Segment breakdown from RFMScore
        from django.db.models import Sum as DSum, Count as DCount, Avg as DAvg
        from analytics.models import RFMScore
        segment_rows = (
            RFMScore.objects.filter(store=store)
            .values('segment')
            .annotate(count=DCount('id'), total_monetary=DSum('monetary'), avg_freq=DAvg('frequency'))
            .order_by('-total_monetary')
        )
        total_monetary = sum(float(r['total_monetary'] or 0) for r in segment_rows)

        COLORS = {'VIP':'#10B981','Loyal':'#1E6FD9','New':'#8B5CF6','At Risk':'#F59E0B','Lost':'#EF4444'}
        segments = []
        for row in segment_rows:
            count   = row['count']
            monetary = float(row['total_monetary'] or 0)
            segments.append({
                'segment':     row['segment'],
                'count':       count,
                'revenue_pct': round(monetary / total_monetary * 100, 1) if total_monetary > 0 else 0,
                'avg_ltv':     round(monetary / count, 2) if count > 0 else 0,
                'avg_orders':  round(float(row['avg_freq'] or 0), 1),
                'color':       COLORS.get(row['segment'], '#8fa3b8'),
            })

        return Response({
            'total_customers':      total,
            'repeat_purchase_rate': round(repeat / total * 100, 1) if total > 0 else 0,
            'avg_ltv':              float(agg['avg_ltv'] or 0),
            'new_this_month':       new_month,
            'at_risk_count':        at_risk,
            'segments':             segments,
        })


class CustomerListView(APIView):
    permission_classes = [IsAuthenticated]

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
            from django.db.models import Q
            qs = qs.filter(
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )

        sort_by = request.query_params.get('sort', '-total_spent')
        if sort_by in ['total_spent','-total_spent','orders_count','-orders_count','last_order_date','-last_order_date']:
            qs = qs.order_by(sort_by)

        page      = max(1, int(request.query_params.get('page', 1)))
        page_size = min(200, int(request.query_params.get('page_size', 50)))
        total     = qs.count()
        customers = qs[(page-1)*page_size : page*page_size]

        return Response({
            'count':       total,
            'page':        page,
            'page_size':   page_size,
            'total_pages': (total + page_size - 1) // page_size,
            'results':     CustomerSerializer(customers, many=True).data,
        })


# ── Alerts ────────────────────────────────────────────────────────────────────

class AlertListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id, user=request.user, is_active=True)
        except Store.DoesNotExist:
            return Response({'error': 'Store not found'}, status=404)

        severity = request.query_params.get('severity')
        qs = Alert.objects.filter(store=store, is_resolved=False).order_by('-created_at')
        if severity:
            qs = qs.filter(severity=severity)

        return Response({
            'summary': {
                'total':         qs.count(),
                'critical':      qs.filter(severity='critical').count(),
                'warning':       qs.filter(severity='warning').count(),
                'opportunities': qs.filter(severity='success').count(),
            },
            'alerts': AlertSerializer(qs, many=True).data,
        })


class AlertResolveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, store_id, alert_id):
        try:
            store = Store.objects.get(id=store_id, user=request.user)
            alert = Alert.objects.get(id=alert_id, store=store)
        except (Store.DoesNotExist, Alert.DoesNotExist):
            return Response({'error': 'Not found'}, status=404)

        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        alert.save(update_fields=['is_resolved', 'resolved_at'])
        return Response({'success': True})
