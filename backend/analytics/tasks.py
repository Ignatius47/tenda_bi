import logging
from datetime import date, timedelta
from decimal import Decimal

from celery import shared_task
from django.db import transaction
from django.db.models import Sum, Count, Avg, F, ExpressionWrapper, DecimalField, Max
from django.utils import timezone

from stores.models import Store
from warehouse.models import Order, OrderItem, Customer, Product
from analytics.models import (
    DailyRevenue, ProductSalesSummary, CategoryRevenueSummary,
    LocationRevenueSummary, InventoryMetric, RFMScore, KPISnapshot,
)

logger = logging.getLogger(__name__)


@shared_task
def run_analytics_for_all_stores():
    store_ids = list(Store.objects.filter(is_active=True).values_list('id', flat=True))
    for store_id in store_ids:
        run_all_analytics.delay(store_id)
    logger.info(f"Dispatched analytics for {len(store_ids)} stores")


@shared_task
def run_all_analytics(store_id: int):
    calculate_daily_revenue.delay(store_id)
    calculate_product_sales.delay(store_id)
    calculate_category_revenue.delay(store_id)
    calculate_location_revenue.delay(store_id)
    calculate_inventory_metrics.delay(store_id)
    calculate_rfm.delay(store_id)
    calculate_kpi_snapshot.delay(store_id)


# ── Daily revenue ─────────────────────────────────────────────────────────────

@shared_task
def calculate_daily_revenue(store_id: int):
    store = Store.objects.get(id=store_id)
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
        .annotate(rev=Sum('total_price'), orders=Count('id'), aov=Avg('total_price'))
        .order_by('day')
    )

    with transaction.atomic():
        for row in rows:
            cost = (
                OrderItem.objects.filter(
                    order__store=store,
                    order__financial_status=Order.STATUS_PAID,
                    order__processed_at__date=row['day'],
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
            DailyRevenue.objects.update_or_create(
                store=store, date=row['day'],
                defaults={
                    'total_revenue':   row['rev'] or 0,
                    'total_profit':    (row['rev'] or Decimal('0')) - cost,
                    'total_orders':    row['orders'] or 0,
                    'avg_order_value': row['aov'] or 0,
                },
            )
    logger.info(f"Daily revenue calculated for {store.shop_domain}")


# ── Product sales ─────────────────────────────────────────────────────────────

@shared_task
def calculate_product_sales(store_id: int, days: int = 30):
    store        = Store.objects.get(id=store_id)
    period_end   = date.today()
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
        .annotate(revenue=Sum('line_total'), units=Sum('quantity'))
    )

    with transaction.atomic():
        for row in rows:
            revenue = row['revenue'] or Decimal('0')
            units   = row['units'] or 0
            cost    = (
                OrderItem.objects.filter(
                    order__store=store,
                    order__financial_status=Order.STATUS_PAID,
                    order__processed_at__date__gte=period_start,
                    product_id=row['product'],
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
            profit = revenue - cost
            margin = float(profit / revenue * 100) if revenue > 0 else 0.0

            ProductSalesSummary.objects.update_or_create(
                store=store, product_id=row['product'], period_start=period_start,
                defaults={
                    'period_end':    period_end,
                    'total_revenue': revenue,
                    'total_profit':  profit,
                    'units_sold':    units,
                    'margin_pct':    margin,
                },
            )
    logger.info(f"Product sales calculated for {store.shop_domain}")


# ── Category revenue ──────────────────────────────────────────────────────────

@shared_task
def calculate_category_revenue(store_id: int, days: int = 30):
    store        = Store.objects.get(id=store_id)
    period_end   = date.today()
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

    total = sum(float(r['revenue'] or 0) for r in rows)
    with transaction.atomic():
        for row in rows:
            cat = row['category'] or 'Uncategorized'
            rev = row['revenue'] or Decimal('0')
            pct = float(rev / total * 100) if total > 0 else 0.0
            CategoryRevenueSummary.objects.update_or_create(
                store=store, category=cat, period_start=period_start,
                defaults={'period_end': period_end, 'total_revenue': rev, 'revenue_pct': pct},
            )
    logger.info(f"Category revenue calculated for {store.shop_domain}")


# ── Location revenue ──────────────────────────────────────────────────────────

@shared_task
def calculate_location_revenue(store_id: int, days: int = 30):
    store        = Store.objects.get(id=store_id)
    period_end   = date.today()
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
        .annotate(revenue=Sum('total_price'), orders=Count('id'))
    )

    with transaction.atomic():
        for row in rows:
            LocationRevenueSummary.objects.update_or_create(
                store=store, location_name=row['location_name'], period_start=period_start,
                defaults={
                    'period_end':    period_end,
                    'total_revenue': row['revenue'] or 0,
                    'total_orders':  row['orders'] or 0,
                },
            )
    logger.info(f"Location revenue calculated for {store.shop_domain}")


# ── Inventory metrics ─────────────────────────────────────────────────────────

@shared_task
def calculate_inventory_metrics(store_id: int):
    store        = Store.objects.get(id=store_id)
    lookback     = 30
    since        = date.today() - timedelta(days=lookback)

    sales = (
        OrderItem.objects.filter(
            order__store=store,
            order__financial_status=Order.STATUS_PAID,
            order__processed_at__date__gte=since,
            variant__isnull=False,
        )
        .values('variant_id')
        .annotate(units=Sum('quantity'), last_sale=Max('order__processed_at'))
    )
    sales_map = {r['variant_id']: (r['units'] or 0, r['last_sale']) for r in sales}

    from warehouse.models import ProductVariant
    variants = ProductVariant.objects.filter(
        product__store=store, product__status='active'
    ).select_related('product')

    with transaction.atomic():
        for variant in variants:
            stock             = variant.inventory_quantity or 0
            units_sold, last_sale = sales_map.get(variant.id, (0, None))
            avg_daily         = units_sold / lookback if units_sold > 0 else 0.0
            days_cover        = (stock / avg_daily) if avg_daily > 0 else 999.0
            days_since_sale   = None
            if last_sale:
                days_since_sale = (timezone.now() - last_sale).days

            if avg_daily > 0 and days_cover <= 7:
                status = InventoryMetric.STATUS_CRITICAL
            elif avg_daily > 0 and days_cover <= 14:
                status = InventoryMetric.STATUS_LOW
            elif avg_daily == 0 and (days_since_sale is None or days_since_sale > 60):
                status = InventoryMetric.STATUS_DEAD
            else:
                status = InventoryMetric.STATUS_OK

            InventoryMetric.objects.update_or_create(
                store=store, variant_id=variant.id,
                defaults={
                    'product':            variant.product,
                    'product_title':      variant.product.title,
                    'variant_title':      variant.title or '',
                    'sku':                variant.sku or '',
                    'stock_quantity':     stock,
                    'avg_daily_sales':    round(avg_daily, 2),
                    'days_cover':         round(min(days_cover, 999.0), 1),
                    'status':             status,
                    'last_sold_days_ago': days_since_sale,
                },
            )
    logger.info(f"Inventory metrics calculated for {store.shop_domain}")


# ── RFM ───────────────────────────────────────────────────────────────────────

@shared_task
def calculate_rfm(store_id: int):
    store     = Store.objects.get(id=store_id)
    now       = timezone.now()
    customers = Customer.objects.filter(store=store)

    with transaction.atomic():
        for customer in customers.iterator(chunk_size=500):
            orders    = Order.objects.filter(
                store=store, customer=customer,
                financial_status=Order.STATUS_PAID,
                cancelled_at__isnull=True,
            )
            frequency = orders.count()
            monetary  = orders.aggregate(total=Sum('total_price'))['total'] or Decimal('0')
            last_order = orders.order_by('-processed_at').values_list('processed_at', flat=True).first()
            recency    = (now - last_order).days if last_order else 999

            def score_r(d):
                return 5 if d<=7 else 4 if d<=30 else 3 if d<=60 else 2 if d<=120 else 1
            def score_f(c):
                return 5 if c>=10 else 4 if c>=5 else 3 if c>=3 else 2 if c>=2 else 1
            def score_m(v):
                return 5 if v>=1000 else 4 if v>=500 else 3 if v>=200 else 2 if v>=50 else 1

            def segment(r, f, m):
                if m >= 200 and f >= 3 and r <= 30:  return 'VIP'
                if f >= 2 and r <= 60:               return 'Loyal'
                if f == 1 and r <= 30:               return 'New'
                if r <= 120:                          return 'At Risk'
                return 'Lost'

            seg = segment(recency, frequency, float(monetary))

            RFMScore.objects.update_or_create(
                store=store, customer=customer,
                defaults={
                    'recency': recency, 'frequency': frequency, 'monetary': monetary,
                    'recency_score':   score_r(recency),
                    'frequency_score': score_f(frequency),
                    'monetary_score':  score_m(float(monetary)),
                    'segment':         seg,
                },
            )
            customer.rfm_segment = seg
            customer.save(update_fields=['rfm_segment'])

    logger.info(f"RFM calculated for {customers.count()} customers in {store.shop_domain}")


# ── KPI Snapshot ──────────────────────────────────────────────────────────────

@shared_task
def calculate_kpi_snapshot(store_id: int):
    store     = Store.objects.get(id=store_id)
    today     = date.today()
    start_30  = today - timedelta(days=30)
    start_60  = today - timedelta(days=60)

    def period_stats(date_from, date_to):
        qs  = Order.objects.filter(
            store=store, financial_status=Order.STATUS_PAID,
            cancelled_at__isnull=True,
            processed_at__date__gte=date_from,
            processed_at__date__lt=date_to,
        )
        agg = qs.aggregate(rev=Sum('total_price'), orders=Count('id'), aov=Avg('total_price'))
        return (agg['rev'] or Decimal('0'), agg['orders'] or 0, agg['aov'] or Decimal('0'))

    cur_rev, cur_orders, cur_aov   = period_stats(start_30, today)
    prev_rev, prev_orders, prev_aov = period_stats(start_60, start_30)

    def pct(cur, prev):
        if prev == 0:
            return 100.0 if cur > 0 else 0.0
        return round(float((cur - prev) / prev * 100), 1)

    def get_cost(date_from, date_to):
        return (
            OrderItem.objects.filter(
                order__store=store,
                order__financial_status=Order.STATUS_PAID,
                order__processed_at__date__gte=date_from,
                order__processed_at__date__lt=date_to,
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

    cur_profit  = cur_rev  - get_cost(start_30, today)
    prev_profit = prev_rev - get_cost(start_60, start_30)

    total_customers = Customer.objects.filter(store=store).count()
    repeat          = Customer.objects.filter(store=store, orders_count__gte=2).count()
    repeat_rate     = round(repeat / total_customers * 100, 1) if total_customers > 0 else 0.0

    KPISnapshot.objects.update_or_create(
        store=store,
        defaults={
            'revenue_30d':          cur_rev,
            'revenue_prev_30d':     prev_rev,
            'revenue_change_pct':   pct(cur_rev, prev_rev),
            'profit_30d':           cur_profit,
            'profit_change_pct':    pct(cur_profit, prev_profit),
            'orders_30d':           cur_orders,
            'orders_change_pct':    pct(cur_orders, prev_orders),
            'aov_30d':              cur_aov,
            'aov_change_pct':       pct(cur_aov, prev_aov),
            'total_customers':      total_customers,
            'repeat_purchase_rate': repeat_rate,
        },
    )
    logger.info(f"KPI snapshot updated for {store.shop_domain}: ${cur_rev:.2f} revenue")
