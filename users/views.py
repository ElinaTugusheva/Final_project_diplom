from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ConfirmEmailToken
from .serializers import (
    ChangePasswordSerializer,
    ResendConfirmationSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """Регистрация нового пользователя"""

    permission_classes = [AllowAny]
    serializer_class = UserCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Создаем токен для подтверждения email
        token = ConfirmEmailToken.objects.create(user=user)

        # Отправляем письмо с подтверждением
        try:
            send_mail(
                subject="Подтверждение регистрации",
                message=f"Для подтверждения регистрации перейдите по ссылке: "
                f"{settings.SITE_URL}/api/v1/users/confirm-email/?key={token.key}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception as e:
            return Response(
                {"status": "error", "message": "User created but email confirmation failed", "error": str(e)},
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {
                "status": "success",
                "message": "User created successfully. Please confirm your email.",
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ConfirmEmailView(APIView):
    """Подтверждение email по токену"""

    permission_classes = [AllowAny]

    def get(self, request):
        key = request.query_params.get("key")
        if not key:
            return Response(
                {"status": "error", "message": "Key parameter is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        token = get_object_or_404(ConfirmEmailToken, key=key)
        user = token.user

        # Проверяем, не активирован ли уже пользователь
        if user.is_active:
            token.delete()
            return Response({"status": "success", "message": "Email already confirmed"})

        # Активируем пользователя
        user.is_active = True
        user.save()
        token.delete()

        return Response({"status": "success", "message": "Email confirmed successfully"})


class ResendConfirmationView(APIView):
    """Повторная отправка письма с подтверждением"""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResendConfirmationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"status": "error", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"]
        user = User.objects.get(email=email)

        # Удаляем старые токены и создаем новый
        ConfirmEmailToken.objects.filter(user=user).delete()
        token = ConfirmEmailToken.objects.create(user=user)

        # Отправляем письмо
        try:
            send_mail(
                subject="Подтверждение регистрации",
                message=f"Для подтверждения регистрации перейдите по ссылке: "
                f"{settings.SITE_URL}/api/v1/users/confirm-email/?key={token.key}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception as e:
            return Response(
                {"status": "error", "message": "Failed to send confirmation email", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({"status": "success", "message": "Confirmation email sent successfully"})


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Профиль пользователя"""

    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        """Используем разные сериализаторы для GET и PUT/PATCH"""
        if self.request.method in ["PUT", "PATCH"]:
            return UserUpdateSerializer
        return UserSerializer


class ChangePasswordView(APIView):
    """Смена пароля пользователя"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})

        if not serializer.is_valid():
            return Response({"status": "error", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        # Меняем пароль
        user = request.user
        new_password = serializer.validated_data["new_password"]
        user.set_password(new_password)
        user.save()

        return Response({"status": "success", "message": "Password changed successfully"})
