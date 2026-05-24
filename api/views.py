import hashlib
import hmac
import json
import logging
from datetime import timedelta
from functools import wraps
from urllib.parse import parse_qsl

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.models import Group
from django.db import OperationalError, ProgrammingError
from django.db.models import Count, Q
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status, viewsets
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import exception_handler

from api.models import Lead, SiteVisit, Task
from orders.models import Order
from products.models import Category, Product, PromoBanner
from users.models import Address, TelegramUser
from .serializers import (
    AddressSerializer,
    AdminUserSerializer,
    PromoBannerSerializer,
    CategorySerializer,
    LeadSerializer,
    OrderCreateSerializer,
    OrderSerializer,
    ProductSerializer,
    SiteVisitSerializer,
    TaskSerializer,
    TelegramUserSerializer,
    get_user_role,
)

User = get_user_model()
logger = logging.getLogger(__name__)
DATABASE_NOT_READY_ERRORS = (OperationalError, ProgrammingError)


def log_api_errors(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        try:
            return view_func(*args, **kwargs)
        except Exception:
            logger.exception("Unhandled API error in %s", view_func.__name__)
            raise

    return wrapped


def database_not_ready_response(exc, fallback=None, status_code=status.HTTP_503_SERVICE_UNAVAILABLE):
    logger.exception("Database is not ready or migrations are missing")
    if fallback is not None:
        return Response(fallback)
    return Response(
        {
            "detail": "Database is not ready. Set DATABASE_URL and run migrations.",
            "error": exc.__class__.__name__,
        },
        status=status_code,
    )


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response

    if isinstance(exc, NotAuthenticated):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        response.data = {"authenticated": False, "message": "Требуется вход"}
    elif isinstance(exc, PermissionDenied):
        response.status_code = status.HTTP_403_FORBIDDEN
        response.data = {"success": False, "message": str(exc.detail)}
    return response


def csrf_failure(request, reason=""):
    return JsonResponse(
        {"success": False, "message": "CSRF verification failed", "reason": reason},
        status=403,
    )


def json_not_found(request, exception=None):
    return JsonResponse({"detail": "Not found."}, status=404)


def json_server_error(request):
    return JsonResponse({"detail": "Server error."}, status=500)


def admin_user_payload(user):
    return {
        "id": user.id,
        "username": user.username,
        "role": get_user_role(user),
    }


def can_access_admin_api(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    return user.groups.filter(name__in=["admin", "manager"]).exists()


def require_admin_session(request, *, superuser=False):
    if not request.user.is_authenticated:
        return Response({"authenticated": False, "message": "Требуется вход"}, status=status.HTTP_401_UNAUTHORIZED)
    if superuser and not request.user.is_superuser:
        return Response({"success": False, "message": "Недостаточно прав"}, status=status.HTTP_403_FORBIDDEN)
    if not can_access_admin_api(request.user):
        return Response({"success": False, "message": "Недостаточно прав"}, status=status.HTTP_403_FORBIDDEN)
    return None


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


def require_user(request):
    user = user_from_request(request)
    if not user:
        return None, Response({"detail": "Telegram user is not authenticated."}, status=status.HTTP_401_UNAUTHORIZED)
    return user, None


@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})


@ensure_csrf_cookie
@api_view(["GET"])
def csrf_token(request):
    token = get_token(request)
    return Response({"success": True, "message": "CSRF cookie set", "csrfToken": token})


@api_view(["POST"])
def admin_login(request):
    username = (request.data.get("username") or "").strip()
    password = request.data.get("password") or ""
    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response(
            {"success": False, "message": "Неверный логин или пароль"},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    if not can_access_admin_api(user):
        return Response({"success": False, "message": "Недостаточно прав"}, status=status.HTTP_403_FORBIDDEN)

    login(request, user)
    return Response({"success": True, "user": admin_user_payload(user)})


@api_view(["GET"])
def admin_me(request):
    error = require_admin_session(request)
    if error:
        return error
    return Response({"authenticated": True, "user": admin_user_payload(request.user)})


@api_view(["POST"])
def admin_logout(request):
    logout(request)
    return Response({"success": True})


@api_view(["POST"])
@log_api_errors
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

    try:
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
    except DATABASE_NOT_READY_ERRORS as exc:
        return database_not_ready_response(exc)
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
@log_api_errors
def categories(request):
    try:
        queryset = Category.objects.filter(is_active=True).annotate(
            products_count=Count("products", filter=Q(products__is_active=True))
        )
        return Response(CategorySerializer(queryset, many=True).data)
    except DATABASE_NOT_READY_ERRORS as exc:
        return database_not_ready_response(exc, fallback=[])


@api_view(["GET"])
@log_api_errors
def products(request):
    try:
        queryset = Product.objects.select_related("category").filter(is_active=True, category__is_active=True)
        category = request.query_params.get("category")
        search = request.query_params.get("search")
        if category and category != "all":
            queryset = queryset.filter(Q(category__slug=category) | Q(category_id=category))
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))
        return Response(ProductSerializer(queryset, many=True, context={"request": request}).data)
    except DATABASE_NOT_READY_ERRORS as exc:
        return database_not_ready_response(exc, fallback=[])


@api_view(["GET"])
@log_api_errors
def top_products(request):
    try:
        queryset = Product.objects.select_related("category").filter(is_active=True, category__is_active=True, is_top=True)
        return Response(ProductSerializer(queryset, many=True, context={"request": request}).data)
    except DATABASE_NOT_READY_ERRORS as exc:
        return database_not_ready_response(exc, fallback=[])


@api_view(["GET"])
@log_api_errors
def promo_products(request):
    try:
        queryset = Product.objects.select_related("category").filter(is_active=True, category__is_active=True, is_promo=True)
        banners = PromoBanner.objects.select_related("product", "product__category").filter(is_active=True)
        return Response(
            {
                "banners": PromoBannerSerializer(banners, many=True, context={"request": request}).data,
                "products": ProductSerializer(queryset, many=True, context={"request": request}).data,
            }
        )
    except DATABASE_NOT_READY_ERRORS as exc:
        return database_not_ready_response(exc, fallback={"banners": [], "products": []})


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
    error = require_admin_session(request)
    if error:
        return error
    now = timezone.now()
    today = timezone.localdate(now)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)
    return Response(
        {
            "leads": {
                "total": Lead.objects.count(),
                "new": Lead.objects.filter(status=Lead.Status.NEW).count(),
                "in_work": Lead.objects.filter(status=Lead.Status.IN_WORK).count(),
                "completed": Lead.objects.filter(status=Lead.Status.COMPLETED).count(),
                "rejected": Lead.objects.filter(status=Lead.Status.REJECTED).count(),
            },
            "users": {
                "total": User.objects.count(),
                "admins": User.objects.filter(Q(is_superuser=True) | Q(is_staff=True) | Q(groups__name="admin"))
                .distinct()
                .count(),
                "managers": User.objects.filter(groups__name="manager").distinct().count(),
            },
            "tasks": {
                "total": Task.objects.count(),
                "open": Task.objects.filter(status=Task.Status.OPEN).count(),
                "done": Task.objects.filter(status=Task.Status.DONE).count(),
            },
            "visits": {
                "today": SiteVisit.objects.filter(created_at__date=today).count(),
                "week": SiteVisit.objects.filter(created_at__gte=week_start).count(),
                "month": SiteVisit.objects.filter(created_at__gte=month_start).count(),
            },
        }
    )


@api_view(["GET"])
def admin_leads(request):
    error = require_admin_session(request)
    if error:
        return error
    queryset = Lead.objects.select_related("assigned_to")
    return Response(LeadSerializer(queryset, many=True).data)


@api_view(["PATCH"])
def admin_lead_detail(request, pk):
    error = require_admin_session(request)
    if error:
        return error
    lead = Lead.objects.filter(pk=pk).first()
    if not lead:
        return Response({"detail": "Lead not found."}, status=status.HTTP_404_NOT_FOUND)
    serializer = LeadSerializer(lead, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["GET", "POST"])
def admin_users(request):
    error = require_admin_session(request, superuser=True)
    if error:
        return error
    if request.method == "GET":
        queryset = User.objects.prefetch_related("groups").order_by("username")
        return Response(AdminUserSerializer(queryset, many=True).data)

    username = (request.data.get("username") or "").strip()
    password = request.data.get("password") or ""
    role = request.data.get("role") or "manager"
    if role not in {"admin", "manager"}:
        return Response({"message": "Invalid role."}, status=status.HTTP_400_BAD_REQUEST)
    if not username or not password:
        return Response({"message": "Username and password are required."}, status=status.HTTP_400_BAD_REQUEST)
    if User.objects.filter(username=username).exists():
        return Response({"message": "User already exists."}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(username=username, password=password)
    user.is_staff = role == "admin"
    user.save(update_fields=["is_staff"])
    group, _ = Group.objects.get_or_create(name=role)
    user.groups.add(group)
    return Response(AdminUserSerializer(user).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "POST"])
def admin_tasks(request):
    error = require_admin_session(request)
    if error:
        return error
    if request.method == "GET":
        queryset = Task.objects.select_related("assigned_to", "created_by")
        return Response(TaskSerializer(queryset, many=True).data)

    serializer = TaskSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    task = serializer.save(created_by=request.user)
    return Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)


@api_view(["PATCH"])
def admin_task_detail(request, pk):
    error = require_admin_session(request)
    if error:
        return error
    task = Task.objects.filter(pk=pk).first()
    if not task:
        return Response({"detail": "Task not found."}, status=status.HTTP_404_NOT_FOUND)
    serializer = TaskSerializer(task, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["POST"])
@log_api_errors
def analytics_visit(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip_address = forwarded_for.split(",")[0].strip() or request.META.get("REMOTE_ADDR")
    data = {
        "page_url": request.data.get("page_url") or request.META.get("HTTP_REFERER") or "https://odil-star.github.io/",
        "referrer": request.data.get("referrer") or "",
        "user_agent": request.data.get("user_agent") or request.META.get("HTTP_USER_AGENT") or "",
    }
    serializer = SiteVisitSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    try:
        visit = serializer.save(ip_address=ip_address)
    except DATABASE_NOT_READY_ERRORS as exc:
        return database_not_ready_response(exc)
    return Response(SiteVisitSerializer(visit).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def admin_orders(request):
    error = require_admin_session(request)
    if error:
        return error
    queryset = Order.objects.select_related("user").prefetch_related("items", "items__product")
    order_status = request.query_params.get("status")
    if order_status:
        queryset = queryset.filter(status=order_status)
    return Response(OrderSerializer(queryset, many=True, context={"request": request}).data)


@api_view(["PATCH"])
def admin_order_status(request, pk):
    error = require_admin_session(request)
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


class AdminSessionMixin:
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not request.user.is_authenticated:
            raise NotAuthenticated("Требуется вход")
        if not can_access_admin_api(request.user):
            raise PermissionDenied("Недостаточно прав")


class AdminProductViewSet(AdminSessionMixin, viewsets.ModelViewSet):
    queryset = Product.objects.select_related("category").all()
    serializer_class = ProductSerializer


class AdminCategoryViewSet(AdminSessionMixin, viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
