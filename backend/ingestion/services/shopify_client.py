import requests
import hmac
import hashlib
import logging
from typing import Generator, Optional
from datetime import datetime, timedelta
from django.conf import settings

logger = logging.getLogger(__name__)

API_VERSION = '2024-10'


class ShopifyClient:
    """
    All Shopify API communication lives here.
    Views and tasks NEVER call Shopify directly — only through this class.
    API version hardcoded to 2024-10 for stability.
    """

    def __init__(self, store):
        self.store    = store
        self.token    = store.access_token
        # Always use hardcoded version — never rely on store.base_url
        self.base_url = f"https://{store.shop_domain}/admin/api/{API_VERSION}"
        self.session  = requests.Session()
        self.session.headers.update({
            'X-Shopify-Access-Token': self.token,
            'Content-Type': 'application/json',
        })

    # ── OAuth ─────────────────────────────────────────────────────────────────

    @staticmethod
    def build_auth_url(shop_domain: str, state: str) -> str:
        from urllib.parse import urlencode
        params = {
            'client_id':    settings.SHOPIFY_API_KEY,
            'scope':        settings.SHOPIFY_SCOPES,
            'redirect_uri': settings.SHOPIFY_REDIRECT_URI,
            'state':        state,
        }
        return f"https://{shop_domain}/admin/oauth/authorize?{urlencode(params)}"

    @staticmethod
    def exchange_token(shop_domain: str, code: str) -> str:
        resp = requests.post(
            f"https://{shop_domain}/admin/oauth/access_token",
            json={
                'client_id':     settings.SHOPIFY_API_KEY,
                'client_secret': settings.SHOPIFY_API_SECRET,
                'code':          code,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()['access_token']

    @staticmethod
    def verify_hmac(params: dict, hmac_value: str) -> bool:
        filtered = {k: v for k, v in params.items() if k != 'hmac'}
        message  = '&'.join(f"{k}={v}" for k, v in sorted(filtered.items()))
        digest   = hmac.new(
            settings.SHOPIFY_API_SECRET.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(digest, hmac_value)

    # ── Shop ──────────────────────────────────────────────────────────────────

    def get_shop(self) -> dict:
        resp = self.session.get(f"{self.base_url}/shop.json", timeout=15)
        resp.raise_for_status()
        return resp.json()['shop']

    # ── Products ──────────────────────────────────────────────────────────────

    def get_products_page(self, since_id: int = 0, limit: int = 250) -> list:
        resp = self.session.get(
            f"{self.base_url}/products.json",
            params={'limit': limit, 'since_id': since_id},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get('products', [])

    def iter_products(self) -> Generator[dict, None, None]:
        since_id = 0
        while True:
            batch = self.get_products_page(since_id=since_id)
            if not batch:
                break
            for p in batch:
                yield p
            if len(batch) < 250:
                break
            since_id = batch[-1]['id']

    # ── Orders ────────────────────────────────────────────────────────────────

    def get_orders_page(
        self,
        since_id: int = 0,
        created_at_min: Optional[str] = None,
        limit: int = 250,
    ) -> list:
        params = {'limit': limit, 'since_id': since_id, 'status': 'any'}
        if created_at_min:
            params['created_at_min'] = created_at_min
        resp = self.session.get(
            f"{self.base_url}/orders.json",
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get('orders', [])

    def iter_orders(self, days_back: int = 365) -> Generator[dict, None, None]:
        since    = (datetime.utcnow() - timedelta(days=days_back)).isoformat()
        since_id = 0
        while True:
            batch = self.get_orders_page(since_id=since_id, created_at_min=since)
            if not batch:
                break
            for o in batch:
                yield o
            if len(batch) < 250:
                break
            since_id = batch[-1]['id']

    # ── Customers ─────────────────────────────────────────────────────────────

    def get_customers_page(self, since_id: int = 0, limit: int = 250) -> list:
        resp = self.session.get(
            f"{self.base_url}/customers.json",
            params={'limit': limit, 'since_id': since_id},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get('customers', [])

    def iter_customers(self) -> Generator[dict, None, None]:
        since_id = 0
        while True:
            batch = self.get_customers_page(since_id=since_id)
            if not batch:
                break
            for c in batch:
                yield c
            if len(batch) < 250:
                break
            since_id = batch[-1]['id']

    # ── Locations ─────────────────────────────────────────────────────────────

    def get_locations(self) -> list:
        resp = self.session.get(f"{self.base_url}/locations.json", timeout=15)
        resp.raise_for_status()
        return resp.json().get('locations', [])

    # ── Inventory ─────────────────────────────────────────────────────────────

    def get_inventory_levels(self, location_id: int, limit: int = 250) -> list:
        resp = self.session.get(
            f"{self.base_url}/inventory_levels.json",
            params={'location_id': location_id, 'limit': limit},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get('inventory_levels', [])

    # ── Webhooks ──────────────────────────────────────────────────────────────

    def register_webhook(self, topic: str, address: str) -> dict:
        resp = self.session.post(
            f"{self.base_url}/webhooks.json",
            json={'webhook': {'topic': topic, 'address': address, 'format': 'json'}},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def register_all_webhooks(self, base_url: str):
        topics = [
            'orders/create', 'orders/updated',
            'products/update',
            'inventory_levels/update',
            'customers/create', 'customers/update',
        ]
        for topic in topics:
            endpoint = topic.replace('/', '_')
            try:
                self.register_webhook(topic, f"{base_url}/api/webhooks/{endpoint}/")
                logger.info(f"Webhook registered: {topic}")
            except Exception as e:
                logger.warning(f"Webhook registration failed for {topic}: {e}")
