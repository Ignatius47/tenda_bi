from django.contrib import admin
from .models import DailyRevenue, RFMScore, InventoryMetric, KPISnapshot


@admin.register(DailyRevenue)
class DailyRevenueAdmin(admin.ModelAdmin):
    list_display = ['store', 'date', 'total_revenue', 'total_profit', 'total_orders']
    list_filter  = ['store']
    ordering     = ['-date']


@admin.register(RFMScore)
class RFMScoreAdmin(admin.ModelAdmin):
    list_display = ['customer', 'segment', 'recency', 'frequency', 'monetary']
    list_filter  = ['segment', 'store']


@admin.register(InventoryMetric)
class InventoryMetricAdmin(admin.ModelAdmin):
    list_display = ['product_title', 'sku', 'stock_quantity', 'avg_daily_sales', 'days_cover', 'status']
    list_filter  = ['status', 'store']


@admin.register(KPISnapshot)
class KPISnapshotAdmin(admin.ModelAdmin):
    list_display = ['store', 'revenue_30d', 'profit_30d', 'orders_30d', 'computed_at']
