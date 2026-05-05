from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from api.views.auth_views import (
    RegisterView, LoginView, MeView,
    ShopifyAuthStartView, ShopifyAuthCallbackView, ShopifyConnectView,
)
from api.views.shopify_views import (
    StoreListView, StoreSyncView, StoreSyncLogsView, WebhookView,
)
from api.views.dashboard_views import (
    DashboardSummaryView, DashboardKPIView, RevenueTrendView,
    TopProductsView, CategoryRevenueView, LocationRevenueView, InsightsView,
)
from api.views.other_views import (
    InventoryOverviewView,
    CustomerAnalyticsView, CustomerListView,
    AlertListView, AlertResolveView,
)

urlpatterns = [

    # ── Auth (manual) ──────────────────────────────────────────────────────────
    path('auth/register/',         RegisterView.as_view()),
    path('auth/login/',            LoginView.as_view()),
    path('auth/token/refresh/',    TokenRefreshView.as_view()),
    path('auth/me/',               MeView.as_view()),

    # ── Shopify-first OAuth ────────────────────────────────────────────────────
    # Step 1: redirect to Shopify (no login required)
    path('auth/shopify/start/',    ShopifyAuthStartView.as_view()),
    # Step 2: callback from Shopify — auto-creates user, returns JWT
    path('auth/shopify/callback/', ShopifyAuthCallbackView.as_view()),

    # ── Store management ───────────────────────────────────────────────────────
    path('shopify/connect/',                              ShopifyConnectView.as_view()),
    path('shopify/stores/',                               StoreListView.as_view()),
    path('shopify/stores/<int:store_id>/sync/',           StoreSyncView.as_view()),
    path('shopify/stores/<int:store_id>/sync-logs/',      StoreSyncLogsView.as_view()),

    # ── Webhooks ───────────────────────────────────────────────────────────────
    path('webhooks/<str:event>/',                         WebhookView.as_view()),

    # ── Dashboard ─────────────────────────────────────────────────────────────
    # Single-call summary endpoint (mobile-optimised)
    path('dashboard/<int:store_id>/summary/',             DashboardSummaryView.as_view()),
    # Individual endpoints for desktop
    path('dashboard/<int:store_id>/kpis/',                DashboardKPIView.as_view()),
    path('dashboard/<int:store_id>/revenue-trend/',       RevenueTrendView.as_view()),
    path('dashboard/<int:store_id>/top-products/',        TopProductsView.as_view()),
    path('dashboard/<int:store_id>/category-revenue/',    CategoryRevenueView.as_view()),
    path('dashboard/<int:store_id>/location-revenue/',    LocationRevenueView.as_view()),
    path('dashboard/<int:store_id>/insights/',            InsightsView.as_view()),

    # ── Inventory ──────────────────────────────────────────────────────────────
    path('inventory/<int:store_id>/',                     InventoryOverviewView.as_view()),

    # ── Customers ─────────────────────────────────────────────────────────────
    path('customers/<int:store_id>/analytics/',           CustomerAnalyticsView.as_view()),
    path('customers/<int:store_id>/list/',                CustomerListView.as_view()),

    # ── Alerts ────────────────────────────────────────────────────────────────
    path('alerts/<int:store_id>/',                        AlertListView.as_view()),
    path('alerts/<int:store_id>/<int:alert_id>/resolve/', AlertResolveView.as_view()),
]
