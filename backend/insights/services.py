import logging
from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone

from stores.models import Store
from analytics.models import InventoryMetric, KPISnapshot, RFMScore
from insights.models import Alert, Insight

logger = logging.getLogger(__name__)


class InsightGenerator:
    """
    Reads precomputed analytics metrics and generates:
    - Alert objects (stockouts, revenue drops, dead stock, at-risk customers)
    - Insight objects (natural language summaries for the dashboard)

    Never calls Shopify directly. Never runs analytics queries.
    Only reads from analytics tables.
    """

    def __init__(self, store: Store):
        self.store = store

    def run(self):
        """Generate all alerts and insights for this store."""
        self._resolve_stale_alerts()
        self._generate_stockout_alerts()
        self._generate_dead_stock_alerts()
        self._generate_revenue_alerts()
        self._generate_customer_alerts()
        self._generate_opportunity_alerts()
        self._generate_insights()
        logger.info(f"Insights generated for {self.store.shop_domain}")

    # ── Internal: resolve stale alerts ────────────────────────────────────────

    def _resolve_stale_alerts(self):
        """Auto-resolve alerts whose condition is no longer true."""
        # Resolve stockout alerts for products now back in stock
        critical_keys = set(
            InventoryMetric.objects.filter(
                store=self.store,
                status=InventoryMetric.STATUS_CRITICAL,
            ).values_list('dedup_key', flat=True)
            if hasattr(InventoryMetric, 'dedup_key') else []
        )
        # Mark resolved anything older than 24h that hasn't been refreshed
        Alert.objects.filter(
            store=self.store,
            is_resolved=False,
            created_at__lt=timezone.now() - timedelta(hours=24),
        ).update(is_resolved=True, resolved_at=timezone.now())

    # ── Stockout alerts ────────────────────────────────────────────────────────

    def _generate_stockout_alerts(self):
        critical = InventoryMetric.objects.filter(
            store=self.store,
            status=InventoryMetric.STATUS_CRITICAL,
        )
        for item in critical:
            dedup_key = f"stockout-{item.variant_id}"
            days = int(item.days_cover) if item.days_cover < 999 else 0

            Alert.objects.update_or_create(
                store=self.store,
                dedup_key=dedup_key,
                defaults={
                    'severity': Alert.SEVERITY_CRITICAL,
                    'category': Alert.CATEGORY_STOCKOUT,
                    'title': f'Stockout risk: {item.product_title}',
                    'description': (
                        f'{item.stock_quantity} units left, selling {item.avg_daily_sales:.1f}/day. '
                        f'Runs out in {days} day{"s" if days != 1 else ""}.'
                    ),
                    'action_label': 'Restock now',
                    'action_url': f'/inventory?variant={item.variant_id}',
                    'is_resolved': False,
                    'metadata': {
                        'variant_id': item.variant_id,
                        'stock': item.stock_quantity,
                        'days_cover': item.days_cover,
                    },
                },
            )

        low_stock = InventoryMetric.objects.filter(
            store=self.store,
            status=InventoryMetric.STATUS_LOW,
        )
        for item in low_stock:
            dedup_key = f"low-stock-{item.variant_id}"
            Alert.objects.update_or_create(
                store=self.store,
                dedup_key=dedup_key,
                defaults={
                    'severity': Alert.SEVERITY_WARNING,
                    'category': Alert.CATEGORY_STOCKOUT,
                    'title': f'Low stock: {item.product_title}',
                    'description': (
                        f'{item.stock_quantity} units remaining. '
                        f'At current rate, runs out in {int(item.days_cover)} days.'
                    ),
                    'action_label': 'Review stock',
                    'action_url': f'/inventory?variant={item.variant_id}',
                    'is_resolved': False,
                    'metadata': {'variant_id': item.variant_id},
                },
            )

    # ── Dead stock alerts ──────────────────────────────────────────────────────

    def _generate_dead_stock_alerts(self):
        dead_count = InventoryMetric.objects.filter(
            store=self.store,
            status=InventoryMetric.STATUS_DEAD,
        ).count()

        if dead_count > 0:
            Alert.objects.update_or_create(
                store=self.store,
                dedup_key='dead-stock-summary',
                defaults={
                    'severity': Alert.SEVERITY_WARNING,
                    'category': Alert.CATEGORY_INVENTORY,
                    'title': f'{dead_count} product{"s" if dead_count != 1 else ""} with no sales in 60+ days',
                    'description': (
                        'These products are tying up capital. '
                        'Consider markdown pricing or discontinuation.'
                    ),
                    'action_label': 'Review dead stock',
                    'action_url': '/inventory?status=dead_stock',
                    'is_resolved': False,
                    'metadata': {'count': dead_count},
                },
            )

    # ── Revenue alerts ─────────────────────────────────────────────────────────

    def _generate_revenue_alerts(self):
        try:
            kpi = KPISnapshot.objects.get(store=self.store)
        except KPISnapshot.DoesNotExist:
            return

        if kpi.revenue_change_pct <= -15:
            Alert.objects.update_or_create(
                store=self.store,
                dedup_key='revenue-drop',
                defaults={
                    'severity': Alert.SEVERITY_WARNING,
                    'category': Alert.CATEGORY_REVENUE,
                    'title': f'Revenue down {abs(kpi.revenue_change_pct):.1f}% vs last period',
                    'description': (
                        f'Revenue dropped from ${float(kpi.revenue_prev_30d):,.0f} '
                        f'to ${float(kpi.revenue_30d):,.0f}. '
                        'Review top product inventory and promotions.'
                    ),
                    'action_label': 'View revenue',
                    'action_url': '/dashboard',
                    'is_resolved': False,
                    'metadata': {
                        'change_pct': kpi.revenue_change_pct,
                        'current': float(kpi.revenue_30d),
                        'previous': float(kpi.revenue_prev_30d),
                    },
                },
            )
        elif kpi.revenue_change_pct >= 15:
            Alert.objects.update_or_create(
                store=self.store,
                dedup_key='revenue-up',
                defaults={
                    'severity': Alert.SEVERITY_SUCCESS,
                    'category': Alert.CATEGORY_OPPORTUNITY,
                    'title': f'Revenue up {kpi.revenue_change_pct:.1f}% this period',
                    'description': (
                        f'Strong growth to ${float(kpi.revenue_30d):,.0f}. '
                        'Review top products and double down on what\'s working.'
                    ),
                    'action_label': 'View top products',
                    'action_url': '/products',
                    'is_resolved': False,
                    'metadata': {'change_pct': kpi.revenue_change_pct},
                },
            )

    # ── Customer alerts ────────────────────────────────────────────────────────

    def _generate_customer_alerts(self):
        at_risk = RFMScore.objects.filter(store=self.store, segment='At Risk')
        at_risk_count = at_risk.count()
        if at_risk_count == 0:
            return

        at_risk_revenue = at_risk.aggregate(
            total=__import__('django.db.models', fromlist=['Sum']).Sum('monetary')
        )['total'] or Decimal('0')

        Alert.objects.update_or_create(
            store=self.store,
            dedup_key='at-risk-customers',
            defaults={
                'severity': Alert.SEVERITY_WARNING,
                'category': Alert.CATEGORY_CUSTOMER,
                'title': f'{at_risk_count} customer{"s" if at_risk_count != 1 else ""} at churn risk',
                'description': (
                    f'These customers haven\'t ordered in 45+ days. '
                    f'Estimated revenue at risk: ${float(at_risk_revenue):,.0f}. '
                    'A win-back campaign could recover them.'
                ),
                'action_label': 'Launch win-back',
                'action_url': '/customers?segment=At+Risk',
                'is_resolved': False,
                'metadata': {
                    'count': at_risk_count,
                    'revenue_at_risk': float(at_risk_revenue),
                },
            },
        )

    # ── Opportunity alerts ─────────────────────────────────────────────────────

    def _generate_opportunity_alerts(self):
        from analytics.models import ProductSalesSummary
        from datetime import date, timedelta

        today = date.today()
        period_30 = today - timedelta(days=30)
        period_60 = today - timedelta(days=60)

        # Find products with > 30% revenue growth vs previous period
        for summary in ProductSalesSummary.objects.filter(
            store=self.store,
            period_start=period_30,
        ).select_related('product'):
            prev = ProductSalesSummary.objects.filter(
                store=self.store,
                product=summary.product,
                period_start=period_60,
            ).first()

            if prev and float(prev.total_revenue) > 0:
                growth = float(
                    (summary.total_revenue - prev.total_revenue) / prev.total_revenue * 100
                )
                if growth >= 30:
                    dedup_key = f"trending-{summary.product_id}"
                    Alert.objects.update_or_create(
                        store=self.store,
                        dedup_key=dedup_key,
                        defaults={
                            'severity': Alert.SEVERITY_SUCCESS,
                            'category': Alert.CATEGORY_OPPORTUNITY,
                            'title': f'Trending: {summary.product.title}',
                            'description': (
                                f'Demand up {growth:.0f}% vs last period. '
                                f'{summary.units_sold} units sold, ${float(summary.total_revenue):,.0f} revenue.'
                            ),
                            'action_label': 'View product',
                            'action_url': f'/products/{summary.product_id}',
                            'is_resolved': False,
                            'metadata': {
                                'growth_pct': growth,
                                'product_id': summary.product_id,
                            },
                        },
                    )

    # ── Natural language insights ──────────────────────────────────────────────

    def _generate_insights(self):
        """Create Insight objects for the dashboard insight panel."""
        # Clear stale insights
        Insight.objects.filter(store=self.store).delete()

        try:
            kpi = KPISnapshot.objects.get(store=self.store)
        except KPISnapshot.DoesNotExist:
            return

        direction = 'up' if kpi.revenue_change_pct >= 0 else 'down'
        sev = 'success' if direction == 'up' else 'warning'

        Insight.objects.create(
            store=self.store,
            insight_type=Insight.TYPE_REVENUE,
            severity=sev,
            title=f'Revenue is {direction} {abs(kpi.revenue_change_pct):.1f}% this month',
            description=(
                f'Your store generated ${float(kpi.revenue_30d):,.0f} in the last 30 days. '
                f'Gross profit: ${float(kpi.profit_30d):,.0f}.'
            ),
            action='View revenue trend',
            value=kpi.revenue_30d,
        )

        # Top product insight
        from analytics.models import ProductSalesSummary
        from datetime import date, timedelta
        top = (
            ProductSalesSummary.objects.filter(
                store=self.store,
                period_start=date.today() - timedelta(days=30),
            )
            .select_related('product')
            .order_by('-total_revenue')
            .first()
        )
        if top:
            Insight.objects.create(
                store=self.store,
                insight_type=Insight.TYPE_PRODUCT,
                severity='info',
                title=f'{top.product.title} is your best performer',
                description=(
                    f'${float(top.total_revenue):,.0f} revenue, '
                    f'{top.units_sold} units sold, '
                    f'{top.margin_pct:.0f}% margin.'
                ),
                action='View product',
                value=top.total_revenue,
            )

        # Customer insight
        vip_count = RFMScore.objects.filter(store=self.store, segment='VIP').count()
        if vip_count > 0:
            Insight.objects.create(
                store=self.store,
                insight_type=Insight.TYPE_CUSTOMER,
                severity='info',
                title=f'{vip_count} VIP customer{"s" if vip_count != 1 else ""} driving your revenue',
                description=(
                    f'Your top customers generate disproportionate revenue. '
                    'Keep them engaged with exclusive offers and early access.'
                ),
                action='View VIP customers',
            )
