from django.db import models
from stores.models import Store


class Alert(models.Model):
    SEVERITY_CRITICAL = 'critical'
    SEVERITY_WARNING = 'warning'
    SEVERITY_INFO = 'info'
    SEVERITY_SUCCESS = 'success'
    SEVERITY_CHOICES = [
        (SEVERITY_CRITICAL, 'Critical'),
        (SEVERITY_WARNING, 'Warning'),
        (SEVERITY_INFO, 'Info'),
        (SEVERITY_SUCCESS, 'Opportunity'),
    ]

    CATEGORY_STOCKOUT = 'stockout'
    CATEGORY_REVENUE = 'revenue'
    CATEGORY_CUSTOMER = 'customer'
    CATEGORY_INVENTORY = 'inventory'
    CATEGORY_OPPORTUNITY = 'opportunity'
    CATEGORY_CHOICES = [
        (CATEGORY_STOCKOUT, 'Stockout'),
        (CATEGORY_REVENUE, 'Revenue'),
        (CATEGORY_CUSTOMER, 'Customer'),
        (CATEGORY_INVENTORY, 'Inventory'),
        (CATEGORY_OPPORTUNITY, 'Opportunity'),
    ]

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='alerts')
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, db_index=True)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, db_index=True)
    title = models.CharField(max_length=500)
    description = models.TextField()
    action_label = models.CharField(max_length=100, blank=True)
    action_url = models.CharField(max_length=255, blank=True)
    is_resolved = models.BooleanField(default=False, db_index=True)
    dedup_key = models.CharField(max_length=255, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'insights_alerts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['store', 'severity', 'is_resolved']),
            models.Index(fields=['store', 'is_resolved']),
        ]

    def __str__(self):
        return f"[{self.severity.upper()}] {self.title}"


class Insight(models.Model):
    """Natural language insight summaries shown in the dashboard."""
    TYPE_REVENUE = 'revenue'
    TYPE_PRODUCT = 'product'
    TYPE_CUSTOMER = 'customer'
    TYPE_INVENTORY = 'inventory'
    TYPE_OPPORTUNITY = 'opportunity'
    TYPE_CHOICES = [
        (TYPE_REVENUE, 'Revenue'),
        (TYPE_PRODUCT, 'Product'),
        (TYPE_CUSTOMER, 'Customer'),
        (TYPE_INVENTORY, 'Inventory'),
        (TYPE_OPPORTUNITY, 'Opportunity'),
    ]

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='insights')
    insight_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    severity = models.CharField(max_length=20, default='info')
    title = models.CharField(max_length=500)
    description = models.TextField()
    action = models.CharField(max_length=255, blank=True)
    value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'insights_insights'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.insight_type}: {self.title}"
