from django.db import models


class TelegramUser(models.Model):
    telegram_id = models.CharField(max_length=64, unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    username = models.CharField(max_length=150, blank=True)
    photo_url = models.URLField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return name or self.username or f"User {self.telegram_id}"


class Address(models.Model):
    user = models.OneToOneField(TelegramUser, on_delete=models.CASCADE, related_name="address")
    full_address = models.CharField(max_length=500, blank=True)
    entrance = models.CharField(max_length=40, blank=True)
    floor = models.CharField(max_length=40, blank=True)
    apartment = models.CharField(max_length=40, blank=True)
    comment = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_address or f"Address for {self.user_id}"
