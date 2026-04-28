from django.db import models
from stores.models import Store


class RawShopifyData(models.Model):
    """Abstract base for all raw Shopify response storage."""
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    shopify_id = models.BigIntegerField(db_index=True)
    raw_json = models.JSONField()
    received_at = models.DateTimeField(auto_now_add=True)
    is_processed = models.BooleanField(default=False, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True


class RawOrder(RawShopifyData):
    """
    Shopify order response stored verbatim.
    Never modify this data — it is the source of truth for reprocessing.
    """
    class Meta:
        db_table = 'raw_orders'
        unique_together = ('store', 'shopify_id')
        indexes = [
            models.Index(fields=['store', 'is_processed']),
            models.Index(fields=['received_at']),
        ]

    def __str__(self):
        return f"RawOrder #{self.shopify_id} (store={self.store_id})"


class RawProduct(RawShopifyData):
    """Shopify product response stored verbatim."""
    class Meta:
        db_table = 'raw_products'
        unique_together = ('store', 'shopify_id')
        indexes = [
            models.Index(fields=['store', 'is_processed']),
        ]

    def __str__(self):
        return f"RawProduct #{self.shopify_id}"


class RawCustomer(RawShopifyData):
    """Shopify customer response stored verbatim."""
    class Meta:
        db_table = 'raw_customers'
        unique_together = ('store', 'shopify_id')
        indexes = [
            models.Index(fields=['store', 'is_processed']),
        ]

    def __str__(self):
        return f"RawCustomer #{self.shopify_id}"


class RawInventoryLevel(models.Model):
    """Shopify inventory level snapshot."""
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    shopify_inventory_item_id = models.BigIntegerField()
    shopify_location_id = models.BigIntegerField()
    available = models.IntegerField(default=0)
    raw_json = models.JSONField()
    received_at = models.DateTimeField(auto_now_add=True)
    is_processed = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = 'raw_inventory_levels'
        indexes = [
            models.Index(fields=['store', 'shopify_inventory_item_id']),
        ]

    def __str__(self):
        return f"RawInventory item={self.shopify_inventory_item_id} loc={self.shopify_location_id}"


class SyncLog(models.Model):
    """Audit log for every sync run."""
    SYNC_FULL = 'full'
    SYNC_INCREMENTAL = 'incremental'
    SYNC_WEBHOOK = 'webhook'
    SYNC_TYPE_CHOICES = [
        (SYNC_FULL, 'Full Sync'),
        (SYNC_INCREMENTAL, 'Incremental Sync'),
        (SYNC_WEBHOOK, 'Webhook'),
    ]

    STATUS_RUNNING = 'running'
    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_RUNNING, 'Running'),
        (STATUS_SUCCESS, 'Success'),
        (STATUS_FAILED, 'Failed'),
    ]

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='sync_logs')
    sync_type = models.CharField(max_length=20, choices=SYNC_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_RUNNING)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    orders_synced = models.IntegerField(default=0)
    products_synced = models.IntegerField(default=0)
    customers_synced = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = 'sync_logs'
        ordering = ['-started_at']

    def __str__(self):
        return f"SyncLog {self.sync_type} {self.status} ({self.store})"
