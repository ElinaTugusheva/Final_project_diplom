from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .models import ConfirmEmailToken
from .serializers import UserCreateSerializer, UserSerializer

User = get_user_model()


class UserModelTest(TestCase):
    """Тесты для модели User"""

    def test_create_user(self):
        """Тест создания обычного пользователя"""
        user = User.objects.create_user(
            email="test@example.com", password="testpass123", first_name="Test", last_name="User"
        )
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.check_password("testpass123"))
        self.assertFalse(user.is_active)
        self.assertEqual(user.type, "buyer")
        self.assertEqual(str(user), "Test User")
        self.assertEqual(user.get_full_name(), "User Test")

    def test_create_user_with_company(self):
        """Тест создания пользователя с компанией"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
            company="Test Company",
            position="Developer",
            type="shop",
            is_active=True,
        )
        self.assertEqual(user.company, "Test Company")
        self.assertEqual(user.position, "Developer")
        self.assertEqual(user.type, "shop")

    def test_create_superuser(self):
        """Тест создания суперпользователя"""
        admin = User.objects.create_superuser(email="admin@example.com", password="adminpass123")
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_active)

    def test_create_user_without_email(self):
        """Тест создания пользователя без email"""
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="testpass123")

    def test_create_superuser_without_staff(self):
        """Тест создания суперпользователя без прав"""
        with self.assertRaises(ValueError):
            User.objects.create_superuser(email="admin@example.com", password="adminpass123", is_staff=False)

    def test_user_unique_email(self):
        """Тест уникальности email"""
        User.objects.create_user(email="test@example.com", password="testpass123")
        with self.assertRaises(Exception):
            User.objects.create_user(email="test@example.com", password="testpass123")


class ConfirmEmailTokenModelTest(TestCase):
    """Тесты для модели ConfirmEmailToken"""

    def setUp(self):
        self.user = User.objects.create_user(email="test@example.com", password="testpass123")
        self.token = ConfirmEmailToken.objects.create(user=self.user)

    def test_token_creation(self):
        """Тест создания токена"""
        self.assertIsNotNone(self.token.key)
        self.assertEqual(self.token.user, self.user)
        self.assertIsNotNone(self.token.created_at)
        self.assertEqual(str(self.token), f"Token for {self.user.email}")

    def test_token_unique_key(self):
        """Тест уникальности ключа токена"""
        token2 = ConfirmEmailToken.objects.create(user=self.user)
        self.assertNotEqual(self.token.key, token2.key)

    def test_token_auto_generate(self):
        """Тест автоматической генерации ключа"""
        token = ConfirmEmailToken(user=self.user)
        token.save()
        self.assertIsNotNone(token.key)


class UserSerializerTest(TestCase):
    """Тесты для сериализаторов пользователей"""

    def setUp(self):
        self.user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "password": "SecurePass123!",
            "password2": "SecurePass123!",
            "company": "Test Company",
            "position": "Developer",
            "type": "buyer",
        }

    def test_user_create_serializer_valid(self):
        """Тест валидного сериализатора создания пользователя"""
        serializer = UserCreateSerializer(data=self.user_data)
        self.assertTrue(serializer.is_valid())
        user = serializer.save()
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.first_name, "Test")
        self.assertEqual(user.last_name, "User")

    def test_user_create_serializer_password_mismatch(self):
        """Тест несовпадения паролей"""
        data = self.user_data.copy()
        data["password2"] = "DifferentPass123!"
        serializer = UserCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)

    def test_user_create_serializer_duplicate_email(self):
        """Тест дублирования email"""
        User.objects.create_user(email="test@example.com", password="testpass123")
        serializer = UserCreateSerializer(data=self.user_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_user_serializer(self):
        """Тест сериализатора пользователя"""
        user = User.objects.create_user(
            email="test@example.com", password="testpass123", first_name="Test", last_name="User"
        )
        serializer = UserSerializer(user)
        data = serializer.data
        self.assertEqual(data["email"], "test@example.com")
        self.assertEqual(data["first_name"], "Test")
        self.assertEqual(data["last_name"], "User")
        self.assertEqual(data["type"], "buyer")
        self.assertFalse(data["is_active"])


class UserAPITest(TestCase):
    """Тесты для API пользователей"""

    def setUp(self):
        self.client = APIClient()
        self.user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "password": "SecurePass123!",
            "password2": "SecurePass123!",
        }

    def test_register_success(self):
        """Тест успешной регистрации"""
        response = self.client.post("/api/v1/users/register/", self.user_data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "success")
        self.assertEqual(response.data["message"], "User created successfully. Please confirm your email.")
        self.assertEqual(response.data["user"]["email"], "test@example.com")

        # Проверяем, что создан токен
        user = User.objects.get(email="test@example.com")
        self.assertTrue(ConfirmEmailToken.objects.filter(user=user).exists())

        # Проверяем, что отправлено письмо
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Подтверждение регистрации", mail.outbox[0].subject)
        self.assertIn("confirm-email", mail.outbox[0].body)

    def test_register_password_mismatch(self):
        """Тест регистрации с несовпадающими паролями"""
        data = self.user_data.copy()
        data["password2"] = "DifferentPass123!"
        response = self.client.post("/api/v1/users/register/", data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data)

    def test_register_duplicate_email(self):
        """Тест регистрации с существующим email"""
        User.objects.create_user(email="test@example.com", password="testpass123")
        response = self.client.post("/api/v1/users/register/", self.user_data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)

    def test_confirm_email_success(self):
        """Тест успешного подтверждения email"""
        # Регистрируем пользователя
        response = self.client.post("/api/v1/users/register/", self.user_data)
        user = User.objects.get(email="test@example.com")
        token = ConfirmEmailToken.objects.get(user=user)

        # Подтверждаем email
        response = self.client.get(f"/api/v1/users/confirm-email/?key={token.key}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "success")
        self.assertEqual(response.data["message"], "Email confirmed successfully")

        # Проверяем, что пользователь активирован
        user.refresh_from_db()
        self.assertTrue(user.is_active)

        # Проверяем, что токен удален
        self.assertFalse(ConfirmEmailToken.objects.filter(user=user).exists())

    def test_confirm_email_invalid_key(self):
        """Тест подтверждения с неверным ключом"""
        response = self.client.get("/api/v1/users/confirm-email/?key=invalid_key")
        self.assertEqual(response.status_code, 404)

    def test_resend_confirmation_success(self):
        """Тест повторной отправки подтверждения"""
        # Регистрируем пользователя
        self.client.post("/api/v1/users/register/", self.user_data)

        # Отправляем повторное письмо
        response = self.client.post("/api/v1/users/resend-confirmation/", {"email": "test@example.com"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "success")
        self.assertEqual(response.data["message"], "Confirmation email sent successfully")

        # Проверяем, что отправлено письмо
        self.assertEqual(len(mail.outbox), 2)

    def test_resend_confirmation_already_active(self):
        """Тест повторной отправки для активного пользователя"""
        # Создаем активного пользователя
        User.objects.create_user(email="test@example.com", password="testpass123", is_active=True)

        response = self.client.post("/api/v1/users/resend-confirmation/", {"email": "test@example.com"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["status"], "error")

    def test_profile_get_authenticated(self):
        """Тест получения профиля авторизованного пользователя"""
        # Создаем пользователя
        user = User.objects.create_user(
            email="test@example.com", password="testpass123", first_name="Test", last_name="User", is_active=True
        )

        # Получаем токен
        token = str(RefreshToken.for_user(user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Получаем профиль
        response = self.client.get("/api/v1/users/profile/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "test@example.com")
        self.assertEqual(response.data["first_name"], "Test")
        self.assertEqual(response.data["last_name"], "User")

    def test_profile_get_unauthenticated(self):
        """Тест получения профиля без авторизации"""
        response = self.client.get("/api/v1/users/profile/")
        self.assertEqual(response.status_code, 401)

    def test_profile_update(self):
        """Тест обновления профиля"""
        # Создаем пользователя
        user = User.objects.create_user(
            email="test@example.com", password="testpass123", first_name="Test", last_name="User", is_active=True
        )

        # Получаем токен
        token = str(RefreshToken.for_user(user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Обновляем профиль
        response = self.client.put(
            "/api/v1/users/profile/",
            {"first_name": "Updated", "last_name": "Name", "company": "New Company", "position": "Manager"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["first_name"], "Updated")
        self.assertEqual(response.data["last_name"], "Name")
        self.assertEqual(response.data["company"], "New Company")
        self.assertEqual(response.data["position"], "Manager")

    def test_profile_update_partial(self):
        """Тест частичного обновления профиля"""
        # Создаем пользователя
        user = User.objects.create_user(
            email="test@example.com", password="testpass123", first_name="Test", last_name="User", is_active=True
        )

        # Получаем токен
        token = str(RefreshToken.for_user(user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Частично обновляем профиль
        response = self.client.patch("/api/v1/users/profile/", {"first_name": "Updated"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["first_name"], "Updated")
        self.assertEqual(response.data["last_name"], "User")


class UserIntegrationTest(TestCase):
    """Интеграционные тесты для пользователей"""

    def test_full_registration_flow(self):
        """Тест полного потока регистрации"""
        # 1. Регистрация
        client = APIClient()
        response = client.post(
            "/api/v1/users/register/",
            {
                "email": "newuser@example.com",
                "username": "newuser",
                "first_name": "New",
                "last_name": "User",
                "password": "SecurePass123!",
                "password2": "SecurePass123!",
            },
        )
        self.assertEqual(response.status_code, 201)

        # 2. Получаем токен
        user = User.objects.get(email="newuser@example.com")
        token = ConfirmEmailToken.objects.get(user=user)

        # 3. Подтверждаем email
        response = client.get(f"/api/v1/users/confirm-email/?key={token.key}")
        self.assertEqual(response.status_code, 200)

        # 4. Проверяем, что пользователь активен
        user.refresh_from_db()
        self.assertTrue(user.is_active)

        # 5. Входим в систему
        response = client.post("/api/v1/auth/login/", {"email": "newuser@example.com", "password": "SecurePass123!"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data["data"])

        # 6. Получаем профиль
        access_token = response.data["data"]["access"]
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = client.get("/api/v1/users/profile/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "newuser@example.com")
