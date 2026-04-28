import logging
from datetime import date, timedelta
from decimal import Decimal

from celery import shared_task
from django.db import transaction
from django.db.models import Sum, Count, Avg, F, ExpressionWrapper, DecimalField
from django.utils import timezone

from stores.models import Store
from warehouse.models import Order, OrderItem, Customer, Product, Inventory
from analytics.models import (
    DailyRevenue, ProductSalesSummary, CategoryRevenueSummary,
    LocationRevenueSummary, InventoryMetric, RFMScore, KPISnapshot,
)

logger = logging.getLogger(__name__)


# ── Master dispatcher ─────────────────────────────────────────────────────────

@shared_task
def run_analytics_for_all_stores():
    """
    Celery Beat calls this every hour.
    Dispatches analytics jobs for each active store.
    """
    store_ids = list(Store.objects.filter(is_active=True).values_list('id', flat=True))
    for store_id in store_ids:
        run_all_analytics.delay(store_id)
    logger.info(f"Dispatched analytics for {len(store_ids)} stores")


@shared_task
def run_all_analytics(store_id: int):
    """Run every analytics job for one store, in dependency order."""
    calculate_daily_revenue.delay(store_id)
    calculate_product_sales.delay(store_id)
    calculate_category_revenue.delay(store_id)
    calculate_location_revenue.delay(store_id)
    calculate_inventory_metrics.delay(store_id)
    calculate_rfm.delay(store_id)
    # KPI snapshot depends on the above — chain it last
    calculate_kpi_snapshot.delay(store_id)


# ── Daily revenue ─────────────────────────────────────────────────────────────

@shared_task
def calculate_daily_revenue(store_id: int):
    """
    Aggregate paid orders by day → DailyRevenue table.
    Uses select_related and annotate — no Python loops over large sets.
    """
    store = Store.objects.get(id=store_id)

    # Aggregate at DB level — much faster than Python loops
    from django.db.models.functions import TruncDate

    rows = (
        Order.objects.filter(
            store=store,
            financial_status=Order.STATUS_PAID,
            cancelled_at__isnull=True,
            processed_at__isnull=False,
        )
        .annotate(day=TruncDate('processed_at'))
        .values('day')
        .annotate(
            rev=Sum('total_price'),
            orders=Count('id'),
            aov=Avg('total_price'),
        )
        .order_by('day')
    )

    with transaction.atomic():
        for row in rows:
            # Profit = revenue - cost of items sold
            cost = (
                OrderItem.objects.filter(
                    order__store=store,
                    order__financial_status=Order.STATUS_PAID,
                    order__processed_at__date=row['day'],
                )
                .exclude(variant__isnull=True)
                .annotate(
                    item_cost=ExpressionWrapper(
                        F('quantity') * F('variant__cost'),
                        output_field=DecimalField(max_digits=14, decimal_places=2),
                    )
                )
                .aggregate(total=Sum('item_cost'))['total'] or Decimal('0')
            )

            profit = (row['rev'] or Decimal('0')) - cost

            DailyRevenue.objects.update_or_create(
                store=store,
                date=row['day'],
                defaults={
                    'total_revenue': row['rev'] or 0,
                    'total_profit': profit,
                    'total_orders': row['orders'] or 0,
                    'avg_order_value': row['aov'] or 0,
                },
            )

    logger.info(f"Daily revenue calculated for {store.shop_domain}: {rows.count()} days")


# ── Product sales summary ─────────────────────────────────────────────────────

@shared_task
def calculate_product_sales(store_id: int, days: int = 30):
    """Aggregate revenue and units sold per product over the last N days."""
    store = Store.objects.get(id=store_id)
    period_end = date.today()
    period_start = period_end - timedelta(days=days)

    rows = (
        OrderItem.objects.filter(
            order__store=store,
            order__financial_status=Order.STATUS_PAID,
            order__cancelled_at__isnull=True,
            order__processed_at__date__gte=period_start,
            product__isnull=False,
        )
        .values('product', 'product__title', 'product__product_type')
        .annotate(
            revenue=Sum('line_total'),
            units=Sum('quantity'),
        )
    )

    with transaction.atomic():
        for row in rows:
            product_id = row['product']
            revenue = row['revenue'] or Decimal('0')
            units = row['units'] or 0

            # Compute profit
            cost = (
                OrderItem.objects.filter(
                    order__store=store,
                    order__financial_status=Order.STATUS_PAID,
                    order__processed_at__date__gte=period_start,
                    product_id=product_id,
                )
                .exclude(variant__isnull=True)
                .annotate(
                    item_cost=ExpressionWrapper(
                        F('quantity') * F('variant__cost'),
                        output_field=DecimalField(max_digits=14, decimal_places=2),
                    )
                )
                .aggregate(total=Sum('item_cost'))['total'] or Decimal('0')
            )

            profit = revenue - cost
            margin = float(profit / revenue * 100) if revenue > 0 else 0.0

            ProductSalesSummary.objects.update_or_create(
                store=store,
                product_id=product_id,
                period_start=period_start,
                defaults={
                    'period_end': period_end,
                    'total_revenue': revenue,
                    'total_profit': profit,
                    'units_sold': units,
                    'margin_pct': margin,
                },
            )

    logger.info(f"Product sales calculated for {store.shop_domain}")


# ── Category revenue ──────────────────────────────────────────────────────────

@shared_task
def calculate_category_revenue(store_id: int, days: int = 30):
    """Aggregate revenue by product category."""
    store = Store.objects.get(id=store_id)
    period_end = date.today()
    period_start = period_end - timedelta(days=days)

    rows = (
        OrderItem.objects.filter(
            order__store=store,
            order__financial_status=Order.STATUS_PAID,
            order__cancelled_at__isnull=True,
            order__processed_at__date__gte=period_start,
            product__isnull=False,
        )
        .values(category=F('product__product_type'))
        .annotate(revenue=Sum('line_total'))
        .order_by('-revenue')
    )

    total_revenue = sum(r['revenue'] or 0 for r in rows)

    with transaction.atomic():
        for row in rows:
            cat = row['category'] or 'Uncategorized'
            rev = row['revenue'] or Decimal('0')
            pct = float(rev / total_revenue * 100) if total_revenue > 0 else 0.0

            CategoryRevenueSummary.objects.update_or_create(
                store=store,
                category=cat,
                period_start=period_start,
                defaults={
                    'period_end': period_end,
                    'total_revenue': rev,
                    'revenue_pct': pct,
                },
            )

    logger.info(f"Category revenue calculated for {store.shop_domain}")


# ── Location revenue ──────────────────────────────────────────────────────────

@shared_task
def calculate_location_revenue(store_id: int, days: int = 30):
    """Aggregate revenue by store location."""
    store = Store.objects.get(id=store_id)
    period_end = date.today()
    period_start = period_end - timedelta(days=days)

    rows = (
        Order.objects.filter(
            store=store,
            financial_status=Order.STATUS_PAID,
            cancelled_at__isnull=True,
            processed_at__date__gte=period_start,
            location__isnull=False,
        )
        .values(location_name=F('location__name'))
        .annotate(
            revenue=Sum('total_price'),
            orders=Count('id'),
        )
    )

    with transaction.atomic():
        for row in rows:
            LocationRevenueSummary.objects.update_or_create(
                store=store,
                location_name=row['location_name'],
                period_start=period_start,
                defaults={
                    'period_end': period_end,
                    'total_revenue': row['revenue'] or 0,
                    'total_orders': row['orders'] or 0,
                },
            )

    logger.info(f"Location revenue calculated for {store.shop_domain}")


# ── Inventory metrics ─────────────────────────────────────────────────────────

@shared_task
def calculate_inventory_metrics(store_id: int):
    """
    For each active variant, compute:
    - avg daily sales (last 30 days)
    - days cover = stock / avg_daily_sales
    - status: critical (<7d), low (<14d), ok, or dead_stock
    """
    store = Store.objects.get(id=store_id)
    lookback_days = 30
    since = date.today() - timedelta(days=lookback_days)

    # Build a map of variant_id → (units_sold, last_sale_date)
    sales = (
        OrderItem.objects.filter(
            order__store=store,
            order__financial_status=Order.STATUS_PAID,
            order__processed_at__date__gte=since,
            variant__isnull=False,
        )
        .values('variant_id')
        .annotate(
            units=Sum('quantity'),
            last_sale=__import__('django.db.models', fromlist=['Max']).Max('order__processed_at'),
        )
    )
    sales_map = {r['variant_id']: (r['units'] or 0, r['last_sale']) for r in sales}

    # Get all active variants with their stock
    from warehouse.models import ProductVariant
    variants = (
        ProductVariant.objects.filter(product__store=store, product__status='active')
        .select_related('product')
    )

    with transaction.atomic():
        for variant in variants:
            stock = variant.inventory_quantity or 0
            units_sold, last_sale = sales_map.get(variant.id, (0, None))
            avg_daily = units_sold / lookback_days if units_sold > 0 else 0.0
            days_cover = (stock / avg_daily) if avg_daily > 0 else 999.0

            # Days since last sale
            days_since_sale = None
            if last_sale:
                days_since_sale = (timezone.now() - last_sale).days

            # Classify status
            if avg_daily > 0 and days_cover <= 7:
                status = InventoryMetric.STATUS_CRITICAL
            elif avg_daily > 0 and days_cover <= 14:
                status = InventoryMetric.STATUS_LOW
            elif avg_daily == 0 and (days_since_sale is None or days_since_sale > 60):
                status = InventoryMetric.STATUS_DEAD
            else:
                status = InventoryMetric.STATUS_OK

            InventoryMetric.objects.update_or_create(
                store=store,
                variant_id=variant.id,
                defaults={
                    'product': variant.product,
                    'product_title': variant.product.title,
                    'variant_title': variant.title or '',
                    'sku': variant.sku or '',
                    'stock_quantity': stock,
                    'avg_daily_sales': round(avg_daily, 2),
                    'days_cover': round(min(days_cover, 999.0), 1),
                    'status': status,
                    'last_sold_days_ago': days_since_sale,
                },
            )

    logger.info(f"Inventory metrics calculated for {store.shop_domain}")


# ── RFM segmentation ──────────────────────────────────────────────────────────

@shared_task
def calculate_rfm(store_id: int):
    """
    Assign RFM scores and segment labels to all customers.

    Segments:
        VIP       — high recency, frequency, monetary
        Loyal     — good frequency, recent enough
        New       — first purchase ≤ 30 days ago
        At Risk   — was active, now quiet (31–120 days)
        Lost      — no activity in 120+ days
    """
    store = Store.objects.get(id=store_id)
    customers = Customer.objects.filter(store=store)
    now = timezone.now()

    with transaction.atomic():
        for customer in customers.iterator(chunk_size=500):
            orders = Order.objects.filter(
                store=store,
                customer=customer,
                financial_status=Order.STATUS_PAID,
                cancelled_at__isnull=True,
            )
            frequency = orders.count()
            monetary = orders.aggregate(total=Sum('total_price'))['total'] or Decimal('0')

            last_order = (
                orders.order_by('-processed_at').values_list('processed_at', flat=True).first()
            )
            recency = (now - last_order).days if last_order else 999

            # Score 1–5
            recency_score = _score_recency(recency)
            frequency_score = _score_frequency(frequency)
            monetary_score = _score_monetary(float(monetary))

            # Segment label
            segment = _assign_segment(recency, frequency, float(monetary))

            RFMScore.objects.update_or_create(
                store=store,
                customer=customer,
                defaults={
                    'recency': recency,
                    'frequency': frequency,
                    'monetary': monetary,
                    'recency_score': recency_score,
                    'frequency_score': frequency_score,
                    'monetary_score': monetary_score,
                    'segment': segment,
                },
            )

            # Write segment back to customer for easy filtering
            customer.rfm_segment = segment
            customer.rfm_recency_score = recency_score
            customer.rfm_frequency_score = frequency_score
            customer.rfm_monetary_score = monetary_score
            customer.save(update_fields=[
                'rfm_segment', 'rfm_recency_score',
                'rfm_frequency_score', 'rfm_monetary_score',
            ])

    logger.info(f"RFM calculated for {customers.count()} customers in {store.shop_domain}")


def _score_recency(days: int) -> int:
    if days <= 7:   return 5
    if days <= 30:  return 4
    if days <= 60:  return 3
    if days <= 120: return 2
    return 1


def _score_frequency(count: int) -> int:
    if count >= 10: return 5
    if count >= 5:  return 4
    if count >= 3:  return 3
    if count >= 2:  return 2
    return 1


def _score_monetary(value: float) -> int:
    if value >= 1000: return 5
    if value >= 500:  return 4
    if value >= 200:  return 3
    if value >= 50:   return 2
    return 1


def _assign_segment(recency: int, frequency: int, monetary: float) -> str:
    if monetary >= 200 and frequency >= 3 and recency <= 30:
        return 'VIP'
    if frequency >= 2 and recency <= 60:
        return 'Loyal'
    if frequency == 1 and recency <= 30:
        return 'New'
    if recency <= 120:
        return 'At Risk'
    return 'Lost'


# ── KPI snapshot ──────────────────────────────────────────────────────────────

@shared_task
def calculate_kpi_snapshot(store_id: int):
    """
    Compute and cache the headline KPIs for the last 30 days.
    Written to KPISnapshot — queried instantly by the API.
    """
    store = Store.objects.get(id=store_id)
    today = date.today()
    start_30 = today - timedelta(days=30)
    start_60 = today - timedelta(days=60)

    def _period_stats(date_from, date_to):
        qs = Order.objects.filter(
            store=store,
            financial_status=Order.STATUS_PAID,
            cancelled_at__isnull=True,
            processed_at__date__gte=date_from,
            processed_at__date__lt=date_to,
        )
        agg = qs.aggregate(rev=Sum('total_price'), orders=Count('id'), aov=Avg('total_price'))
        return (
            agg['rev'] or Decimal('0'),
            agg['orders'] or 0,
            agg['aov'] or Decimal('0'),
        )

    cur_rev, cur_orders, cur_aov = _period_stats(start_30, today)
    prev_rev, prev_orders, prev_aov = _period_stats(start_60, start_30)

    def _pct(cur, prev):
        if prev == 0:
            return 100.0 if cur > 0 else 0.0
        return round(float((cur - prev) / prev * 100), 1)

    # Profit
    cur_cost = (
        OrderItem.objects.filter(
            order__store=store,
            order__financial_status=Order.STATUS_PAID,
            order__processed_at__date__gte=start_30,
        )
        .exclude(variant__isnull=True)
        .annotate(
            ic=ExpressionWrapper(
                F('quantity') * F('variant__cost'),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )
        .aggregate(total=Sum('ic'))['total'] or Decimal('0')
    )
    cur_profit = cur_rev - cur_cost

    prev_cost = (
        OrderItem.objects.filter(
            order__store=store,
            order__financial_status=Order.STATUS_PAID,
            order__processed_at__date__gte=start_60,
            order__processed_at__date__lt=start_30,
        )
        .exclude(variant__isnull=True)
        .annotate(
            ic=ExpressionWrapper(
                F('quantity') * F('variant__cost'),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )
        .aggregate(total=Sum('ic'))['total'] or Decimal('0')
    )
    prev_profit = prev_rev - prev_cost

    # Customers
    total_customers = Customer.objects.filter(store=store).count()
    repeat_customers = Customer.objects.filter(store=store, orders_count__gte=2).count()
    repeat_rate = round(repeat_customers / total_customers * 100, 1) if total_customers > 0 else 0.0

    KPISnapshot.objects.update_or_create(
        store=store,
        defaults={
            'revenue_30d': cur_rev,
            'revenue_prev_30d': prev_rev,
            'revenue_change_pct': _pct(cur_rev, prev_rev),
            'profit_30d': cur_profit,
            'profit_change_pct': _pct(cur_profit, prev_profit),
            'orders_30d': cur_orders,
            'orders_change_pct': _pct(cur_orders, prev_orders),
            'aov_30d': cur_aov,
            'aov_change_pct': _pct(cur_aov, prev_aov),
            'total_customers': total_customers,
            'repeat_purchase_rate': repeat_rate,
        },
    )

    logger.info(f"KPI snapshot updated for {store.shop_domain}: ${cur_rev:.2f} revenue")
