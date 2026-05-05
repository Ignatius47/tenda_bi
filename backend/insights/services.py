import logging
from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone

from stores.models import Store
from analytics.models import InventoryMetric, KPISnapshot, RFMScore, ProductSalesSummary
from insights.models import Alert, Insight

logger = logging.getLogger(__name__)


class InsightGenerator:
    def __init__(self, store: Store):
        self.store = store

    def run(self):
        self._resolve_stale_alerts()
        self._stockout_alerts()
        self._dead_stock_alerts()
        self._revenue_alerts()
        self._customer_alerts()
        self._opportunity_alerts()
        self._generate_insights()
        logger.info(f"Insights generated for {self.store.shop_domain}")

    def _resolve_stale_alerts(self):
        Alert.objects.filter(
            store=self.store,
            is_resolved=False,
            created_at__lt=timezone.now() - timedelta(hours=24),
        ).update(is_resolved=True, resolved_at=timezone.now())

    def _stockout_alerts(self):
        for item in InventoryMetric.objects.filter(store=self.store, status=InventoryMetric.STATUS_CRITICAL):
            days = int(item.days_cover) if item.days_cover < 999 else 0
            Alert.objects.update_or_create(
                store=self.store, dedup_key=f"stockout-{item.variant_id}",
                defaults={
                    'severity':    Alert.SEV_CRITICAL,
                    'category':    Alert.CAT_STOCKOUT,
                    'title':       f"Stockout risk: {item.product_title}",
                    'description': (
                        f"{item.stock_quantity} units left, selling {item.avg_daily_sales:.1f}/day. "
                        f"Runs out in {days} day{'s' if days != 1 else ''}."
                    ),
                    'action_label': 'Restock now',
                    'action_url':   f"/inventory?variant={item.variant_id}",
                    'is_resolved':  False,
                    'metadata':     {'variant_id': item.variant_id, 'stock': item.stock_quantity},
                },
            )
        for item in InventoryMetric.objects.filter(store=self.store, status=InventoryMetric.STATUS_LOW):
            Alert.objects.update_or_create(
                store=self.store, dedup_key=f"low-stock-{item.variant_id}",
                defaults={
                    'severity':    Alert.SEV_WARNING,
                    'category':    Alert.CAT_STOCKOUT,
                    'title':       f"Low stock: {item.product_title}",
                    'description': f"{item.stock_quantity} units. Runs out in {int(item.days_cover)} days.",
                    'action_label': 'Review stock',
                    'is_resolved':  False,
                    'metadata':     {'variant_id': item.variant_id},
                },
            )

    def _dead_stock_alerts(self):
        dead = InventoryMetric.objects.filter(store=self.store, status=InventoryMetric.STATUS_DEAD).count()
        if dead > 0:
            Alert.objects.update_or_create(
                store=self.store, dedup_key='dead-stock-summary',
                defaults={
                    'severity':    Alert.SEV_WARNING,
                    'category':    Alert.CAT_INVENTORY,
                    'title':       f"{dead} product{'s' if dead != 1 else ''} with no sales in 60+ days",
                    'description': 'Consider markdown pricing or discontinuation to free up capital.',
                    'action_label':'Review dead stock',
                    'action_url':  '/inventory?status=dead_stock',
                    'is_resolved': False,
                    'metadata':    {'count': dead},
                },
            )

    def _revenue_alerts(self):
        try:
            kpi = KPISnapshot.objects.get(store=self.store)
        except KPISnapshot.DoesNotExist:
            return
        if kpi.revenue_change_pct <= -15:
            Alert.objects.update_or_create(
                store=self.store, dedup_key='revenue-drop',
                defaults={
                    'severity':    Alert.SEV_WARNING,
                    'category':    Alert.CAT_REVENUE,
                    'title':       f"Revenue down {abs(kpi.revenue_change_pct):.1f}% vs last period",
                    'description': f"From ${float(kpi.revenue_prev_30d):,.0f} to ${float(kpi.revenue_30d):,.0f}. Review top product inventory.",
                    'action_label':'View revenue',
                    'action_url':  '/dashboard',
                    'is_resolved': False,
                },
            )
        elif kpi.revenue_change_pct >= 15:
            Alert.objects.update_or_create(
                store=self.store, dedup_key='revenue-up',
                defaults={
                    'severity':    Alert.SEV_SUCCESS,
                    'category':    Alert.CAT_OPPORTUNITY,
                    'title':       f"Revenue up {kpi.revenue_change_pct:.1f}% this period",
                    'description': f"Strong growth to ${float(kpi.revenue_30d):,.0f}. Double down on what's working.",
                    'action_label':'View top products',
                    'action_url':  '/products',
                    'is_resolved': False,
                },
            )

    def _customer_alerts(self):
        at_risk = RFMScore.objects.filter(store=self.store, segment='At Risk')
        count   = at_risk.count()
        if count > 0:
            revenue = at_risk.aggregate(t=__import__('django.db.models', fromlist=['Sum']).Sum('monetary'))['t'] or Decimal('0')
            Alert.objects.update_or_create(
                store=self.store, dedup_key='at-risk-customers',
                defaults={
                    'severity':    Alert.SEV_WARNING,
                    'category':    Alert.CAT_CUSTOMER,
                    'title':       f"{count} customer{'s' if count != 1 else ''} at churn risk",
                    'description': f"No purchase in 45+ days. Revenue at risk: ${float(revenue):,.0f}.",
                    'action_label':'Launch win-back',
                    'action_url':  '/customers?segment=At+Risk',
                    'is_resolved': False,
                    'metadata':    {'count': count},
                },
            )

    def _opportunity_alerts(self):
        today       = date.today()
        period_30   = today - timedelta(days=30)
        period_60   = today - timedelta(days=60)

        for summary in ProductSalesSummary.objects.filter(
            store=self.store, period_start=period_30
        ).select_related('product'):
            prev = ProductSalesSummary.objects.filter(
                store=self.store, product=summary.product, period_start=period_60
            ).first()
            if prev and float(prev.total_revenue) > 0:
                growth = float((summary.total_revenue - prev.total_revenue) / prev.total_revenue * 100)
                if growth >= 30:
                    Alert.objects.update_or_create(
                        store=self.store, dedup_key=f"trending-{summary.product_id}",
                        defaults={
                            'severity':    Alert.SEV_SUCCESS,
                            'category':    Alert.CAT_OPPORTUNITY,
                            'title':       f"Trending: {summary.product.title}",
                            'description': f"Demand up {growth:.0f}%. {summary.units_sold} units sold, ${float(summary.total_revenue):,.0f} revenue.",
                            'action_label':'View product',
                            'is_resolved': False,
                        },
                    )

    def _generate_insights(self):
        Insight.objects.filter(store=self.store).delete()
        try:
            kpi = KPISnapshot.objects.get(store=self.store)
        except KPISnapshot.DoesNotExist:
            return

        direction = 'up' if kpi.revenue_change_pct >= 0 else 'down'
        Insight.objects.create(
            store=self.store,
            insight_type=Insight.TYPE_REVENUE,
            severity='success' if direction == 'up' else 'warning',
            title=f"Revenue is {direction} {abs(kpi.revenue_change_pct):.1f}% this month",
            description=f"Your store generated ${float(kpi.revenue_30d):,.0f} in the last 30 days. Gross profit: ${float(kpi.profit_30d):,.0f}.",
            action='View revenue trend',
            value=kpi.revenue_30d,
        )

        today      = date.today()
        period_30  = today - timedelta(days=30)
        top = (
            ProductSalesSummary.objects.filter(store=self.store, period_start=period_30)
            .select_related('product').order_by('-total_revenue').first()
        )
        if top:
            Insight.objects.create(
                store=self.store,
                insight_type=Insight.TYPE_PRODUCT,
                severity='info',
                title=f"{top.product.title} is your best performer",
                description=f"${float(top.total_revenue):,.0f} revenue, {top.units_sold} units, {top.margin_pct:.0f}% margin.",
                action='View product',
                value=top.total_revenue,
            )

        vip = RFMScore.objects.filter(store=self.store, segment='VIP').count()
        if vip > 0:
            Insight.objects.create(
                store=self.store,
                insight_type=Insight.TYPE_CUSTOMER,
                severity='info',
                title=f"{vip} VIP customer{'s' if vip != 1 else ''} driving your revenue",
                description="Your top customers generate disproportionate revenue. Keep them engaged.",
                action='View VIP customers',
            )
