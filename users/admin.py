from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import ConfirmEmailToken, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Административная панель для модели User"""

    list_display = ("email", "first_name", "last_name", "type", "is_active", "is_staff")
    list_filter = ("type", "is_active", "is_staff")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "company", "position", "type")}),
        (
            _("Permissions"),
            {
                "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )


@admin.register(ConfirmEmailToken)
class ConfirmEmailTokenAdmin(admin.ModelAdmin):
    """Административная панель для модели ConfirmEmailToken"""

    list_display = ("user", "key", "created_at")
    search_fields = ("user__email", "key")
    readonly_fields = ("key", "created_at")
    list_filter = ("created_at",)

    def has_add_permission(self, request):
        """Запрещаем добавление токенов через админку"""
        return False
