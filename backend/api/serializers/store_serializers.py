from rest_framework import serializers
from stores.models import Store
from raw_data.models import SyncLog


class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = [
            'id', 'shop_domain', 'shop_name', 'currency',
            'timezone', 'is_active', 'installed_at', 'last_synced_at',
        ]
        read_only_fields = fields


class SyncLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncLog
        fields = [
            'id', 'sync_type', 'status', 'started_at', 'finished_at',
            'orders_synced', 'products_synced', 'customers_synced', 'error_message',
        ]
        read_only_fields = fields
