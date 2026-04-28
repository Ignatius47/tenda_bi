from django.db import models
from django.conf import settings


class Store(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='stores',
    )
    shop_domain = models.CharField(max_length=255, unique=True, db_index=True)
    shop_name = models.CharField(max_length=255, blank=True)
    access_token = models.CharField(max_length=512)
    currency = models.CharField(max_length=10, default='USD')
    timezone = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    installed_at = models.DateTimeField(auto_now_add=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    # Shopify internal shop id
    shopify_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'stores'
        verbose_name = 'Store'

    def __str__(self):
        return self.shop_name or self.shop_domain

    @property
    def base_url(self):
     return f"https://{self.shop_domain}/admin/api/2024-10"
