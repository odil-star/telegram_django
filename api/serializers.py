from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import serializers

from api.models import Lead, SiteVisit, Task
from orders.models import Order, OrderItem
from products.models import Category, Product, PromoBanner
from users.models import Address, TelegramUser

User = get_user_model()


def get_user_role(user):
    if user.is_superuser:
        return "superuser"
    if user.groups.filter(name="admin").exists() or user.is_staff:
        return "admin"
    if user.groups.filter(name="manager").exists():
        return "manager"
    return "manager"


class AdminUserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "username", "role", "is_active", "is_staff", "is_superuser", "date_joined")
        read_only_fields = fields

    def get_role(self, obj):
        return get_user_role(obj)


class LeadSerializer(serializers.ModelSerializer):
    assigned_to = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False, allow_null=True)
    assigned_to_user = AdminUserSerializer(source="assigned_to", read_only=True)

    class Meta:
        model = Lead
        fields = (
            "id",
            "name",
            "phone",
            "service",
            "tariff",
            "message",
            "status",
            "assigned_to",
            "assigned_to_user",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "assigned_to_user")


class TaskSerializer(serializers.ModelSerializer):
    assigned_to = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False, allow_null=True)
    assigned_to_user = AdminUserSerializer(source="assigned_to", read_only=True)
    created_by_user = AdminUserSerializer(source="created_by", read_only=True)

    class Meta:
        model = Task
        fields = (
            "id",
            "title",
            "description",
            "assigned_to",
            "assigned_to_user",
            "created_by",
            "created_by_user",
            "status",
            "priority",
            "due_date",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_by", "created_by_user", "created_at", "updated_at")


class SiteVisitSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteVisit
        fields = ("id", "page_url", "referrer", "user_agent", "ip_address", "created_at")
        read_only_fields = ("id", "ip_address", "created_at")


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ("full_address", "entrance", "floor", "apartment", "comment", "updated_at")
        read_only_fields = ("updated_at",)


class TelegramUserSerializer(serializers.ModelSerializer):
    address = AddressSerializer(read_only=True)
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = TelegramUser
        fields = (
            "id",
            "telegram_id",
            "first_name",
            "last_name",
            "username",
            "photo_url",
            "phone",
            "display_name",
            "address",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "telegram_id", "created_at", "updated_at")


class CategorySerializer(serializers.ModelSerializer):
    products_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "image_url", "sort_order", "is_active", "products_count")


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source="category", write_only=True
    )
    final_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    image_src = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "category",
            "category_id",
            "name",
            "slug",
            "description",
            "price",
            "final_price",
            "image",
            "image_url",
            "image_src",
            "is_top",
            "is_promo",
            "discount_percent",
            "rating",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("slug", "created_at", "updated_at")

    def get_image_src(self, obj):
        request = self.context.get("request")
        if obj.image:
            url = obj.image.url
            return request.build_absolute_uri(url) if request else url
        return obj.image_url


class PromoBannerSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source="product", write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = PromoBanner
        fields = ("id", "title", "subtitle", "image_url", "product", "product_id", "is_active", "sort_order")


class OrderItemSerializer(serializers.ModelSerializer):
    product_image = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ("id", "product", "product_name", "product_image", "price", "quantity", "total")

    def get_product_image(self, obj):
        if not obj.product:
            return ""
        return ProductSerializer(obj.product, context=self.context).data.get("image_src", "")


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user = TelegramUserSerializer(read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    delivery_method_label = serializers.CharField(source="get_delivery_method_display", read_only=True)
    payment_method_label = serializers.CharField(source="get_payment_method_display", read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "user",
            "status",
            "status_label",
            "delivery_method",
            "delivery_method_label",
            "payment_method",
            "payment_method_label",
            "address",
            "phone",
            "comment",
            "total_amount",
            "items",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "user", "status", "total_amount", "items", "created_at", "updated_at")


class OrderCreateItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, max_value=99)


class OrderCreateSerializer(serializers.Serializer):
    delivery_method = serializers.ChoiceField(choices=Order.DeliveryMethod.choices)
    payment_method = serializers.ChoiceField(choices=Order.PaymentMethod.choices)
    address = serializers.CharField(max_length=500, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    comment = serializers.CharField(required=False, allow_blank=True)
    items = OrderCreateItemSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Корзина пуста.")
        product_ids = [item["product_id"] for item in value]
        products = Product.objects.filter(id__in=product_ids, is_active=True)
        found_ids = set(products.values_list("id", flat=True))
        missing = set(product_ids) - found_ids
        if missing:
            raise serializers.ValidationError(f"Товары недоступны: {', '.join(map(str, missing))}.")
        return value

    def create(self, validated_data):
        user = self.context["user"]
        items_data = validated_data.pop("items")
        if not validated_data.get("address") and hasattr(user, "address"):
            validated_data["address"] = user.address.full_address
        if not validated_data.get("phone"):
            validated_data["phone"] = user.phone

        product_map = Product.objects.in_bulk([item["product_id"] for item in items_data])
        total_amount = Decimal("0.00")
        order_items = []

        for item in items_data:
            product = product_map[item["product_id"]]
            quantity = item["quantity"]
            price = product.final_price
            item_total = price * quantity
            total_amount += item_total
            order_items.append(
                OrderItem(
                    product=product,
                    product_name=product.name,
                    price=price,
                    quantity=quantity,
                    total=item_total,
                )
            )

        order = Order.objects.create(user=user, total_amount=total_amount, **validated_data)
        for order_item in order_items:
            order_item.order = order
        OrderItem.objects.bulk_create(order_items)
        return order


class DashboardSerializer(serializers.Serializer):
    orders_total = serializers.IntegerField()
    new_orders = serializers.IntegerField()
    sales_total = serializers.DecimalField(max_digits=12, decimal_places=2)
    products_total = serializers.IntegerField()
