from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class APITestCase(TestCase):
    """Базовый класс для тестирования API"""

    def setUp(self):
        """Настройка перед каждым тестом"""
        self.client = APIClient()

        # Создаем тестового пользователя
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123", first_name="Test", last_name="User", is_active=True
        )

        # Получаем JWT токен для пользователя
        self.token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")


class LoginAPITest(APITestCase):
    """Тесты для входа в систему"""

    def test_login_success(self):
        """Тест успешного входа"""
        response = self.client.post("/api/v1/auth/login/", {"email": "test@example.com", "password": "testpass123"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "success")
        self.assertIn("access", response.data["data"])
        self.assertIn("refresh", response.data["data"])
        self.assertIn("user", response.data["data"])

    def test_login_invalid_password(self):
        """Тест входа с неверным паролем"""
        response = self.client.post("/api/v1/auth/login/", {"email": "test@example.com", "password": "wrongpassword"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["status"], "error")

    def test_login_inactive_user(self):
        """Тест входа неактивного пользователя"""
        # Создаем неактивного пользователя
        User.objects.create_user(email="inactive@example.com", password="testpass123", is_active=False)

        response = self.client.post("/api/v1/auth/login/", {"email": "inactive@example.com", "password": "testpass123"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["status"], "error")


class LogoutAPITest(APITestCase):
    """Тесты для выхода из системы"""

    def test_logout_success(self):
        """Тест успешного выхода"""
        refresh = str(RefreshToken.for_user(self.user))

        response = self.client.post("/api/v1/auth/logout/", {"refresh": refresh})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "success")

    def test_logout_without_refresh(self):
        """Тест выхода без refresh токена"""
        response = self.client.post("/api/v1/auth/logout/", {})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "success")


class PasswordResetAPITest(APITestCase):
    """Тесты для сброса пароля"""

    def test_password_reset_request(self):
        """Тест запроса на сброс пароля"""
        response = self.client.post("/api/v1/auth/password-reset/", {"email": "test@example.com"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "success")
        self.assertEqual(response.data["message"], "Password reset email sent")

    def test_password_reset_invalid_email(self):
        """Тест запроса сброса для несуществующего email"""
        response = self.client.post("/api/v1/auth/password-reset/", {"email": "nonexistent@example.com"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["status"], "error")


class TokenAPITest(APITestCase):
    """Тесты для JWT токенов"""

    def test_token_refresh(self):
        """Тест обновления токена"""
        refresh = str(RefreshToken.for_user(self.user))

        response = self.client.post("/api/v1/auth/refresh/", {"refresh": refresh})

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    def test_token_verify(self):
        """Тест проверки токена"""
        response = self.client.post("/api/v1/auth/verify/", {"token": self.token})

        self.assertEqual(response.status_code, 200)

    def test_token_verify_invalid(self):
        """Тест проверки невалидного токена"""
        response = self.client.post("/api/v1/auth/verify/", {"token": "invalid_token"})

        self.assertEqual(response.status_code, 401)


class UnauthorizedAPITest(TestCase):
    """Тесты для неавторизованных запросов"""

    def setUp(self):
        self.client = APIClient()

    def test_profile_unauthorized(self):
        """Тест доступа к профилю без авторизации"""
        response = self.client.get("/api/v1/users/profile/")

        self.assertEqual(response.status_code, 401)

    def test_cart_unauthorized(self):
        """Тест доступа к корзине без авторизации"""
        response = self.client.get("/api/v1/cart/")

        self.assertEqual(response.status_code, 401)

    def test_orders_unauthorized(self):
        """Тест доступа к заказам без авторизации"""
        response = self.client.get("/api/v1/orders/")

        self.assertEqual(response.status_code, 401)


class ProtectedEndpointTest(APITestCase):
    """Тесты защищенных эндпоинтов"""

    def test_profile_authenticated(self):
        """Тест доступа к профилю с авторизацией"""
        response = self.client.get("/api/v1/users/profile/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "test@example.com")

    def test_cart_authenticated(self):
        """Тест доступа к корзине с авторизацией"""
        response = self.client.get("/api/v1/cart/")

        self.assertEqual(response.status_code, 200)
        # Корзина должна быть пустой
        self.assertEqual(response.data["state"], "basket")
        self.assertEqual(len(response.data["ordered_items"]), 0)
