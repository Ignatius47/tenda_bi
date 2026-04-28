import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task
def cleanup_old_alerts():
    """Remove resolved alerts older than 30 days."""
    from insights.models import Alert
    cutoff = timezone.now() - timedelta(days=30)
    deleted, _ = Alert.objects.filter(
        is_resolved=True,
        resolved_at__lt=cutoff,
    ).delete()
    logger.info(f"Cleaned up {deleted} old alerts")


@shared_task
def cleanup_processed_raw_data():
    """
    Optionally archive raw data older than 90 days to keep the DB lean.
    Only delete after confirming warehouse transformation was successful.
    """
    from raw_data.models import RawOrder, RawProduct, RawCustomer
    cutoff = timezone.now() - timedelta(days=90)

    for model in [RawOrder, RawProduct, RawCustomer]:
        deleted, _ = model.objects.filter(
            is_processed=True,
            processed_at__lt=cutoff,
        ).delete()
        logger.info(f"Deleted {deleted} old {model.__name__} records")
