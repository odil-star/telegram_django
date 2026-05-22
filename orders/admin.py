from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "price", "quantity", "total")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "delivery_method", "payment_method", "total_amount", "created_at")
    list_filter = ("status", "delivery_method", "payment_method")
    search_fields = ("id", "user__telegram_id", "user__username", "phone", "address")
    inlines = [OrderItemInline]
