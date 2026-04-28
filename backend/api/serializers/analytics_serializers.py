from rest_framework import serializers
from analytics.models import (
    DailyRevenue, ProductSalesSummary, CategoryRevenueSummary,
    LocationRevenueSummary, InventoryMetric, RFMScore, KPISnapshot,
)
from insights.models import Alert, Insight
from warehouse.models import Customer, Product


class KPISnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = KPISnapshot
        fields = [
            'revenue_30d', 'revenue_prev_30d', 'revenue_change_pct',
            'profit_30d', 'profit_change_pct',
            'orders_30d', 'orders_change_pct',
            'aov_30d', 'aov_change_pct',
            'total_customers', 'repeat_purchase_rate',
            'computed_at',
        ]


class DailyRevenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyRevenue
        fields = ['date', 'total_revenue', 'total_profit', 'total_orders', 'avg_order_value']


class ProductSalesSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source='product.title')
    category = serializers.CharField(source='product.product_type')
    trend_pct = serializers.SerializerMethodField()

    class Meta:
        model = ProductSalesSummary
        fields = [
            'product_id', 'title', 'category',
            'total_revenue', 'total_profit', 'units_sold',
            'margin_pct', 'trend_pct',
        ]

    def get_trend_pct(self, obj):
        # Trend vs previous period is computed at analytics time
        # Return 0 here; full trend is available via the trends endpoint
        return getattr(obj, 'trend_pct', 0.0)


class CategoryRevenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryRevenueSummary
        fields = ['category', 'total_revenue', 'revenue_pct']


class LocationRevenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationRevenueSummary
        fields = ['location_name', 'total_revenue', 'total_orders']


class InventoryMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryMetric
        fields = [
            'variant_id', 'product_title', 'variant_title', 'sku',
            'stock_quantity', 'avg_daily_sales', 'days_cover',
            'status', 'last_sold_days_ago', 'computed_at',
        ]


class RFMSegmentSummarySerializer(serializers.Serializer):
    """Aggregated RFM segment counts and revenue percentages."""
    segment = serializers.CharField()
    count = serializers.IntegerField()
    revenue_pct = serializers.FloatField()
    avg_ltv = serializers.FloatField()
    avg_orders = serializers.FloatField()


class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = [
            'id', 'severity', 'category', 'title', 'description',
            'action_label', 'action_url', 'is_resolved',
            'metadata', 'created_at',
        ]


class InsightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Insight
        fields = [
            'id', 'insight_type', 'severity', 'title',
            'description', 'action', 'value', 'created_at',
        ]


class CustomerSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Customer
        fields = [
            'id', 'shopify_customer_id', 'email', 'full_name',
            'first_name', 'last_name', 'city', 'country',
            'orders_count', 'total_spent',
            'rfm_segment', 'rfm_recency_score', 'rfm_frequency_score', 'rfm_monetary_score',
            'last_order_date', 'shopify_created_at',
        ]
