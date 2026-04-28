from django.contrib import admin
from .models import Product, ProductVariant, Customer, Order, OrderItem, Inventory, Location


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['title', 'vendor', 'product_type', 'status', 'store']
    list_filter = ['status', 'store', 'product_type']
    search_fields = ['title', 'vendor', 'shopify_product_id']


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['email', 'full_name', 'orders_count', 'total_spent', 'rfm_segment', 'store']
    list_filter = ['rfm_segment', 'store']
    search_fields = ['email', 'first_name', 'last_name']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'store', 'customer', 'total_price', 'financial_status', 'processed_at']
    list_filter = ['financial_status', 'store']
    search_fields = ['shopify_order_id', 'order_number', 'email']
    select_related = True


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ['variant', 'location', 'stock_quantity', 'updated_at']
    list_filter = ['location']
