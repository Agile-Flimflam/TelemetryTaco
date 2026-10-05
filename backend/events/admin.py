from django.contrib import admin

from events.models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("id", "event_name", "distinct_id", "timestamp", "uuid")
    list_filter = ("event_name", "timestamp")
    search_fields = ("distinct_id", "event_name", "uuid")
    ordering = ("-timestamp", "-id")
