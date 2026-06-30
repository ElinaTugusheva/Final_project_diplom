from rest_framework import serializers
from django.db import transaction
from .models import (
    Shop, Category, Product, ProductInfo,
    Parameter, ProductParameter, Order, OrderItem, Contact
)


class ShopSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Shop"""

    class Meta:
        model = Shop
        fields = ('id', 'name', 'url', 'state')
        read_only_fields = ('id',)


class CategorySerializer(serializers.ModelSerializer):
    """Сериализатор для модели Category"""

    class Meta:
        model = Category
        fields = ('id', 'name')
        read_only_fields = ('id',)


class ProductSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Product"""
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'name', 'category', 'description')
        read_only_fields = ('id',)


class ParameterSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Parameter"""

    class Meta:
        model = Parameter
        fields = ('id', 'name')
        read_only_fields = ('id',)


class ProductParameterSerializer(serializers.ModelSerializer):
    """Сериализатор для модели ProductParameter"""
    parameter = ParameterSerializer(read_only=True)

    class Meta:
        model = ProductParameter
        fields = ('id', 'parameter', 'value')
        read_only_fields = ('id',)


class ProductInfoSerializer(serializers.ModelSerializer):
    """Сериализатор для модели ProductInfo"""
    product = ProductSerializer(read_only=True)
    shop = ShopSerializer(read_only=True)
    product_parameters = ProductParameterSerializer(many=True, read_only=True)

    class Meta:
        model = ProductInfo
        fields = ('id', 'product', 'shop', 'external_id', 'model',
                  'quantity', 'price', 'price_rrc', 'product_parameters')
        read_only_fields = ('id',)


class ContactSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Contact"""

    class Meta:
        model = Contact
        fields = ('id', 'first_name', 'last_name', 'middle_name',
                  'email', 'phone', 'city', 'street', 'house',
                  'structure', 'building', 'apartment')
        read_only_fields = ('id',)

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class OrderItemSerializer(serializers.ModelSerializer):
    """Сериализатор для модели OrderItem"""
    product_info = ProductInfoSerializer(read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ('id', 'product_info', 'quantity', 'total_price')
        read_only_fields = ('id',)

    def get_total_price(self, obj):
        """Вычисляет общую стоимость позиции"""
        return obj.quantity * obj.product_info.price


class OrderSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Order"""
    ordered_items = OrderItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()
    contact = ContactSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'user', 'dt', 'state', 'contact', 'ordered_items', 'total_price')
        read_only_fields = ('id', 'dt', 'user')

    def get_total_price(self, obj):
        """Вычисляет общую сумму заказа"""
        return obj.total_price


class OrderCreateSerializer(serializers.Serializer):
    """Сериализатор для создания заказа из корзины"""
    contact_id = serializers.IntegerField()

    def validate_contact_id(self, value):
        """Проверяет, что контакт принадлежит пользователю"""
        user = self.context['request'].user
        try:
            contact = Contact.objects.get(id=value, user=user)
        except Contact.DoesNotExist:
            raise serializers.ValidationError("Contact not found")
        return value

    @transaction.atomic
    def save(self):
        """Создает заказ из корзины"""
        user = self.context['request'].user
        contact_id = self.validated_data['contact_id']
        contact = Contact.objects.get(id=contact_id, user=user)

        # Получаем корзину пользователя (заказ со статусом 'basket')
        try:
            order = Order.objects.get(user=user, state='basket')
        except Order.DoesNotExist:
            raise serializers.ValidationError("Cart is empty")

        if order.ordered_items.count() == 0:
            raise serializers.ValidationError("Cart is empty")

        # Меняем статус на 'new'
        order.state = 'new'
        order.contact = contact
        order.save()

        return order


class CartAddSerializer(serializers.Serializer):
    """Сериализатор для добавления товара в корзину"""
    product_info_id = serializers.IntegerField()
    quantity = serializers.IntegerField(default=1, min_value=1)

    def validate_product_info_id(self, value):
        """Проверяет, что товар существует и есть в наличии"""
        try:
            product_info = ProductInfo.objects.get(id=value)
            if product_info.quantity < self.initial_data.get('quantity', 1):
                raise serializers.ValidationError("Not enough quantity available")
        except ProductInfo.DoesNotExist:
            raise serializers.ValidationError("Product not found")
        return value


class CartRemoveSerializer(serializers.Serializer):
    """Сериализатор для удаления товара из корзины"""
    product_info_id = serializers.IntegerField()
    quantity = serializers.IntegerField(required=False, min_value=1)

    def validate_product_info_id(self, value):
        """Проверяет, что товар есть в корзине"""
        try:
            ProductInfo.objects.get(id=value)
        except ProductInfo.DoesNotExist:
            raise serializers.ValidationError("Product not found")
        return value


class ShopStateSerializer(serializers.Serializer):
    """Сериализатор для изменения статуса магазина"""
    state = serializers.BooleanField(required=False)

    def validate(self, attrs):
        """Проверяет, что передан хотя бы один параметр"""
        if not attrs:
            raise serializers.ValidationError("At least one field must be provided")
        return attrs


class ProductFilterSerializer(serializers.Serializer):
    """Сериализатор для фильтрации товаров"""
    shop_id = serializers.IntegerField(required=False)
    category_id = serializers.IntegerField(required=False)
    min_price = serializers.IntegerField(required=False, min_value=0)
    max_price = serializers.IntegerField(required=False, min_value=0)
    search = serializers.CharField(required=False)

    def validate(self, attrs):
        """Проверяет, что min_price не больше max_price"""
        min_price = attrs.get('min_price')
        max_price = attrs.get('max_price')
        if min_price is not None and max_price is not None and min_price > max_price:
            raise serializers.ValidationError("min_price cannot be greater than max_price")
        return attrs