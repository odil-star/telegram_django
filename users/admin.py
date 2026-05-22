from django.contrib import admin

from .models import Address, TelegramUser


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ("telegram_id", "display_name", "username", "phone", "created_at")
    search_fields = ("telegram_id", "first_name", "last_name", "username", "phone")


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("user", "full_address", "updated_at")
    search_fields = ("full_address", "user__telegram_id", "user__username")
