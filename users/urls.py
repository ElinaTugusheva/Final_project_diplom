from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    # Регистрация
    path("register/", views.RegisterView.as_view(), name="register"),
    # Подтверждение email
    path("confirm-email/", views.ConfirmEmailView.as_view(), name="confirm-email"),
    # Повторная отправка подтверждения
    path("resend-confirmation/", views.ResendConfirmationView.as_view(), name="resend-confirmation"),
    # Профиль пользователя
    path("profile/", views.UserProfileView.as_view(), name="profile"),
    # Смена пароля
    path("change-password/", views.ChangePasswordView.as_view(), name="change-password"),
]
