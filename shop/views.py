import requests
import yaml
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import URLValidator
from django.db import transaction
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import filters, generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Category, Contact, Order, OrderItem, Parameter, Product, ProductInfo, ProductParameter, Shop
from .serializers import (
    CartAddSerializer,
    CartRemoveSerializer,
    CategorySerializer,
    ContactSerializer,
    OrderSerializer,
    ProductInfoSerializer,
    ShopSerializer,
)


class ProductListView(generics.ListAPIView):
    """Список товаров с фильтрацией и поиском"""

    permission_classes = [AllowAny]
    serializer_class = ProductInfoSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["shop__id", "product__category__id", "shop__state"]
    search_fields = ["product__name", "model", "product__description"]
    ordering_fields = ["price", "product__name", "quantity"]
    ordering = ["product__name"]

    def get_queryset(self):
        return ProductInfo.objects.select_related("product", "shop").filter(shop__state=True, quantity__gt=0).distinct()


class ProductDetailView(generics.RetrieveAPIView):
    """Детальная информация о товаре"""

    permission_classes = [AllowAny]
    serializer_class = ProductInfoSerializer
    queryset = ProductInfo.objects.select_related("product", "shop").all()


class CategoryListView(generics.ListAPIView):
    """Список категорий"""

    permission_classes = [AllowAny]
    serializer_class = CategorySerializer
    queryset = Category.objects.all().distinct()


class ShopListView(generics.ListAPIView):
    """Список магазинов"""

    permission_classes = [AllowAny]
    serializer_class = ShopSerializer
    queryset = Shop.objects.filter(state=True)


class ShopToggleView(APIView):
    """Включение/отключение приема заказов магазином"""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        shop = get_object_or_404(Shop, pk=pk)

        # Проверяем, что пользователь владелец магазина
        if shop.user != request.user:
            return Response(
                {"status": "error", "message": "You do not have permission to manage this shop"},
                status=status.HTTP_403_FORBIDDEN,
            )

        shop.state = not shop.state
        shop.save()

        return Response(
            {"status": "success", "message": f'Shop state changed to {"active" if shop.state else "inactive"}'}
        )


class ContactListView(generics.ListCreateAPIView):
    """Просмотр и создание контактов"""

    permission_classes = [IsAuthenticated]
    serializer_class = ContactSerializer

    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ContactDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Просмотр, обновление и удаление контакта"""

    permission_classes = [IsAuthenticated]
    serializer_class = ContactSerializer

    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user)


class CartView(APIView):
    """Просмотр корзины"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        order, _ = Order.objects.get_or_create(user=request.user, state="basket")
        serializer = OrderSerializer(order)
        return Response(serializer.data)


class CartAddView(APIView):
    """Добавление товара в корзину"""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "product_info_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="ID товара (ProductInfo)", example=1
                ),
                "quantity": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="Количество товара", example=2, default=1
                ),
            },
            required=["product_info_id"],
        ),
        responses={200: "Товар добавлен в корзину", 400: "Ошибка валидации", 404: "Товар не найден"},
    )
    def post(self, request):
        serializer = CartAddSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"status": "error", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        product_info_id = serializer.validated_data["product_info_id"]
        quantity = serializer.validated_data["quantity"]

        try:
            product_info = ProductInfo.objects.get(id=product_info_id)
        except ProductInfo.DoesNotExist:
            return Response({"status": "error", "message": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

        # Проверяем количество
        if product_info.quantity < quantity:
            return Response(
                {"status": "error", "message": f"Not enough quantity. Available: {product_info.quantity}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Получаем или создаем корзину
        order, _ = Order.objects.get_or_create(user=request.user, state="basket")

        # Добавляем товар в корзину
        order_item, created = OrderItem.objects.get_or_create(
            order=order, product_info=product_info, defaults={"quantity": quantity}
        )

        if not created:
            # Проверяем, что общее количество не превышает доступное
            if order_item.quantity + quantity > product_info.quantity:
                return Response(
                    {
                        "status": "error",
                        "message": f"Cannot add more. Available: {product_info.quantity}, "
                        f"Already in cart: {order_item.quantity}",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            order_item.quantity += quantity
            order_item.save()

        return Response({"status": "success", "message": "Product added to cart"})


class CartRemoveView(APIView):
    """Удаление товара из корзины"""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "product_info_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="ID товара (ProductInfo)", example=1
                ),
                "quantity": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="Количество для удаления (если не указано - удалить все)",
                    example=1,
                    default=None,
                ),
            },
            required=["product_info_id"],
        ),
        responses={200: "Товар удален из корзины", 400: "Ошибка валидации", 404: "Товар не найден в корзине"},
    )
    def post(self, request):
        serializer = CartRemoveSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"status": "error", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        product_info_id = serializer.validated_data["product_info_id"]
        quantity = serializer.validated_data.get("quantity")

        try:
            order = Order.objects.get(user=request.user, state="basket")
            order_item = OrderItem.objects.get(order=order, product_info_id=product_info_id)
        except Order.DoesNotExist:
            return Response({"status": "error", "message": "Cart is empty"}, status=status.HTTP_404_NOT_FOUND)
        except OrderItem.DoesNotExist:
            return Response({"status": "error", "message": "Item not found in cart"}, status=status.HTTP_404_NOT_FOUND)

        if quantity is None or quantity >= order_item.quantity:
            order_item.delete()
        else:
            order_item.quantity -= quantity
            order_item.save()

        return Response({"status": "success", "message": "Product removed from cart"})


class OrderListView(generics.ListAPIView):
    """Список заказов пользователя"""

    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).exclude(state="basket").order_by("-dt")


class OrderDetailView(generics.RetrieveAPIView):
    """Детальная информация о заказе"""

    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).exclude(state="basket")


class OrderCreateView(APIView):
    """Создание заказа из корзины"""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "contact_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="ID контакта (адреса доставки)", example=1
                ),
            },
            required=["contact_id"],
        ),
        responses={201: "Заказ создан", 400: "Ошибка валидации", 404: "Контакт не найден"},
    )
    @transaction.atomic
    def post(self, request):
        contact_id = request.data.get("contact_id")

        if not contact_id:
            return Response(
                {"status": "error", "message": "contact_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            contact = Contact.objects.get(id=contact_id, user=request.user)
        except Contact.DoesNotExist:
            return Response({"status": "error", "message": "Contact not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            order = Order.objects.get(user=request.user, state="basket")
        except Order.DoesNotExist:
            return Response({"status": "error", "message": "Cart is empty"}, status=status.HTTP_400_BAD_REQUEST)

        if order.ordered_items.count() == 0:
            return Response({"status": "error", "message": "Cart is empty"}, status=status.HTTP_400_BAD_REQUEST)

        # Проверяем наличие товаров
        for item in order.ordered_items.all():
            if item.quantity > item.product_info.quantity:
                return Response(
                    {
                        "status": "error",
                        "message": f"Not enough quantity for {item.product_info.product.name}. "
                        f"Available: {item.product_info.quantity}",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Обновляем заказ
        order.state = "new"
        order.contact = contact
        order.save()

        # Уменьшаем количество товаров
        for item in order.ordered_items.all():
            product_info = item.product_info
            product_info.quantity -= item.quantity
            product_info.save()

        try:
            self._send_order_emails(order, request.user, contact)
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send order emails for order #{order.id}: {e}")

        return Response(
            {"status": "success", "message": "Order created successfully", "order": OrderSerializer(order).data},
            status=status.HTTP_201_CREATED,
        )

    def _send_order_emails(self, order, user, contact):
        """отправка писем вынесена из транзакции"""
        order_items = order.ordered_items.all()
        items_text = "\n".join(
            [
                f"- {item.product_info.product.name} x{item.quantity} = "
                f"{item.quantity * item.product_info.price} руб."
                for item in order_items
            ]
        )

        # Отправляем письмо пользователю
        send_mail(
            subject=f"Подтверждение заказа #{order.id}",
            message=f"Ваш заказ #{order.id} подтвержден.\n\n"
            f"Детали заказа:\n{items_text}\n\n"
            f"Сумма: {order.total_price} руб.\n"
            f"Адрес доставки: {contact.get_full_address()}\n\n"
            f"Спасибо за заказ!",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        # Отправляем письмо администратору
        send_mail(
            subject=f"Новый заказ #{order.id}",
            message=f"Поступил новый заказ #{order.id}\n\n"
            f"Пользователь: {user.email}\n"
            f"Сумма: {order.total_price} руб.\n"
            f"Адрес доставки: {contact.get_full_address()}\n\n"
            f"Детали заказа:\n{items_text}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.EMAIL_HOST_USER],
            fail_silently=False,
        )


class PartnerImportView(APIView):
    """Импорт товаров от поставщика"""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "url": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="URL YAML файла с товарами",
                    example="http://localhost:8001/price_svyaznoy.yaml",
                ),
            },
            required=["url"],
        ),
        responses={
            200: openapi.Response(
                description="Успешный импорт",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "status": openapi.Schema(type=openapi.TYPE_STRING),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "products_imported": openapi.Schema(type=openapi.TYPE_INTEGER),
                    },
                ),
            ),
            400: "Ошибка валидации",
            403: "Доступ запрещен",
            500: "Внутренняя ошибка сервера",
        },
    )
    def post(self, request):
        # Проверяем, что пользователь - магазин
        if request.user.type != "shop":
            return Response(
                {"status": "error", "message": "Only shops can import products"}, status=status.HTTP_403_FORBIDDEN
            )

        url = request.data.get("url")
        if not url:
            return Response({"status": "error", "message": "URL is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Проверяем URL
        validate_url = URLValidator()
        try:
            validate_url(url)
        except ValidationError as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Загружаем данные
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = yaml.safe_load(response.content)
        except Exception as e:
            return Response(
                {"status": "error", "message": f"Failed to load data: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Проверяем структуру данных
        if "shop" not in data or "categories" not in data or "goods" not in data:
            return Response(
                {"status": "error", "message": "Invalid data format. Required fields: shop, categories, goods"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                # Создаем или обновляем магазин
                shop, _ = Shop.objects.get_or_create(name=data["shop"], user=request.user)

                # Создаем категории
                for category_data in data["categories"]:
                    category, _ = Category.objects.get_or_create(
                        id=category_data["id"], defaults={"name": category_data["name"]}
                    )
                    if not category.name:
                        category.name = category_data["name"]
                        category.save()
                    category.shops.add(shop)

                # Удаляем старые товары магазина
                ProductInfo.objects.filter(shop=shop).delete()

                # Создаем товары
                for item in data["goods"]:
                    product, _ = Product.objects.get_or_create(name=item["name"], category_id=item["category"])

                    product_info = ProductInfo.objects.create(
                        product=product,
                        shop=shop,
                        external_id=item["id"],
                        model=item.get("model", ""),
                        price=item["price"],
                        price_rrc=item.get("price_rrc", 0),
                        quantity=item["quantity"],
                    )

                    # Добавляем параметры
                    for param_name, param_value in item.get("parameters", {}).items():
                        parameter, _ = Parameter.objects.get_or_create(name=param_name)
                        ProductParameter.objects.create(
                            product_info=product_info, parameter=parameter, value=str(param_value)
                        )

                return Response(
                    {
                        "status": "success",
                        "message": "Products imported successfully",
                        "products_imported": len(data["goods"]),
                    }
                )

        except Exception as e:
            return Response(
                {"status": "error", "message": f"Import failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PartnerExportView(APIView):
    """Экспорт товаров для поставщика"""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(responses={200: "YAML файл с товарами", 403: "Доступ запрещен", 404: "Магазин не найден"})
    def get(self, request):
        # Проверяем, что пользователь - магазин
        if request.user.type != "shop":
            return Response(
                {"status": "error", "message": "Only shops can export products"}, status=status.HTTP_403_FORBIDDEN
            )

        try:
            shop = Shop.objects.get(user=request.user)
        except Shop.DoesNotExist:
            return Response({"status": "error", "message": "Shop not found"}, status=status.HTTP_404_NOT_FOUND)

        # Собираем данные
        data = {"shop": shop.name, "categories": [], "goods": []}

        # Категории
        categories = shop.categories.all()
        for category in categories:
            data["categories"].append({"id": category.id, "name": category.name})

        # Товары
        product_infos = ProductInfo.objects.filter(shop=shop).select_related("product", "product__category")
        for pi in product_infos:
            item = {
                "id": pi.external_id,
                "category": pi.product.category_id,
                "model": pi.model,
                "name": pi.product.name,
                "price": pi.price,
                "price_rrc": pi.price_rrc,
                "quantity": pi.quantity,
                "parameters": {},
            }

            # Параметры
            for param in pi.product_parameters.all():
                item["parameters"][param.parameter.name] = param.value

            data["goods"].append(item)

        # Возвращаем YAML
        yaml_data = yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)

        return Response(yaml_data, content_type="application/x-yaml")
