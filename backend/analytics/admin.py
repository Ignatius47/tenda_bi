from django.contrib import admin
from .models import DailyRevenue, ProductSalesSummary, RFMScore, InventoryMetric, KPISnapshot


@admin.register(DailyRevenue)
class DailyRevenueAdmin(admin.ModelAdmin):
    list_display = ['store', 'date', 'total_revenue', 'total_profit', 'total_orders', 'avg_order_value']
    list_filter = ['store']
    ordering = ['-date']


@admin.register(RFMScore)
class RFMScoreAdmin(admin.ModelAdmin):
    list_display = ['customer', 'segment', 'recency', 'frequency', 'monetary', 'computed_at']
    list_filter = ['segment', 'store']
    search_fields = ['customer__email']


@admin.register(InventoryMetric)
class InventoryMetricAdmin(admin.ModelAdmin):
    list_display = ['product_title', 'sku', 'stock_quantity', 'avg_daily_sales', 'days_cover', 'status']
    list_filter = ['status', 'store']
    search_fields = ['product_title', 'sku']


@admin.register(KPISnapshot)
class KPISnapshotAdmin(admin.ModelAdmin):
    list_display = ['store', 'revenue_30d', 'profit_30d', 'orders_30d', 'aov_30d', 'computed_at']
    readonly_fields = ['computed_at']
