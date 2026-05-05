import logging
from celery import shared_task
from stores.models import Store
from insights.services import InsightGenerator

logger = logging.getLogger(__name__)


@shared_task
def generate_insights_for_all_stores():
    for store_id in Store.objects.filter(is_active=True).values_list('id', flat=True):
        generate_insights_for_store.delay(store_id)


@shared_task(bind=True, max_retries=2)
def generate_insights_for_store(self, store_id: int):
    try:
        store = Store.objects.get(id=store_id, is_active=True)
        InsightGenerator(store).run()
    except Store.DoesNotExist:
        logger.error(f"Store {store_id} not found")
    except Exception as exc:
        logger.exception(f"Insight generation failed for store {store_id}")
        raise self.retry(exc=exc)
