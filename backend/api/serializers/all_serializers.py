from rest_framework import serializers
from django.contrib.auth import authenticate
from users.models import User
from stores.models import Store
from raw_data.models import SyncLog
from analytics.models import (
    KPISnapshot, DailyRevenue, ProductSalesSummary,
    CategoryRevenueSummary, LocationRevenueSummary, InventoryMetric,
)
from insights.models import Alert, Insight
from warehouse.models import Customer


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model  = User
        fields = ['email', 'password', 'full_name']

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            full_name=validated_data.get('full_name', ''),
        )


class LoginSerializer(serializers.Serializer):
    email    = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        user = authenticate(username=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError('Invalid credentials.')
        if not user.is_active:
            raise serializers.ValidationError('Account disabled.')
        data['user'] = user
        return data


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model        = User
        fields       = ['id', 'email', 'full_name', 'role', 'shopify_auth', 'created_at']
        read_only_fields = ['id', 'created_at', 'shopify_auth']


# ── Store ─────────────────────────────────────────────────────────────────────

class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model        = Store
        fields       = ['id', 'shop_domain', 'shop_name', 'currency', 'timezone', 'is_active', 'installed_at', 'last_synced_at']
        read_only_fields = fields


class SyncLogSerializer(serializers.ModelSerializer):
    class Meta:
        model        = SyncLog
        fields       = ['id', 'sync_type', 'status', 'started_at', 'finished_at', 'orders_synced', 'products_synced', 'customers_synced', 'error_message']
        read_only_fields = fields


# ── Analytics ─────────────────────────────────────────────────────────────────

class KPISnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model  = KPISnapshot
        fields = [
            'revenue_30d', 'revenue_prev_30d', 'revenue_change_pct',
            'profit_30d', 'profit_change_pct',
            'orders_30d', 'orders_change_pct',
            'aov_30d', 'aov_change_pct',
            'total_customers', 'repeat_purchase_rate', 'computed_at',
        ]


class DailyRevenueSerializer(serializers.ModelSerializer):
    class Meta:
        model  = DailyRevenue
        fields = ['date', 'total_revenue', 'total_profit', 'total_orders', 'avg_order_value']


class ProductSalesSerializer(serializers.ModelSerializer):
    title     = serializers.CharField(source='product.title')
    category  = serializers.CharField(source='product.product_type')
    trend_pct = serializers.FloatField(default=0)

    class Meta:
        model  = ProductSalesSummary
        fields = ['product_id', 'title', 'category', 'total_revenue', 'total_profit', 'units_sold', 'margin_pct', 'trend_pct']


class CategoryRevenueSerializer(serializers.ModelSerializer):
    class Meta:
        model  = CategoryRevenueSummary
        fields = ['category', 'total_revenue', 'revenue_pct']


class LocationRevenueSerializer(serializers.ModelSerializer):
    class Meta:
        model  = LocationRevenueSummary
        fields = ['location_name', 'total_revenue', 'total_orders']


class InventoryMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model  = InventoryMetric
        fields = ['variant_id', 'product_title', 'variant_title', 'sku', 'stock_quantity', 'avg_daily_sales', 'days_cover', 'status', 'last_sold_days_ago']


class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Alert
        fields = ['id', 'severity', 'category', 'title', 'description', 'action_label', 'action_url', 'is_resolved', 'metadata', 'created_at']


class InsightSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Insight
        fields = ['id', 'insight_type', 'severity', 'title', 'description', 'action', 'value', 'created_at']


class CustomerSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model  = Customer
        fields = [
            'id', 'shopify_customer_id', 'email', 'full_name',
            'first_name', 'last_name', 'city', 'country',
            'orders_count', 'total_spent',
            'rfm_segment', 'last_order_date', 'shopify_created_at',
        ]
