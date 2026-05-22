import hashlib
import hmac
import json
from urllib.parse import parse_qsl

from django.conf import settings
from django.db.models import Count, Q, Sum
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from orders.models import Order
from products.models import Category, Product, PromoBanner
from users.models import Address, TelegramUser
from .serializers import (
    AddressSerializer,
    PromoBannerSerializer,
    CategorySerializer,
    OrderCreateSerializer,
    OrderSerializer,
    ProductSerializer,
    TelegramUserSerializer,
)


def verify_telegram_init_data(init_data):
    if not settings.BOT_TOKEN:
        return None

    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        return None

    data_check_string = "\n".join(f"{key}={parsed[key]}" for key in sorted(parsed))
    secret_key = hmac.new(b"WebAppData", settings.BOT_TOKEN.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        return None

    user_raw = parsed.get("user")
    return json.loads(user_raw) if user_raw else None


def user_from_request(request):
    telegram_id = request.headers.get("X-Telegram-Id") or request.query_params.get("telegram_id")
    if not telegram_id:
        return None
    return TelegramUser.objects.filter(telegram_id=str(telegram_id)).first()


def admin_allowed(request):
    token = request.headers.get("X-Admin-Token") or request.query_params.get("admin_token")
    return bool(settings.ADMIN_API_TOKEN and token == settings.ADMIN_API_TOKEN)


def require_user(request):
    user = user_from_request(request)
    if not user:
        return None, Response({"detail": "Telegram user is not authenticated."}, status=status.HTTP_401_UNAUTHORIZED)
    return user, None


def require_admin(request):
    if not admin_allowed(request):
        return Response({"detail": "Admin token is invalid."}, status=status.HTTP_403_FORBIDDEN)
    return None


@api_view(["POST"])
def telegram_auth(request):
    init_data = request.data.get("initData") or request.data.get("init_data") or ""
    init_data_unsafe = request.data.get("initDataUnsafe") or request.data.get("init_data_unsafe") or {}

    telegram_user = verify_telegram_init_data(init_data) if init_data else None
    if settings.BOT_TOKEN and init_data and telegram_user is None:
        return Response({"detail": "Invalid Telegram initData."}, status=status.HTTP_401_UNAUTHORIZED)
    if telegram_user is None and isinstance(init_data_unsafe, dict):
        if settings.DEBUG or not settings.BOT_TOKEN:
            telegram_user = init_data_unsafe.get("user") or init_data_unsafe

    if not telegram_user and settings.BOT_TOKEN and not settings.DEBUG:
        return Response({"detail": "Telegram initData is required."}, status=status.HTTP_401_UNAUTHORIZED)

    if not telegram_user:
        telegram_user = request.data

    telegram_id = telegram_user.get("id") or telegram_user.get("telegram_id")
    if not telegram_id:
        return Response({"detail": "telegram_id is required."}, status=status.HTTP_400_BAD_REQUEST)

    user, _ = TelegramUser.objects.update_or_create(
        telegram_id=str(telegram_id),
        defaults={
            "first_name": telegram_user.get("first_name", "") or "",
            "last_name": telegram_user.get("last_name", "") or "",
            "username": telegram_user.get("username", "") or "",
            "photo_url": telegram_user.get("photo_url", "") or "",
        },
    )
    Address.objects.get_or_create(user=user)
    return Response({"user": TelegramUserSerializer(user).data})


@api_view(["GET"])
def profile(request):
    user, error = require_user(request)
    if error:
        return error
    return Response(TelegramUserSerializer(user).data)


@api_view(["PATCH"])
def profile_address(request):
    user, error = require_user(request)
    if error:
        return error
    address, _ = Address.objects.get_or_create(user=user)
    serializer = AddressSerializer(address, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    phone = request.data.get("phone")
    if phone is not None:
        user.phone = phone
        user.save(update_fields=["phone", "updated_at"])
    return Response(TelegramUserSerializer(user).data)


@api_view(["GET"])
def categories(request):
    queryset = Category.objects.filter(is_active=True).annotate(
        products_count=Count("products", filter=Q(products__is_active=True))
    )
    return Response(CategorySerializer(queryset, many=True).data)


@api_view(["GET"])
def products(request):
    queryset = Product.objects.select_related("category").filter(is_active=True, category__is_active=True)
    category = request.query_params.get("category")
    search = request.query_params.get("search")
    if category and category != "all":
        queryset = queryset.filter(Q(category__slug=category) | Q(category_id=category))
    if search:
        queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))
    return Response(ProductSerializer(queryset, many=True, context={"request": request}).data)


@api_view(["GET"])
def top_products(request):
    queryset = Product.objects.select_related("category").filter(is_active=True, category__is_active=True, is_top=True)
    return Response(ProductSerializer(queryset, many=True, context={"request": request}).data)


@api_view(["GET"])
def promo_products(request):
    queryset = Product.objects.select_related("category").filter(is_active=True, category__is_active=True, is_promo=True)
    banners = PromoBanner.objects.select_related("product", "product__category").filter(is_active=True)
    return Response(
        {
            "banners": PromoBannerSerializer(banners, many=True, context={"request": request}).data,
            "products": ProductSerializer(queryset, many=True, context={"request": request}).data,
        }
    )


@api_view(["POST"])
def create_order(request):
    user, error = require_user(request)
    if error:
        return error
    serializer = OrderCreateSerializer(data=request.data, context={"user": user})
    serializer.is_valid(raise_exception=True)
    order = serializer.save()
    return Response(OrderSerializer(order, context={"request": request}).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def my_orders(request):
    user, error = require_user(request)
    if error:
        return error
    queryset = Order.objects.filter(user=user).prefetch_related("items", "items__product").select_related("user")
    return Response(OrderSerializer(queryset, many=True, context={"request": request}).data)


@api_view(["GET"])
def order_detail(request, pk):
    user, error = require_user(request)
    if error:
        return error
    order = Order.objects.filter(pk=pk, user=user).prefetch_related("items", "items__product").first()
    if not order:
        return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
    return Response(OrderSerializer(order, context={"request": request}).data)


@api_view(["GET"])
def admin_dashboard(request):
    error = require_admin(request)
    if error:
        return error
    completed_sales = Order.objects.exclude(status=Order.Status.CANCELED).aggregate(total=Sum("total_amount"))["total"] or 0
    return Response(
        {
            "orders_total": Order.objects.count(),
            "new_orders": Order.objects.filter(status=Order.Status.NEW).count(),
            "sales_total": completed_sales,
            "products_total": Product.objects.count(),
        }
    )


@api_view(["GET"])
def admin_orders(request):
    error = require_admin(request)
    if error:
        return error
    queryset = Order.objects.select_related("user").prefetch_related("items", "items__product")
    order_status = request.query_params.get("status")
    if order_status:
        queryset = queryset.filter(status=order_status)
    return Response(OrderSerializer(queryset, many=True, context={"request": request}).data)


@api_view(["PATCH"])
def admin_order_status(request, pk):
    error = require_admin(request)
    if error:
        return error
    order = Order.objects.filter(pk=pk).first()
    if not order:
        return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
    new_status = request.data.get("status")
    if new_status not in Order.Status.values:
        return Response({"detail": "Invalid status."}, status=status.HTTP_400_BAD_REQUEST)
    order.status = new_status
    order.save(update_fields=["status", "updated_at"])
    return Response(OrderSerializer(order, context={"request": request}).data)


class AdminTokenMixin:
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not admin_allowed(request):
            self.permission_denied(request, message="Admin token is invalid.")


class AdminProductViewSet(AdminTokenMixin, viewsets.ModelViewSet):
    queryset = Product.objects.select_related("category").all()
    serializer_class = ProductSerializer


class AdminCategoryViewSet(AdminTokenMixin, viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
