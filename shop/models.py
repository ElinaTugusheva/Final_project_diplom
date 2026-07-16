from django.contrib.auth import get_user_model
from django.db import models
from django.core.validators import MinValueValidator

User = get_user_model()

STATE_CHOICES = (
    ("basket", "Корзина"),
    ("new", "Новый"),
    ("confirmed", "Подтвержден"),
    ("assembled", "Собран"),
    ("sent", "Отправлен"),
    ("delivered", "Доставлен"),
    ("canceled", "Отменен"),
)


class Shop(models.Model):
    """Модель магазина/поставщика"""

    name = models.CharField(max_length=50, verbose_name="Название")
    url = models.URLField(verbose_name="Ссылка для импорта", null=True, blank=True)
    user = models.OneToOneField(User, verbose_name="Пользователь", blank=True, null=True, on_delete=models.CASCADE)
    state = models.BooleanField(verbose_name="Статус приема заказов", default=True)

    class Meta:
        verbose_name = "Магазин"
        verbose_name_plural = "Список магазинов"
        ordering = ("-name",)

    def __str__(self):
        return self.name


class Category(models.Model):
    """Модель категории товаров"""

    name = models.CharField(max_length=40, verbose_name="Название")
    shops = models.ManyToManyField(Shop, verbose_name="Магазины", related_name="categories", blank=True)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Список категорий"
        ordering = ("-name",)

    def __str__(self):
        return self.name


class Product(models.Model):
    """Модель товара"""

    name = models.CharField(max_length=80, verbose_name="Название")
    category = models.ForeignKey(
        Category, verbose_name="Категория", related_name="products", blank=True, on_delete=models.CASCADE
    )
    description = models.TextField(verbose_name="Описание", blank=True)

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Список товаров"
        ordering = ("-name",)

    def __str__(self):
        return self.name


class ProductInfo(models.Model):
    """Информация о товаре в конкретном магазине"""

    product = models.ForeignKey(Product, verbose_name="Товар", related_name="product_infos", on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, verbose_name="Магазин", related_name="product_infos", on_delete=models.CASCADE)
    external_id = models.PositiveIntegerField(verbose_name="Внешний ID")
    model = models.CharField(max_length=80, verbose_name="Модель", blank=True)
    quantity = models.PositiveIntegerField(verbose_name="Количество")
    price = models.PositiveIntegerField(verbose_name="Цена", validators=[MinValueValidator(1)])
    price_rrc = models.PositiveIntegerField(
        verbose_name="Рекомендуемая цена", default=0, validators=[MinValueValidator(0)]
    )

    class Meta:
        verbose_name = "Информация о товаре"
        verbose_name_plural = "Информация о товарах"
        constraints = [
            models.UniqueConstraint(fields=["product", "shop", "external_id"], name="unique_product_info"),
        ]

    def __str__(self):
        return f"{self.product.name} ({self.shop.name})"


class Parameter(models.Model):
    """Модель характеристики товара"""

    name = models.CharField(max_length=40, verbose_name="Название")

    class Meta:
        verbose_name = "Характеристика"
        verbose_name_plural = "Список характеристик"
        ordering = ("-name",)

    def __str__(self):
        return self.name


class ProductParameter(models.Model):
    """Значение характеристики для конкретного товара в магазине"""

    product_info = models.ForeignKey(
        ProductInfo, verbose_name="Информация о товаре", related_name="product_parameters", on_delete=models.CASCADE
    )
    parameter = models.ForeignKey(
        Parameter, verbose_name="Характеристика", related_name="product_parameters", on_delete=models.CASCADE
    )
    value = models.CharField(verbose_name="Значение", max_length=100)

    class Meta:
        verbose_name = "Значение характеристики"
        verbose_name_plural = "Значения характеристик"
        constraints = [
            models.UniqueConstraint(fields=["product_info", "parameter"], name="unique_product_parameter"),
        ]

    def __str__(self):
        return f"{self.parameter.name}: {self.value}"


class Contact(models.Model):
    """Модель контактов пользователя (адреса доставки)"""

    user = models.ForeignKey(User, verbose_name="Пользователь", related_name="contacts", on_delete=models.CASCADE)
    first_name = models.CharField(max_length=50, verbose_name="Имя")
    last_name = models.CharField(max_length=50, verbose_name="Фамилия")
    middle_name = models.CharField(max_length=50, verbose_name="Отчество", blank=True)
    email = models.EmailField(verbose_name="Email")
    phone = models.CharField(max_length=20, verbose_name="Телефон")

    # Адрес
    city = models.CharField(max_length=50, verbose_name="Город")
    street = models.CharField(max_length=100, verbose_name="Улица")
    house = models.CharField(max_length=15, verbose_name="Дом", blank=True)
    structure = models.CharField(max_length=15, verbose_name="Корпус", blank=True)
    building = models.CharField(max_length=15, verbose_name="Строение", blank=True)
    apartment = models.CharField(max_length=15, verbose_name="Квартира", blank=True)

    class Meta:
        verbose_name = "Контакт"
        verbose_name_plural = "Список контактов"
        ordering = ("-id",)

    def __str__(self):
        return f"{self.last_name} {self.first_name} - {self.city}, {self.street}"

    def get_full_address(self):
        """Возвращает полный адрес в виде строки"""
        parts = [self.city, self.street]
        if self.house:
            parts.append(f"д.{self.house}")
        if self.structure:
            parts.append(f"корп.{self.structure}")
        if self.building:
            parts.append(f"стр.{self.building}")
        if self.apartment:
            parts.append(f"кв.{self.apartment}")
        return " ".join(parts)


class Order(models.Model):
    """Модель заказа"""

    user = models.ForeignKey(User, verbose_name="Пользователь", related_name="orders", on_delete=models.CASCADE)
    dt = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    state = models.CharField(verbose_name="Статус", choices=STATE_CHOICES, max_length=15, default="basket")
    contact = models.ForeignKey(Contact, verbose_name="Контакт", blank=True, null=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Список заказов"
        ordering = ("-dt",)

    def __str__(self):
        return f"Заказ #{self.id} от {self.dt}"

    @property
    def total_price(self):
        """Вычисляет общую сумму заказа"""
        return sum(item.quantity * item.product_info.price for item in self.ordered_items.all())


class OrderItem(models.Model):
    """Позиция заказа"""

    order = models.ForeignKey(Order, verbose_name="Заказ", related_name="ordered_items", on_delete=models.CASCADE)
    product_info = models.ForeignKey(
        ProductInfo, verbose_name="Информация о товаре", related_name="ordered_items", on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(verbose_name="Количество")

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Список позиций заказа"
        constraints = [
            models.UniqueConstraint(fields=["order", "product_info"], name="unique_order_item"),
        ]

    def __str__(self):
        return f"{self.product_info.product.name} x{self.quantity}"
