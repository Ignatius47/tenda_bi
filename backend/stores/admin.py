from django.contrib import admin
from .models import Store


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ['shop_domain', 'shop_name', 'user', 'currency', 'is_active', 'last_synced_at', 'installed_at']
    list_filter = ['is_active', 'currency']
    search_fields = ['shop_domain', 'shop_name', 'user__email']
    readonly_fields = ['installed_at', 'last_synced_at']
