from django.contrib import admin
from .models import Alert, Insight


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ['title', 'severity', 'category', 'store', 'is_resolved', 'created_at']
    list_filter = ['severity', 'category', 'is_resolved', 'store']
    search_fields = ['title', 'description']
    actions = ['resolve_alerts']

    def resolve_alerts(self, request, queryset):
        from django.utils import timezone
        queryset.update(is_resolved=True, resolved_at=timezone.now())
    resolve_alerts.short_description = 'Mark selected alerts as resolved'


@admin.register(Insight)
class InsightAdmin(admin.ModelAdmin):
    list_display = ['title', 'insight_type', 'severity', 'store', 'created_at']
    list_filter = ['insight_type', 'severity', 'store']
