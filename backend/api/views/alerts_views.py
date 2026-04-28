from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from stores.models import Store
from insights.models import Alert
from api.permissions import IsStoreOwner
from api.serializers.analytics_serializers import AlertSerializer


class AlertListView(APIView):
    """
    GET /api/alerts/{store_id}/
    Returns all active (unresolved) alerts for a store, grouped by severity.
    """
    permission_classes = [IsAuthenticated, IsStoreOwner]

    def get(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id, user=request.user, is_active=True)
        except Store.DoesNotExist:
            return Response({'error': 'Store not found'}, status=404)

        severity_filter = request.query_params.get('severity')
        qs = Alert.objects.filter(store=store, is_resolved=False)
        if severity_filter:
            qs = qs.filter(severity=severity_filter)

        qs = qs.order_by(
            # critical first, then warning, then success/info
            'is_resolved',
            '-created_at',
        )

        summary = {
            'total': qs.count(),
            'critical': qs.filter(severity=Alert.SEVERITY_CRITICAL).count(),
            'warning': qs.filter(severity=Alert.SEVERITY_WARNING).count(),
            'opportunities': qs.filter(severity=Alert.SEVERITY_SUCCESS).count(),
        }

        return Response({
            'summary': summary,
            'alerts': AlertSerializer(qs, many=True).data,
        })


class AlertResolveView(APIView):
    """
    POST /api/alerts/{store_id}/{alert_id}/resolve/
    Mark a specific alert as resolved.
    """
    permission_classes = [IsAuthenticated, IsStoreOwner]

    def post(self, request, store_id, alert_id):
        try:
            store = Store.objects.get(id=store_id, user=request.user)
            alert = Alert.objects.get(id=alert_id, store=store)
        except (Store.DoesNotExist, Alert.DoesNotExist):
            return Response({'error': 'Not found'}, status=404)

        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        alert.save(update_fields=['is_resolved', 'resolved_at'])
        return Response({'success': True, 'alert_id': alert.id})
