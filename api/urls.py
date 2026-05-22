from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"admin/products", views.AdminProductViewSet, basename="admin-products")
router.register(r"admin/categories", views.AdminCategoryViewSet, basename="admin-categories")

urlpatterns = [
    path("telegram/auth/", views.telegram_auth, name="telegram-auth"),
    path("profile/", views.profile, name="profile"),
    path("profile/address/", views.profile_address, name="profile-address"),
    path("categories/", views.categories, name="categories"),
    path("products/", views.products, name="products"),
    path("products/top/", views.top_products, name="top-products"),
    path("products/promos/", views.promo_products, name="promo-products"),
    path("promos/", views.promo_products, name="promos"),
    path("orders/", views.create_order, name="create-order"),
    path("orders/my/", views.my_orders, name="my-orders"),
    path("orders/<int:pk>/", views.order_detail, name="order-detail"),
    path("admin/dashboard/", views.admin_dashboard, name="admin-dashboard"),
    path("admin/orders/", views.admin_orders, name="admin-orders"),
    path("admin/orders/<int:pk>/status/", views.admin_order_status, name="admin-order-status"),
    path("", include(router.urls)),
]
