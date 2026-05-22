from decimal import Decimal

from django.core.management.base import BaseCommand

from products.models import Category, Product, PromoBanner


DEMO_CATEGORIES = [
    ("Бургеры", "burgers"),
    ("Пицца", "pizza"),
    ("Лаваш", "lavash"),
    ("Напитки", "drinks"),
    ("Комбо", "combo"),
    ("Сеты", "sets"),
    ("Десерты", "desserts"),
    ("Соусы", "sauces"),
]

DEMO_PRODUCTS = [
    {
        "category": "burgers",
        "name": "Smash Burger",
        "description": "Две котлеты, cheddar, маринованный лук и фирменный соус.",
        "price": "42000",
        "image_url": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=900&q=80",
        "is_top": True,
    },
    {
        "category": "burgers",
        "name": "Chicken Crispy",
        "description": "Хрустящая курица, салат айсберг, томаты и чесночный соус.",
        "price": "36000",
        "image_url": "https://images.unsplash.com/photo-1615297928064-24977384d0da?auto=format&fit=crop&w=900&q=80",
        "is_promo": True,
        "discount_percent": 10,
    },
    {
        "category": "pizza",
        "name": "Пепперони",
        "description": "Моцарелла, томатный соус и пряная пепперони.",
        "price": "69000",
        "image_url": "https://images.unsplash.com/photo-1628840042765-356cda07504e?auto=format&fit=crop&w=900&q=80",
        "is_top": True,
    },
    {
        "category": "pizza",
        "name": "Маргарита",
        "description": "Классика с томатами, моцареллой и базиликом.",
        "price": "59000",
        "image_url": "https://images.unsplash.com/photo-1595854341625-f33ee10dbf94?auto=format&fit=crop&w=900&q=80",
    },
    {
        "category": "lavash",
        "name": "Лаваш Big Beef",
        "description": "Говядина, картофель фри, свежие овощи и сливочный соус.",
        "price": "38000",
        "image_url": "https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?auto=format&fit=crop&w=900&q=80",
        "is_top": True,
    },
    {
        "category": "drinks",
        "name": "Лимонад Манго",
        "description": "Холодный лимонад с манго и лаймом.",
        "price": "18000",
        "image_url": "https://images.unsplash.com/photo-1621263764928-df1444c5e859?auto=format&fit=crop&w=900&q=80",
        "is_promo": True,
    },
    {
        "category": "combo",
        "name": "Комбо №1",
        "description": "Smash Burger, картофель фри и напиток.",
        "price": "69000",
        "image_url": "https://images.unsplash.com/photo-1594212699903-ec8a3eca50f5?auto=format&fit=crop&w=900&q=80",
        "is_top": True,
        "is_promo": True,
        "discount_percent": 12,
    },
    {
        "category": "sets",
        "name": "Party Set",
        "description": "2 пиццы, 4 напитка, картофель и набор соусов.",
        "price": "189000",
        "image_url": "https://images.unsplash.com/photo-1548365328-9f547fb09530?auto=format&fit=crop&w=900&q=80",
        "is_promo": True,
        "discount_percent": 15,
    },
    {
        "category": "desserts",
        "name": "Чизкейк",
        "description": "Нежный чизкейк с ягодным топпингом.",
        "price": "25000",
        "image_url": "https://images.unsplash.com/photo-1533134242443-d4fd215305ad?auto=format&fit=crop&w=900&q=80",
    },
    {
        "category": "sauces",
        "name": "Сырный соус",
        "description": "Густой соус cheddar для картофеля и бургеров.",
        "price": "6000",
        "image_url": "https://images.unsplash.com/photo-1472476443507-c7a5948772fc?auto=format&fit=crop&w=900&q=80",
    },
]


class Command(BaseCommand):
    help = "Seed demo fast-food categories, products and promos."

    def handle(self, *args, **options):
        categories = {}
        for index, (name, slug) in enumerate(DEMO_CATEGORIES):
            category, _ = Category.objects.update_or_create(
                slug=slug,
                defaults={"name": name, "sort_order": index, "is_active": True},
            )
            categories[slug] = category

        for demo_product in DEMO_PRODUCTS:
            product_data = demo_product.copy()
            category_slug = product_data.pop("category")
            Product.objects.update_or_create(
                name=product_data["name"],
                defaults={
                    **product_data,
                    "category": categories[category_slug],
                    "price": Decimal(product_data["price"]),
                    "is_active": True,
                },
            )

        combo = Product.objects.filter(name="Комбо №1").first()
        PromoBanner.objects.update_or_create(
            title="Комбо недели",
            defaults={
                "subtitle": "Бургер, фри и напиток со скидкой 12%",
                "image_url": "https://images.unsplash.com/photo-1610614819513-58e34989848b?auto=format&fit=crop&w=1200&q=80",
                "product": combo,
                "is_active": True,
                "sort_order": 1,
            },
        )
        PromoBanner.objects.update_or_create(
            title="Большая пицца для друзей",
            defaults={
                "subtitle": "Заказывайте сеты для компании и экономьте до 15%",
                "image_url": "https://images.unsplash.com/photo-1513104890138-7c749659a591?auto=format&fit=crop&w=1200&q=80",
                "is_active": True,
                "sort_order": 2,
            },
        )

        self.stdout.write(self.style.SUCCESS("Demo data seeded."))
