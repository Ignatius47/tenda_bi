import logging
from celery import shared_task
from django.utils import timezone as dj_timezone

from stores.models import Store
from raw_data.models import RawOrder, RawProduct, RawCustomer, RawInventoryLevel, SyncLog
from ingestion.services.shopify_client import ShopifyClient

logger = logging.getLogger(__name__)


# ── Full sync ─────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_full_sync(self, store_id: int):
    """Pull ALL Shopify data. Called once after OAuth install."""
    try:
        store = Store.objects.get(id=store_id, is_active=True)
    except Store.DoesNotExist:
        logger.error(f"Store {store_id} not found")
        return

    log = SyncLog.objects.create(store=store, sync_type=SyncLog.SYNC_FULL)

    try:
        client = ShopifyClient(store)

        products_count  = _ingest_products(store, client)
        customers_count = _ingest_customers(store, client)
        orders_count    = _ingest_orders(store, client, days_back=365)

        # Inventory is non-fatal
        try:
            _ingest_inventory(store, client)
        except Exception as e:
            logger.warning(f"Inventory sync skipped (non-fatal): {e}")

        log.status           = SyncLog.STATUS_SUCCESS
        log.products_synced  = products_count
        log.customers_synced = customers_count
        log.orders_synced    = orders_count
        log.finished_at      = dj_timezone.now()
        log.save()

        store.last_synced_at = dj_timezone.now()
        store.save(update_fields=['last_synced_at'])

        logger.info(
            f"Full sync complete for {store.shop_domain}: "
            f"{orders_count} orders, {products_count} products, {customers_count} customers"
        )

        # Chain to ETL
        from warehouse.tasks import transform_all
        transform_all.delay(store_id)

    except Exception as exc:
        log.status        = SyncLog.STATUS_FAILED
        log.error_message = str(exc)
        log.finished_at   = dj_timezone.now()
        log.save()
        logger.exception(f"Full sync failed for store {store_id}: {exc}")
        raise self.retry(exc=exc)


# ── Incremental sync ──────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def run_incremental_sync(self, store_id: int):
    """Pull only data changed since last sync. Runs every 15 min."""
    try:
        store = Store.objects.get(id=store_id, is_active=True)
    except Store.DoesNotExist:
        return

    log = SyncLog.objects.create(store=store, sync_type=SyncLog.SYNC_INCREMENTAL)

    try:
        client = ShopifyClient(store)

        if store.last_synced_at:
            delta     = dj_timezone.now() - store.last_synced_at
            days_back = max(1, delta.days + 1)
        else:
            days_back = 1

        products_count  = _ingest_products(store, client)
        customers_count = _ingest_customers(store, client)
        orders_count    = _ingest_orders(store, client, days_back=days_back)

        try:
            _ingest_inventory(store, client)
        except Exception as e:
            logger.warning(f"Inventory sync skipped (non-fatal): {e}")

        log.status           = SyncLog.STATUS_SUCCESS
        log.products_synced  = products_count
        log.customers_synced = customers_count
        log.orders_synced    = orders_count
        log.finished_at      = dj_timezone.now()
        log.save()

        store.last_synced_at = dj_timezone.now()
        store.save(update_fields=['last_synced_at'])

        logger.info(f"Incremental sync complete for {store.shop_domain}: {orders_count} orders")

        from warehouse.tasks import transform_all
        transform_all.delay(store_id)

    except Exception as exc:
        log.status        = SyncLog.STATUS_FAILED
        log.error_message = str(exc)
        log.finished_at   = dj_timezone.now()
        log.save()
        logger.exception(f"Incremental sync failed for store {store_id}")
        raise self.retry(exc=exc)


@shared_task
def sync_all_active_stores():
    """Dispatched by Celery Beat every 15 minutes."""
    store_ids = list(Store.objects.filter(is_active=True).values_list('id', flat=True))
    for store_id in store_ids:
        run_incremental_sync.delay(store_id)
    logger.info(f"Dispatched incremental sync for {len(store_ids)} stores")


# ── Webhook handlers ──────────────────────────────────────────────────────────

@shared_task
def handle_order_webhook(store_id: int, order_data: dict):
    try:
        store      = Store.objects.get(id=store_id)
        shopify_id = order_data.get('id')
        if not shopify_id:
            return
        RawOrder.objects.update_or_create(
            store=store, shopify_id=shopify_id,
            defaults={'raw_json': order_data, 'is_processed': False},
        )
        from warehouse.tasks import transform_single_order
        transform_single_order.delay(store_id, shopify_id)
    except Exception as e:
        logger.exception(f"Webhook order failed: {e}")


@shared_task
def handle_product_webhook(store_id: int, product_data: dict):
    try:
        store      = Store.objects.get(id=store_id)
        shopify_id = product_data.get('id')
        if not shopify_id:
            return
        RawProduct.objects.update_or_create(
            store=store, shopify_id=shopify_id,
            defaults={'raw_json': product_data, 'is_processed': False},
        )
        from warehouse.tasks import transform_single_product
        transform_single_product.delay(store_id, shopify_id)
    except Exception as e:
        logger.exception(f"Webhook product failed: {e}")


@shared_task
def handle_inventory_webhook(store_id: int, inventory_data: dict):
    try:
        store = Store.objects.get(id=store_id)
        RawInventoryLevel.objects.create(
            store=store,
            shopify_inventory_item_id=inventory_data.get('inventory_item_id', 0),
            shopify_location_id=inventory_data.get('location_id', 0),
            available=inventory_data.get('available', 0),
            raw_json=inventory_data,
            is_processed=False,
        )
        from warehouse.tasks import transform_inventory
        transform_inventory.delay(store_id)
    except Exception as e:
        logger.exception(f"Webhook inventory failed: {e}")


# ── Internal helpers ──────────────────────────────────────────────────────────

def _ingest_products(store: Store, client: ShopifyClient) -> int:
    count = 0
    for product in client.iter_products():
        RawProduct.objects.update_or_create(
            store=store, shopify_id=product['id'],
            defaults={'raw_json': product, 'is_processed': False},
        )
        count += 1
    logger.info(f"Ingested {count} products for {store.shop_domain}")
    return count


def _ingest_customers(store: Store, client: ShopifyClient) -> int:
    count = 0
    for customer in client.iter_customers():
        RawCustomer.objects.update_or_create(
            store=store, shopify_id=customer['id'],
            defaults={'raw_json': customer, 'is_processed': False},
        )
        count += 1
    logger.info(f"Ingested {count} customers for {store.shop_domain}")
    return count


def _ingest_orders(store: Store, client: ShopifyClient, days_back: int = 365) -> int:
    count = 0
    for order in client.iter_orders(days_back=days_back):
        RawOrder.objects.update_or_create(
            store=store, shopify_id=order['id'],
            defaults={'raw_json': order, 'is_processed': False},
        )
        count += 1
    logger.info(f"Ingested {count} orders for {store.shop_domain}")
    return count


def _ingest_inventory(store: Store, client: ShopifyClient):
    """Pull inventory — skips locations that return errors."""
    try:
        locations = client.get_locations()
    except Exception as e:
        logger.warning(f"Could not fetch locations for {store.shop_domain}: {e}")
        return

    for location in locations:
        try:
            levels = client.get_inventory_levels(location['id'])
            for level in levels:
                RawInventoryLevel.objects.update_or_create(
                    store=store,
                    shopify_inventory_item_id=level.get('inventory_item_id'),
                    shopify_location_id=level.get('location_id'),
                    defaults={
                        'available':    level.get('available', 0),
                        'raw_json':     level,
                        'is_processed': False,
                    },
                )
        except Exception as e:
            logger.warning(f"Skipping inventory for location {location.get('id')}: {e}")
            continue

    logger.info(f"Inventory sync complete for {store.shop_domain}")
