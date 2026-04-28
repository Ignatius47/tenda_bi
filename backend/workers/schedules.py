"""
Celery Beat periodic task schedule.
All scheduled tasks are defined here — not scattered across apps.

Schedule summary:
  Every 15 min  → incremental Shopify sync (all stores)
  Every hour    → analytics calculations + insight generation
  Daily 02:00   → full RFM recomputation
  Daily 03:00   → cleanup old resolved alerts (30d+)
"""
from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    # ── Data ingestion ────────────────────────────────────────────────────
    'sync-all-stores-every-15-minutes': {
        'task': 'ingestion.tasks.sync_all_active_stores',
        'schedule': crontab(minute='*/15'),
    },

    # ── Analytics ─────────────────────────────────────────────────────────
    'run-analytics-every-hour': {
        'task': 'analytics.tasks.run_analytics_for_all_stores',
        'schedule': crontab(minute=5),  # 5 min past every hour
    },

    # ── Insights ──────────────────────────────────────────────────────────
    'generate-insights-every-hour': {
        'task': 'insights.tasks.generate_insights_for_all_stores',
        'schedule': crontab(minute=20),  # 20 min past every hour
    },

    # ── RFM (daily, after midnight) ────────────────────────────────────────
    'calculate-rfm-daily': {
        'task': 'analytics.tasks.run_analytics_for_all_stores',
        'schedule': crontab(hour=2, minute=0),
    },

    # ── Cleanup ───────────────────────────────────────────────────────────
    'cleanup-old-alerts-daily': {
        'task': 'workers.tasks.cleanup_old_alerts',
        'schedule': crontab(hour=3, minute=0),
    },
}
