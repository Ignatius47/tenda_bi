from django.db import models
from stores.models import Store


# ── Location ──────────────────────────────────────────────────────────────────

class Location(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='locations')
    shopify_location_id = models.BigIntegerField(db_index=True)
    name = models.CharField(max_length=255)
    address1 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'wh_locations'
        unique_together = ('store', 'shopify_location_id')

    def __str__(self):
        return f"{self.name} ({self.city})"


# ── Product ───────────────────────────────────────────────────────────────────

class Product(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='wh_products')
    shopify_product_id = models.BigIntegerField(db_index=True)
    title = models.CharField(max_length=500)
    vendor = models.CharField(max_length=255, blank=True)
    product_type = models.CharField(max_length=255, blank=True, db_index=True)
    tags = models.TextField(blank=True)
    status = models.CharField(max_length=50, default='active', db_index=True)
    shopify_created_at = models.DateTimeField(null=True, blank=True)
    shopify_updated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wh_products'
        unique_together = ('store', 'shopify_product_id')
        indexes = [
            models.Index(fields=['store', 'status']),
            models.Index(fields=['product_type']),
        ]

    def __str__(self):
        return self.title


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    shopify_variant_id = models.BigIntegerField(db_index=True)
    title = models.CharField(max_length=255, blank=True)
    sku = models.CharField(max_length=255, blank=True, db_index=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    compare_at_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    inventory_quantity = models.IntegerField(default=0)
    shopify_inventory_item_id = models.BigIntegerField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = 'wh_product_variants'
        unique_together = ('product', 'shopify_variant_id')

    def __str__(self):
        return f"{self.product.title} — {self.title}"

    @property
    def margin_pct(self):
        if self.price and self.price > 0:
            return float((self.price - self.cost) / self.price * 100)
        return 0.0


# ── Customer ──────────────────────────────────────────────────────────────────

class Customer(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='wh_customers')
    shopify_customer_id = models.BigIntegerField(db_index=True)
    email = models.EmailField(blank=True, db_index=True)
    first_name = models.CharField(max_length=255, blank=True)
    last_name  = models.CharField(max_length=255, blank=True)
    phone      = models.CharField(max_length=50, blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    orders_count = models.IntegerField(default=0)
    total_spent = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    accepts_marketing = models.BooleanField(default=False)
    tags = models.TextField(blank=True)
    # RFM — computed by analytics engine
    rfm_segment = models.CharField(max_length=50, blank=True, db_index=True)
    rfm_recency_score = models.IntegerField(null=True, blank=True)
    rfm_frequency_score = models.IntegerField(null=True, blank=True)
    rfm_monetary_score = models.IntegerField(null=True, blank=True)
    last_order_date = models.DateTimeField(null=True, blank=True)
    shopify_created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'wh_customers'
        unique_together = ('store', 'shopify_customer_id')
        indexes = [
            models.Index(fields=['store', 'rfm_segment']),
            models.Index(fields=['last_order_date']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} <{self.email}>"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email


# ── Order ─────────────────────────────────────────────────────────────────────

class Order(models.Model):
    STATUS_PAID = 'paid'
    STATUS_PENDING = 'pending'
    STATUS_REFUNDED = 'refunded'
    STATUS_VOIDED = 'voided'

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='wh_orders')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True)
    shopify_order_id = models.BigIntegerField(db_index=True)
    order_number = models.IntegerField(null=True, blank=True)
    email = models.EmailField(blank=True)
    financial_status = models.CharField(max_length=50, blank=True, db_index=True)
    fulfillment_status = models.CharField(max_length=50, blank=True, null=True)
    subtotal_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_discounts = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    shopify_created_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'wh_orders'
        unique_together = ('store', 'shopify_order_id')
        indexes = [
            models.Index(fields=['store', 'financial_status']),
            models.Index(fields=['store', 'processed_at']),
            models.Index(fields=['processed_at']),
        ]

    def __str__(self):
        return f"Order #{self.order_number or self.shopify_order_id}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    shopify_line_item_id = models.BigIntegerField(db_index=True)
    title = models.CharField(max_length=500, blank=True)
    variant_title = models.CharField(max_length=255, blank=True)
    sku = models.CharField(max_length=255, blank=True)
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        db_table = 'wh_order_items'
        unique_together = ('order', 'shopify_line_item_id')
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['variant']),
        ]

    def __str__(self):
        return f"{self.title} x{self.quantity}"


# ── Inventory ─────────────────────────────────────────────────────────────────

class Inventory(models.Model):
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='inventory_levels')
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='inventory_levels')
    stock_quantity = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'wh_inventory'
        unique_together = ('variant', 'location')
        indexes = [
            models.Index(fields=['variant']),
            models.Index(fields=['stock_quantity']),
        ]

    def __str__(self):
        return f"{self.variant} @ {self.location}: {self.stock_quantity}"
