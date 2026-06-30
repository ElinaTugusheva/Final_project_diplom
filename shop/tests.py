from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from .models import (
    Shop, Category, Product, ProductInfo,
    Parameter, ProductParameter, Contact, Order, OrderItem
)
from .serializers import (
    ShopSerializer, CategorySerializer, ProductSerializer,
    ProductInfoSerializer, ContactSerializer, OrderSerializer
)

User = get_user_model()


class ShopModelTest(TestCase):
    """Тесты для модели Shop"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='shop@example.com',
            password='testpass123',
            type='shop'
        )
        self.shop = Shop.objects.create(
            name='Test Shop',
            url='http://test.com',
            user=self.user,
            state=True
        )

    def test_shop_creation(self):
        """Тест создания магазина"""
        self.assertEqual(self.shop.name, 'Test Shop')
        self.assertEqual(self.shop.user, self.user)
        self.assertTrue(self.shop.state)
        self.assertEqual(str(self.shop), 'Test Shop')

    def test_shop_unique_user(self):
        """Тест уникальности пользователя для магазина"""
        with self.assertRaises(IntegrityError):
            Shop.objects.create(
                name='Another Shop',
                user=self.user
            )


class CategoryModelTest(TestCase):
    """Тесты для модели Category"""

    def setUp(self):
        self.category = Category.objects.create(name='Electronics')
        self.shop = Shop.objects.create(name='Test Shop')
        self.category.shops.add(self.shop)

    def test_category_creation(self):
        """Тест создания категории"""
        self.assertEqual(self.category.name, 'Electronics')
        self.assertEqual(str(self.category), 'Electronics')
        self.assertEqual(self.category.shops.count(), 1)
        self.assertEqual(self.category.shops.first().name, 'Test Shop')


class ProductModelTest(TestCase):
    """Тесты для модели Product"""

    def setUp(self):
        self.category = Category.objects.create(name='Electronics')
        self.product = Product.objects.create(
            name='iPhone 15',
            category=self.category,
            description='Latest iPhone model'
        )

    def test_product_creation(self):
        """Тест создания товара"""
        self.assertEqual(self.product.name, 'iPhone 15')
        self.assertEqual(self.product.category, self.category)
        self.assertEqual(self.product.description, 'Latest iPhone model')
        self.assertEqual(str(self.product), 'iPhone 15')


class ProductInfoModelTest(TestCase):
    """Тесты для модели ProductInfo"""

    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', password='testpass')
        self.shop = Shop.objects.create(name='Test Shop', user=self.user)
        self.category = Category.objects.create(name='Electronics')
        self.product = Product.objects.create(name='iPhone 15', category=self.category)
        self.product_info = ProductInfo.objects.create(
            product=self.product,
            shop=self.shop,
            external_id=123,
            model='A2849',
            quantity=10,
            price=99900,
            price_rrc=109900
        )

    def test_product_info_creation(self):
        """Тест создания информации о товаре"""
        self.assertEqual(self.product_info.product, self.product)
        self.assertEqual(self.product_info.shop, self.shop)
        self.assertEqual(self.product_info.external_id, 123)
        self.assertEqual(self.product_info.quantity, 10)
        self.assertEqual(self.product_info.price, 99900)
        self.assertEqual(str(self.product_info), 'iPhone 15 (Test Shop)')

    def test_unique_product_info(self):
        """Тест уникальности product_info"""
        with self.assertRaises(IntegrityError):
            ProductInfo.objects.create(
                product=self.product,
                shop=self.shop,
                external_id=123,
                quantity=5,
                price=89900
            )


class ParameterModelTest(TestCase):
    """Тесты для модели Parameter"""

    def setUp(self):
        self.parameter = Parameter.objects.create(name='Color')

    def test_parameter_creation(self):
        """Тест создания параметра"""
        self.assertEqual(self.parameter.name, 'Color')
        self.assertEqual(str(self.parameter), 'Color')


class ProductParameterModelTest(TestCase):
    """Тесты для модели ProductParameter"""

    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', password='testpass')
        self.shop = Shop.objects.create(name='Test Shop', user=self.user)
        self.category = Category.objects.create(name='Electronics')
        self.product = Product.objects.create(name='iPhone 15', category=self.category)
        self.product_info = ProductInfo.objects.create(
            product=self.product,
            shop=self.shop,
            external_id=123,
            quantity=10,
            price=99900
        )
        self.parameter = Parameter.objects.create(name='Color')
        self.product_parameter = ProductParameter.objects.create(
            product_info=self.product_info,
            parameter=self.parameter,
            value='Black'
        )

    def test_product_parameter_creation(self):
        """Тест создания параметра товара"""
        self.assertEqual(self.product_parameter.product_info, self.product_info)
        self.assertEqual(self.product_parameter.parameter, self.parameter)
        self.assertEqual(self.product_parameter.value, 'Black')
        self.assertEqual(str(self.product_parameter), 'Color: Black')

    def test_unique_product_parameter(self):
        """Тест уникальности product_parameter"""
        with self.assertRaises(IntegrityError):
            ProductParameter.objects.create(
                product_info=self.product_info,
                parameter=self.parameter,
                value='White'
            )


class ContactModelTest(TestCase):
    """Тесты для модели Contact"""

    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', password='testpass')
        self.contact = Contact.objects.create(
            user=self.user,
            first_name='Иван',
            last_name='Иванов',
            middle_name='Петрович',
            email='ivan@example.com',
            phone='+79123456789',
            city='Москва',
            street='Тверская',
            house='15',
            apartment='10'
        )

    def test_contact_creation(self):
        """Тест создания контакта"""
        self.assertEqual(self.contact.user, self.user)
        self.assertEqual(self.contact.first_name, 'Иван')
        self.assertEqual(self.contact.last_name, 'Иванов')
        self.assertEqual(self.contact.email, 'ivan@example.com')
        self.assertEqual(str(self.contact), 'Иванов Иван - Москва, Тверская')

    def test_get_full_address(self):
        """Тест получения полного адреса"""
        address = self.contact.get_full_address()
        self.assertEqual(address, 'Москва Тверская д.15 кв.10')


class OrderModelTest(TestCase):
    """Тесты для модели Order"""

    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', password='testpass')
        self.contact = Contact.objects.create(
            user=self.user,
            first_name='Иван',
            last_name='Иванов',
            email='ivan@example.com',
            phone='+79123456789',
            city='Москва',
            street='Тверская',
            house='15'
        )
        self.order = Order.objects.create(
            user=self.user,
            state='basket',
            contact=self.contact
        )
        self.shop = Shop.objects.create(name='Test Shop')
        self.category = Category.objects.create(name='Electronics')
        self.product = Product.objects.create(name='iPhone 15', category=self.category)
        self.product_info = ProductInfo.objects.create(
            product=self.product,
            shop=self.shop,
            external_id=123,
            quantity=10,
            price=99900
        )
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product_info=self.product_info,
            quantity=2
        )

    def test_order_creation(self):
        """Тест создания заказа"""
        self.assertEqual(self.order.user, self.user)
        self.assertEqual(self.order.state, 'basket')
        self.assertEqual(self.order.contact, self.contact)
        self.assertTrue(str(self.order).startswith('Заказ #'))

    def test_order_total_price(self):
        """Тест вычисления общей суммы заказа"""
        self.assertEqual(self.order.total_price, 199800)  # 2 * 99900

    def test_order_item_creation(self):
        """Тест создания позиции заказа"""
        self.assertEqual(self.order_item.order, self.order)
        self.assertEqual(self.order_item.product_info, self.product_info)
        self.assertEqual(self.order_item.quantity, 2)
        self.assertEqual(str(self.order_item), 'iPhone 15 x2')


class SerializerTest(TestCase):
    """Тесты для сериализаторов"""

    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', password='testpass')
        self.shop = Shop.objects.create(name='Test Shop', user=self.user)
        self.category = Category.objects.create(name='Electronics')
        self.product = Product.objects.create(name='iPhone 15', category=self.category)
        self.product_info = ProductInfo.objects.create(
            product=self.product,
            shop=self.shop,
            external_id=123,
            quantity=10,
            price=99900
        )
        self.contact = Contact.objects.create(
            user=self.user,
            first_name='Иван',
            last_name='Иванов',
            email='ivan@example.com',
            phone='+79123456789',
            city='Москва',
            street='Тверская',
            house='15'
        )

    def test_shop_serializer(self):
        """Тест сериализатора Shop"""
        serializer = ShopSerializer(self.shop)
        data = serializer.data
        self.assertEqual(data['name'], 'Test Shop')
        self.assertEqual(data['state'], True)

    def test_category_serializer(self):
        """Тест сериализатора Category"""
        serializer = CategorySerializer(self.category)
        data = serializer.data
        self.assertEqual(data['name'], 'Electronics')

    def test_product_serializer(self):
        """Тест сериализатора Product"""
        serializer = ProductSerializer(self.product)
        data = serializer.data
        self.assertEqual(data['name'], 'iPhone 15')

    def test_product_info_serializer(self):
        """Тест сериализатора ProductInfo"""
        serializer = ProductInfoSerializer(self.product_info)
        data = serializer.data
        self.assertEqual(data['price'], 99900)
        self.assertEqual(data['quantity'], 10)

    def test_contact_serializer(self):
        """Тест сериализатора Contact"""
        serializer = ContactSerializer(self.contact)
        data = serializer.data
        self.assertEqual(data['first_name'], 'Иван')
        self.assertEqual(data['last_name'], 'Иванов')


class APITest(TestCase):
    """Тесты для API эндпоинтов"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            is_active=True
        )
        self.token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

        self.shop = Shop.objects.create(name='Test Shop', state=True)
        self.category = Category.objects.create(name='Electronics')
        self.product = Product.objects.create(name='iPhone 15', category=self.category)
        self.product_info = ProductInfo.objects.create(
            product=self.product,
            shop=self.shop,
            external_id=123,
            quantity=10,
            price=99900
        )
        self.contact = Contact.objects.create(
            user=self.user,
            first_name='Иван',
            last_name='Иванов',
            email='ivan@example.com',
            phone='+79123456789',
            city='Москва',
            street='Тверская',
            house='15'
        )

    def test_products_list(self):
        """Тест списка товаров"""
        response = self.client.get('/api/v1/products/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)

    def test_product_detail(self):
        """Тест деталей товара"""
        response = self.client.get(f'/api/v1/products/{self.product_info.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['price'], 99900)

    def test_categories_list(self):
        """Тест списка категорий"""
        response = self.client.get('/api/v1/categories/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_shops_list(self):
        """Тест списка магазинов"""
        response = self.client.get('/api/v1/shops/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_contacts_list(self):
        """Тест списка контактов"""
        response = self.client.get('/api/v1/contacts/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_cart_empty(self):
        """Тест пустой корзины"""
        response = self.client.get('/api/v1/cart/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['state'], 'basket')
        self.assertEqual(len(response.data['ordered_items']), 0)

    def test_cart_add(self):
        """Тест добавления в корзину"""
        response = self.client.post('/api/v1/cart/add/', {
            'product_info_id': self.product_info.id,
            'quantity': 2
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'success')

        # Проверяем, что товар добавился
        cart_response = self.client.get('/api/v1/cart/')
        self.assertEqual(len(cart_response.data['ordered_items']), 1)

    def test_cart_add_not_enough_quantity(self):
        """Тест добавления больше чем есть в наличии"""
        response = self.client.post('/api/v1/cart/add/', {
            'product_info_id': self.product_info.id,
            'quantity': 100
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['status'], 'error')

    def test_order_create(self):
        """Тест создания заказа"""
        # Сначала добавляем товар в корзину
        self.client.post('/api/v1/cart/add/', {
            'product_info_id': self.product_info.id,
            'quantity': 2
        })

        # Создаем заказ
        response = self.client.post('/api/v1/orders/create/', {
            'contact_id': self.contact.id
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], 'success')

        # Проверяем, что заказ создался
        orders_response = self.client.get('/api/v1/orders/')
        self.assertEqual(len(orders_response.data), 1)

    def test_order_create_empty_cart(self):
        """Тест создания заказа с пустой корзиной"""
        response = self.client.post('/api/v1/orders/create/', {
            'contact_id': self.contact.id
        })
        self.assertEqual(response.status_code, 400)

    def test_order_create_invalid_contact(self):
        """Тест создания заказа с несуществующим контактом"""
        # Добавляем товар в корзину
        self.client.post('/api/v1/cart/add/', {
            'product_info_id': self.product_info.id,
            'quantity': 2
        })

        response = self.client.post('/api/v1/orders/create/', {
            'contact_id': 999
        })
        self.assertEqual(response.status_code, 404)

    def test_orders_list(self):
        """Тест списка заказов"""
        # Создаем заказ
        self.client.post('/api/v1/cart/add/', {
            'product_info_id': self.product_info.id,
            'quantity': 2
        })
        self.client.post('/api/v1/orders/create/', {
            'contact_id': self.contact.id
        })

        response = self.client.get('/api/v1/orders/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)