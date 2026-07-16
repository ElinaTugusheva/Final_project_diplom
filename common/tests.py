from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase

from .utils import format_price, generate_order_number, get_client_ip, validate_phone
from .validators import validate_phone_number, validate_positive_number


class UtilsTest(TestCase):
    """Тесты для утилитных функций"""

    def setUp(self):
        self.factory = RequestFactory()

    def test_validate_phone(self):
        """Тест валидации номера телефона"""
        # Правильные номера
        self.assertTrue(validate_phone("+79123456789"))
        self.assertTrue(validate_phone("79123456789"))
        self.assertTrue(validate_phone("+1234567890"))
        self.assertTrue(validate_phone("1234567890"))

        # Неправильные номера
        self.assertFalse(validate_phone("123456"))  # слишком короткий
        self.assertFalse(validate_phone("abc"))  # буквы
        self.assertFalse(validate_phone("+abc123"))  # буквы с плюсом
        self.assertFalse(validate_phone(""))  # пустая строка

    def test_format_price(self):
        """Тест форматирования цены"""
        self.assertEqual(format_price(1000), "1,000.00")
        self.assertEqual(format_price(1000.5), "1,000.50")
        self.assertEqual(format_price(1000.55), "1,000.55")
        self.assertEqual(format_price(0), "0.00")
        self.assertEqual(format_price(9999999), "9,999,999.00")

    def test_generate_order_number(self):
        """Тест генерации номера заказа"""
        self.assertEqual(generate_order_number(1), "ORD-000001")
        self.assertEqual(generate_order_number(123), "ORD-000123")
        self.assertEqual(generate_order_number(999999), "ORD-999999")
        self.assertEqual(generate_order_number(1000000), "ORD-1000000")

    def test_get_client_ip(self):
        """Тест получения IP адреса клиента"""
        # Тест с HTTP_X_FORWARDED_FOR
        request = self.factory.get("/", HTTP_X_FORWARDED_FOR="192.168.1.1, 10.0.0.1")
        self.assertEqual(get_client_ip(request), "192.168.1.1")

        # Тест с REMOTE_ADDR
        request = self.factory.get("/", REMOTE_ADDR="127.0.0.1")
        self.assertEqual(get_client_ip(request), "127.0.0.1")

        # Тест без IP
        request = self.factory.get("/")
        self.assertIsNone(get_client_ip(request))


class ValidatorsTest(TestCase):
    """Тесты для валидаторов"""

    def test_validate_phone_number(self):
        """Тест валидатора номера телефона"""
        # Правильные номера
        self.assertEqual(validate_phone_number("+79123456789"), "+79123456789")
        self.assertEqual(validate_phone_number("1234567890"), "1234567890")

        # Неправильные номера (должны вызывать ValidationError)
        with self.assertRaises(ValidationError):
            validate_phone_number("123456")

        with self.assertRaises(ValidationError):
            validate_phone_number("abc")

        with self.assertRaises(ValidationError):
            validate_phone_number("")

    def test_validate_positive_number(self):
        """Тест валидатора положительного числа"""
        # Правильные значения
        self.assertEqual(validate_positive_number(0), 0)
        self.assertEqual(validate_positive_number(10), 10)
        self.assertEqual(validate_positive_number(999.99), 999.99)

        # Неправильные значения (должны вызывать ValidationError)
        with self.assertRaises(ValidationError):
            validate_positive_number(-1)

        with self.assertRaises(ValidationError):
            validate_positive_number(-10.5)


class IntegrationTest(TestCase):
    """Интеграционные тесты для утилит"""

    def test_format_price_with_validate(self):
        """Тест форматирования цены с валидацией"""
        price = 1000.50
        formatted = format_price(price)
        self.assertEqual(formatted, "1,000.50")
        self.assertTrue("." in formatted)
        self.assertTrue("," in formatted)

    def test_generate_order_number_unique(self):
        """Тест уникальности номеров заказов"""
        numbers = set()
        for i in range(1, 101):
            order_num = generate_order_number(i)
            numbers.add(order_num)

        # Все 100 номеров должны быть уникальными
        self.assertEqual(len(numbers), 100)

    def test_validate_phone_edge_cases(self):
        """Тест граничных случаев для валидации телефона"""
        # Минимальная длина
        self.assertTrue(validate_phone("1234567890"))  # 10 цифр

        # Максимальная длина
        self.assertTrue(validate_phone("+123456789012345"))  # 16 символов с плюсом

        # С пробелами (должно быть False)
        self.assertFalse(validate_phone("+7 912 345 67 89"))

        # Со скобками (должно быть False)
        self.assertFalse(validate_phone("+7(912)345-67-89"))
