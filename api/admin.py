from django.contrib import admin

from .models import Lead, SiteVisit, Task


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "service", "status", "assigned_to", "created_at")
    list_filter = ("status", "service", "created_at")
    search_fields = ("name", "phone", "service", "tariff", "message")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "priority", "assigned_to", "created_by", "due_date")
    list_filter = ("status", "priority", "due_date")
    search_fields = ("title", "description")


@admin.register(SiteVisit)
class SiteVisitAdmin(admin.ModelAdmin):
    list_display = ("page_url", "ip_address", "created_at")
    list_filter = ("created_at",)
    search_fields = ("page_url", "referrer", "user_agent", "ip_address")
