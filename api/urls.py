from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"admin/products", views.AdminProductViewSet, basename="admin-products")
router.register(r"admin/categories", views.AdminCategoryViewSet, basename="admin-categories")

urlpatterns = [
    path("health/", views.health, name="health"),
    path("csrf/", views.csrf_token, name="csrf"),
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
    path("admin/login/", views.admin_login, name="admin-login"),
    path("admin/me/", views.admin_me, name="admin-me"),
    path("admin/logout/", views.admin_logout, name="admin-logout"),
    path("admin/dashboard/", views.admin_dashboard, name="admin-dashboard"),
    path("admin/leads/", views.admin_leads, name="admin-leads"),
    path("admin/leads/<int:pk>/", views.admin_lead_detail, name="admin-lead-detail"),
    path("admin/users/", views.admin_users, name="admin-users"),
    path("admin/tasks/", views.admin_tasks, name="admin-tasks"),
    path("admin/tasks/<int:pk>/", views.admin_task_detail, name="admin-task-detail"),
    path("admin/orders/", views.admin_orders, name="admin-orders"),
    path("admin/orders/<int:pk>/status/", views.admin_order_status, name="admin-order-status"),
    path("analytics/visit/", views.analytics_visit, name="analytics-visit"),
    path("", include(router.urls)),
]
