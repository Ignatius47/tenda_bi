from django.contrib import admin
from .models import RawOrder, RawProduct, RawCustomer, SyncLog


@admin.register(RawOrder)
class RawOrderAdmin(admin.ModelAdmin):
    list_display  = ['shopify_id', 'store', 'is_processed', 'received_at']
    list_filter   = ['is_processed', 'store']
    readonly_fields = ['raw_json', 'received_at']


@admin.register(RawProduct)
class RawProductAdmin(admin.ModelAdmin):
    list_display  = ['shopify_id', 'store', 'is_processed', 'received_at']
    list_filter   = ['is_processed', 'store']
    readonly_fields = ['raw_json', 'received_at']


@admin.register(RawCustomer)
class RawCustomerAdmin(admin.ModelAdmin):
    list_display  = ['shopify_id', 'store', 'is_processed', 'received_at']
    list_filter   = ['is_processed', 'store']
    readonly_fields = ['raw_json', 'received_at']


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display  = ['store', 'sync_type', 'status', 'orders_synced', 'products_synced', 'customers_synced', 'started_at']
    list_filter   = ['sync_type', 'status', 'store']
    readonly_fields = ['started_at', 'finished_at']
