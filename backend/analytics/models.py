from django.db import models
from stores.models import Store
from warehouse.models import Product, Customer


# ── Revenue summaries ─────────────────────────────────────────────────────────

class DailyRevenue(models.Model):
    """Precomputed daily revenue per store. Powers the revenue trend chart."""
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='daily_revenues')
    date = models.DateField(db_index=True)
    total_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_profit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_orders = models.IntegerField(default=0)
    avg_order_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        db_table = 'analytics_daily_revenue'
        unique_together = ('store', 'date')
        ordering = ['date']
        indexes = [
            models.Index(fields=['store', 'date']),
        ]

    def __str__(self):
        return f"{self.store} {self.date}: ${self.total_revenue}"


class ProductSalesSummary(models.Model):
    """Precomputed product revenue and units — updated daily."""
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sales_summary')
    period_start = models.DateField(db_index=True)
    period_end = models.DateField()
    total_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_profit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    units_sold = models.IntegerField(default=0)
    margin_pct = models.FloatField(default=0)

    class Meta:
        db_table = 'analytics_product_sales'
        unique_together = ('store', 'product', 'period_start')
        indexes = [
            models.Index(fields=['store', 'period_start']),
        ]


class CategoryRevenueSummary(models.Model):
    """Revenue aggregated by product category per period."""
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    category = models.CharField(max_length=255)
    period_start = models.DateField(db_index=True)
    period_end = models.DateField()
    total_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    revenue_pct = models.FloatField(default=0)

    class Meta:
        db_table = 'analytics_category_revenue'
        unique_together = ('store', 'category', 'period_start')


class LocationRevenueSummary(models.Model):
    """Revenue by store location per period."""
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    location_name = models.CharField(max_length=255)
    period_start = models.DateField(db_index=True)
    period_end = models.DateField()
    total_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_orders = models.IntegerField(default=0)

    class Meta:
        db_table = 'analytics_location_revenue'
        unique_together = ('store', 'location_name', 'period_start')


# ── Inventory metrics ─────────────────────────────────────────────────────────

class InventoryMetric(models.Model):
    """Per-variant inventory health metrics — recomputed daily."""
    STATUS_CRITICAL = 'critical'
    STATUS_LOW = 'low'
    STATUS_OK = 'ok'
    STATUS_DEAD = 'dead_stock'
    STATUS_CHOICES = [
        (STATUS_CRITICAL, 'Critical'),
        (STATUS_LOW, 'Low'),
        (STATUS_OK, 'Healthy'),
        (STATUS_DEAD, 'Dead Stock'),
    ]

    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant_id = models.IntegerField(db_index=True)
    product_title = models.CharField(max_length=500)
    variant_title = models.CharField(max_length=255, blank=True)
    sku = models.CharField(max_length=255, blank=True)
    stock_quantity = models.IntegerField(default=0)
    avg_daily_sales = models.FloatField(default=0)
    days_cover = models.FloatField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OK, db_index=True)
    last_sold_days_ago = models.IntegerField(null=True, blank=True)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'analytics_inventory_metrics'
        unique_together = ('store', 'variant_id')
        indexes = [
            models.Index(fields=['store', 'status']),
        ]


# ── Customer RFM ──────────────────────────────────────────────────────────────

class RFMScore(models.Model):
    """RFM scores and segment per customer — computed by analytics engine."""
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='rfm_score')
    recency = models.IntegerField(default=0)        # days since last order
    frequency = models.IntegerField(default=0)      # total orders
    monetary = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    recency_score = models.IntegerField(default=1)  # 1–5
    frequency_score = models.IntegerField(default=1)
    monetary_score = models.IntegerField(default=1)
    segment = models.CharField(max_length=50, blank=True, db_index=True)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'analytics_rfm_scores'
        indexes = [
            models.Index(fields=['store', 'segment']),
        ]

    def __str__(self):
        return f"RFM {self.customer} → {self.segment}"


# ── KPI snapshot ─────────────────────────────────────────────────────────────

class KPISnapshot(models.Model):
    """
    Latest KPI values per store. One row per store.
    Updated after each analytics run.
    """
    store = models.OneToOneField(Store, on_delete=models.CASCADE, related_name='kpi_snapshot')
    # Revenue
    revenue_30d = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    revenue_prev_30d = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    revenue_change_pct = models.FloatField(default=0)
    # Profit
    profit_30d = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    profit_change_pct = models.FloatField(default=0)
    # Orders
    orders_30d = models.IntegerField(default=0)
    orders_change_pct = models.FloatField(default=0)
    # AOV
    aov_30d = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    aov_change_pct = models.FloatField(default=0)
    # Customers
    total_customers = models.IntegerField(default=0)
    repeat_purchase_rate = models.FloatField(default=0)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'analytics_kpi_snapshot'
