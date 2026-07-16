from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from . import views

app_name = "api"

urlpatterns = [
    # Корневой эндпоинт API
    path("", views.APIRootView.as_view(), name="api-root"),
    # Authentication endpoints
    path("auth/login/", views.LoginView.as_view(), name="login"),
    path("auth/logout/", views.LogoutView.as_view(), name="logout"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/verify/", TokenVerifyView.as_view(), name="token-verify"),
    # Password reset
    path("auth/password-reset/", views.PasswordResetView.as_view(), name="password-reset"),
    path("auth/password-reset-confirm/", views.PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    # User endpoints
    path("users/", include("users.urls")),
    # Shop endpoints
    path("", include("shop.urls")),
]
