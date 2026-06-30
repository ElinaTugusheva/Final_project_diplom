from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth import get_user_model

from .serializers import (
    LoginSerializer,
    PasswordResetSerializer,
    PasswordResetConfirmSerializer
)
from users.serializers import UserSerializer

User = get_user_model()


class APIRootView(APIView):
    """Корневой эндпоинт API"""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            'status': 'success',
            'message': 'Purchase Automation API v1',
            'version': '1.0.0',
            'endpoints': {
                'auth': {
                    'login': '/api/v1/auth/login/',
                    'logout': '/api/v1/auth/logout/',
                    'refresh': '/api/v1/auth/refresh/',
                    'verify': '/api/v1/auth/verify/',
                    'password_reset': '/api/v1/auth/password-reset/',
                    'password_reset_confirm': '/api/v1/auth/password-reset-confirm/',
                },
                'users': {
                    'register': '/api/v1/users/register/',
                    'profile': '/api/v1/users/profile/',
                    'confirm_email': '/api/v1/users/confirm-email/',
                    'resend_confirmation': '/api/v1/users/resend-confirmation/',
                    'change_password': '/api/v1/users/change-password/',
                },
                'shop': {
                    'products': '/api/v1/products/',
                    'categories': '/api/v1/categories/',
                    'shops': '/api/v1/shops/',
                    'contacts': '/api/v1/contacts/',
                    'cart': '/api/v1/cart/',
                    'orders': '/api/v1/orders/',
                    'import': '/api/v1/import/',
                }
            },
            'documentation': {
                'swagger': '/swagger/',
                'redoc': '/redoc/'
            }
        })


class LoginView(generics.CreateAPIView):
    """Вход пользователя"""
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)

        return Response({
            'status': 'success',
            'message': 'Login successful',
            'data': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserSerializer(user).data
            }
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """Выход пользователя"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass

        return Response({
            'status': 'success',
            'message': 'Logout successful'
        }, status=status.HTTP_200_OK)


class PasswordResetView(APIView):
    """Запрос на сброс пароля"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = User.objects.get(email=email)

            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            reset_url = f"{settings.SITE_URL}/reset-password/{uid}/{token}/"

            try:
                send_mail(
                    subject='Сброс пароля',
                    message=f'Для сброса пароля перейдите по ссылке: {reset_url}',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
            except Exception as e:
                return Response({
                    'status': 'error',
                    'message': 'Failed to send reset email',
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response({
                'status': 'success',
                'message': 'Password reset email sent'
            })

        return Response({
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    """Подтверждение сброса пароля"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            password = serializer.validated_data['password']

            uid = request.query_params.get('uid')
            token_from_url = request.query_params.get('token')

            if not uid or not token_from_url:
                return Response({
                    'status': 'error',
                    'message': 'Missing uid or token parameters'
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                uid = force_str(urlsafe_base64_decode(uid))
                user = User.objects.get(pk=uid)
            except (TypeError, ValueError, OverflowError, User.DoesNotExist):
                return Response({
                    'status': 'error',
                    'message': 'Invalid user'
                }, status=status.HTTP_400_BAD_REQUEST)

            if not default_token_generator.check_token(user, token_from_url):
                return Response({
                    'status': 'error',
                    'message': 'Invalid or expired token'
                }, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(password)
            user.save()

            return Response({
                'status': 'success',
                'message': 'Password reset successful'
            })

        return Response({
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)