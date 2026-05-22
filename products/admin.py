from django.contrib import admin

from .models import Category, Product, PromoBanner


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "sort_order", "is_active")
    list_filter = ("is_active",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "discount_percent", "rating", "is_top", "is_promo", "is_active")
    list_filter = ("category", "is_top", "is_promo", "is_active")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(PromoBanner)
class PromoBannerAdmin(admin.ModelAdmin):
    list_display = ("title", "product", "sort_order", "is_active")
    list_filter = ("is_active",)
