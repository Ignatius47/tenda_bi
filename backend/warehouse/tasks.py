import logging
from datetime import datetime

from celery import shared_task
from django.utils.dateparse import parse_datetime
from django.utils import timezone

from stores.models import Store
from raw_data.models import RawOrder, RawProduct, RawCustomer, RawInventoryLevel
from warehouse.models import (
    Product, ProductVariant, Customer, Order, OrderItem,
    Inventory, Location,
)

logger = logging.getLogger(__name__)


def _parse_dt(value):
    """Safely parse a Shopify ISO datetime string."""
    if not value:
        return None
    try:
        return parse_datetime(value)
    except Exception:
        return None


def _safe_decimal(value, default=0):
    """Convert a value to float safely."""
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return float(default)


# ── Full transform (all unprocessed raw data for a store) ────────────────────

@shared_task
def transform_all(store_id: int):
    """
    Transform ALL unprocessed raw records for a store.
    Order: locations → products → customers → orders → inventory.
    """
    try:
        store = Store.objects.get(id=store_id)
    except Store.DoesNotExist:
        logger.error(f"transform_all: store {store_id} not found")
        return

    logger.info(f"Starting ETL transform for {store.shop_domain}")
    transform_products(store_id)
    transform_customers(store_id)
    transform_orders(store_id)
    transform_inventory(store_id)
    logger.info(f"ETL transform complete for {store.shop_domain}")
    from analytics.tasks import run_all_analytics
    run_all_analytics.delay(store_id)

# ── Products ──────────────────────────────────────────────────────────────────

@shared_task
def transform_products(store_id: int):
    """Raw products → wh_products + wh_product_variants."""
    store = Store.objects.get(id=store_id)
    raw_qs = RawProduct.objects.filter(store=store, is_processed=False)
    count = 0

    for raw in raw_qs.iterator(chunk_size=200):
        try:
            _transform_one_product(store, raw.raw_json)
            raw.is_processed = True
            raw.processed_at = timezone.now()
            raw.save(update_fields=['is_processed', 'processed_at'])
            count += 1
        except Exception as e:
            logger.warning(f"Failed to transform product {raw.shopify_id}: {e}")

    logger.info(f"Transformed {count} products for {store.shop_domain}")


def _transform_one_product(store: Store, data: dict):
    product, _ = Product.objects.update_or_create(
        store=store,
        shopify_product_id=data['id'],
        defaults={
            'title': data.get('title', ''),
            'vendor': data.get('vendor', ''),
            'product_type': data.get('product_type', ''),
            'tags': data.get('tags', ''),
            'status': data.get('status', 'active'),
            'shopify_created_at': _parse_dt(data.get('created_at')),
            'shopify_updated_at': _parse_dt(data.get('updated_at')),
        },
    )

    for v in data.get('variants', []):
        ProductVariant.objects.update_or_create(
            product=product,
            shopify_variant_id=v['id'],
            defaults={
                'title': v.get('title', ''),
                'sku': v.get('sku', ''),
                'price': _safe_decimal(v.get('price')),
                'compare_at_price': _safe_decimal(v.get('compare_at_price')) or None,
                'inventory_quantity': v.get('inventory_quantity', 0),
                'shopify_inventory_item_id': v.get('inventory_item_id'),
            },
        )


@shared_task
def transform_single_product(store_id: int, shopify_product_id: int):
    """Transform a single product (called from webhook handler)."""
    store = Store.objects.get(id=store_id)
    try:
        raw = RawProduct.objects.get(store=store, shopify_id=shopify_product_id)
        _transform_one_product(store, raw.raw_json)
        raw.is_processed = True
        raw.processed_at = timezone.now()
        raw.save(update_fields=['is_processed', 'processed_at'])
    except RawProduct.DoesNotExist:
        logger.warning(f"RawProduct {shopify_product_id} not found for store {store_id}")


# ── Customers ─────────────────────────────────────────────────────────────────

@shared_task
def transform_customers(store_id: int):
    """Raw customers → wh_customers."""
    store = Store.objects.get(id=store_id)
    raw_qs = RawCustomer.objects.filter(store=store, is_processed=False)
    count = 0

    for raw in raw_qs.iterator(chunk_size=200):
        try:
            _transform_one_customer(store, raw.raw_json)
            raw.is_processed = True
            raw.processed_at = timezone.now()
            raw.save(update_fields=['is_processed', 'processed_at'])
            count += 1
        except Exception as e:
            logger.warning(f"Failed to transform customer {raw.shopify_id}: {e}")

    logger.info(f"Transformed {count} customers for {store.shop_domain}")


def _transform_one_customer(store: Store, data: dict):
    addr = data.get('default_address') or {}
    Customer.objects.update_or_create(
        store=store,
        shopify_customer_id=data['id'],
        defaults={
            'email': data.get('email', ''),
            'first_name': data.get('first_name', ''),
            'last_name': data.get('last_name', ''),
            'phone': data.get('phone', ''),
            'city': addr.get('city', ''),
            'country': addr.get('country', ''),
            'orders_count': data.get('orders_count', 0),
            'total_spent': _safe_decimal(data.get('total_spent')),
            'accepts_marketing': data.get('accepts_marketing', False),
            'tags': data.get('tags', ''),
            'shopify_created_at': _parse_dt(data.get('created_at')),
        },
    )


# ── Orders ────────────────────────────────────────────────────────────────────

@shared_task
def transform_orders(store_id: int):
    """Raw orders → wh_orders + wh_order_items."""
    store = Store.objects.get(id=store_id)
    raw_qs = RawOrder.objects.filter(store=store, is_processed=False).select_related('store')
    count = 0

    for raw in raw_qs.iterator(chunk_size=100):
        try:
            _transform_one_order(store, raw.raw_json)
            raw.is_processed = True
            raw.processed_at = timezone.now()
            raw.save(update_fields=['is_processed', 'processed_at'])
            count += 1
        except Exception as e:
            logger.warning(f"Failed to transform order {raw.shopify_id}: {e}")

    logger.info(f"Transformed {count} orders for {store.shop_domain}")


def _transform_one_order(store: Store, data: dict):
    # Resolve customer
    customer = None
    cust_data = data.get('customer')
    if cust_data:
        customer = Customer.objects.filter(
            store=store,
            shopify_customer_id=cust_data['id'],
        ).first()

    order, _ = Order.objects.update_or_create(
        store=store,
        shopify_order_id=data['id'],
        defaults={
            'customer': customer,
            'order_number': data.get('order_number'),
            'email': data.get('email', ''),
            'financial_status': data.get('financial_status', ''),
            'fulfillment_status': data.get('fulfillment_status', ''),
            'subtotal_price': _safe_decimal(data.get('subtotal_price')),
            'total_discounts': _safe_decimal(data.get('total_discounts')),
            'total_tax': _safe_decimal(data.get('total_tax')),
            'total_price': _safe_decimal(data.get('total_price')),
            'currency': data.get('currency', ''),
            'processed_at': _parse_dt(data.get('processed_at')),
            'shopify_created_at': _parse_dt(data.get('created_at')),
            'cancelled_at': _parse_dt(data.get('cancelled_at')),
        },
    )

    # Update customer's last_order_date
    if customer and order.processed_at:
        if not customer.last_order_date or order.processed_at > customer.last_order_date:
            customer.last_order_date = order.processed_at
            customer.save(update_fields=['last_order_date'])

    # Transform line items
    for item_data in data.get('line_items', []):
        _transform_one_order_item(order, store, item_data)


def _transform_one_order_item(order: Order, store: Store, data: dict):
    # Resolve product and variant
    product = None
    variant = None

    if data.get('product_id'):
        product = Product.objects.filter(
            store=store,
            shopify_product_id=data['product_id'],
        ).first()

    if data.get('variant_id') and product:
        variant = ProductVariant.objects.filter(
            product=product,
            shopify_variant_id=data['variant_id'],
        ).first()

    # Calculate total discount from allocations
    total_discount = sum(
        _safe_decimal(d.get('amount', 0))
        for d in data.get('discount_allocations', [])
    )

    qty = data.get('quantity', 1)
    price = _safe_decimal(data.get('price'))

    OrderItem.objects.update_or_create(
        order=order,
        shopify_line_item_id=data['id'],
        defaults={
            'product': product,
            'variant': variant,
            'title': data.get('title', ''),
            'variant_title': data.get('variant_title', ''),
            'sku': data.get('sku', ''),
            'quantity': qty,
            'price': price,
            'total_discount': total_discount,
            'line_total': price * qty - total_discount,
        },
    )


@shared_task
def transform_single_order(store_id: int, shopify_order_id: int):
    """Transform a single order (webhook)."""
    store = Store.objects.get(id=store_id)
    try:
        raw = RawOrder.objects.get(store=store, shopify_id=shopify_order_id)
        _transform_one_order(store, raw.raw_json)
        raw.is_processed = True
        raw.processed_at = timezone.now()
        raw.save(update_fields=['is_processed', 'processed_at'])
    except RawOrder.DoesNotExist:
        logger.warning(f"RawOrder {shopify_order_id} not found")


# ── Inventory ─────────────────────────────────────────────────────────────────

@shared_task
def transform_inventory(store_id: int):
    """Raw inventory levels → wh_inventory."""
    store = Store.objects.get(id=store_id)
    raw_qs = RawInventoryLevel.objects.filter(store=store, is_processed=False)
    count = 0

    for raw in raw_qs.iterator(chunk_size=500):
        try:
            variant = ProductVariant.objects.filter(
                shopify_inventory_item_id=raw.shopify_inventory_item_id,
                product__store=store,
            ).first()

            location = Location.objects.filter(
                store=store,
                shopify_location_id=raw.shopify_location_id,
            ).first()

            if variant and location:
                Inventory.objects.update_or_create(
                    variant=variant,
                    location=location,
                    defaults={'stock_quantity': raw.available},
                )
                # Keep variant total in sync
                variant.inventory_quantity = (
                    Inventory.objects.filter(variant=variant)
                    .aggregate(total=__import__('django.db.models', fromlist=['Sum']).Sum('stock_quantity'))['total'] or 0
                )
                variant.save(update_fields=['inventory_quantity'])

            raw.is_processed = True
            raw.processed_at = timezone.now()
            raw.save(update_fields=['is_processed', 'processed_at'])
            count += 1
        except Exception as e:
            logger.warning(f"Failed to transform inventory {raw.id}: {e}")

    logger.info(f"Transformed {count} inventory records for store {store_id}")
