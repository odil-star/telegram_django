from django.db import models

from products.models import Product
from users.models import TelegramUser


class Order(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новый"
        ACCEPTED = "accepted", "Принят"
        COOKING = "cooking", "Готовится"
        DELIVERING = "delivering", "Доставляется"
        COMPLETED = "completed", "Завершен"
        CANCELED = "canceled", "Отменен"

    class DeliveryMethod(models.TextChoices):
        DELIVERY = "delivery", "Доставка"
        PICKUP = "pickup", "Самовывоз"

    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Наличные"
        CARD_ON_DELIVERY = "card_on_delivery", "Карта при получении"
        ONLINE_LATER = "online_later", "Онлайн оплата позже"

    user = models.ForeignKey(TelegramUser, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    delivery_method = models.CharField(max_length=20, choices=DeliveryMethod.choices, default=DeliveryMethod.DELIVERY)
    payment_method = models.CharField(max_length=30, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    address = models.CharField(max_length=500, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    comment = models.TextField(blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk} - {self.user.display_name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, blank=True, null=True)
    product_name = models.CharField(max_length=160)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    total = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"
