from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import ConfirmEmailToken

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для модели пользователя"""

    class Meta:
        model = User
        fields = ("id", "email", "username", "first_name", "last_name", "company", "position", "type", "is_active")
        read_only_fields = ("id", "is_active")


class UserCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания пользователя"""

    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = (
            "email",
            "username",
            "first_name",
            "last_name",
            "password",
            "password2",
            "company",
            "position",
            "type",
        )
        extra_kwargs = {
            "first_name": {"required": True},
            "last_name": {"required": True},
            "email": {"required": True},
        }

    def validate(self, attrs):
        """Проверяет, что пароли совпадают"""
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def validate_email(self, value):
        """Проверяет, что email уникален"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        """Создает пользователя"""
        validated_data.pop("password2")
        user = User.objects.create_user(**validated_data)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления профиля пользователя"""

    class Meta:
        model = User
        fields = ("first_name", "last_name", "company", "position")

    def update(self, instance, validated_data):
        """Обновляет пользователя"""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    """Сериализатор для смены пароля"""

    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    new_password2 = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        """Проверяет, что новый пароль совпадает с подтверждением"""
        if attrs["new_password"] != attrs["new_password2"]:
            raise serializers.ValidationError({"new_password": "Password fields didn't match."})
        return attrs

    def validate_old_password(self, value):
        """Проверяет, что старый пароль верный"""
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value


class ConfirmEmailTokenSerializer(serializers.ModelSerializer):
    """Сериализатор для токена подтверждения email"""

    user = UserSerializer(read_only=True)

    class Meta:
        model = ConfirmEmailToken
        fields = ("id", "user", "key", "created_at")
        read_only_fields = ("id", "key", "created_at")


class EmailSerializer(serializers.Serializer):
    """Сериализатор для отправки email"""

    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        """Проверяет, что пользователь с таким email существует"""
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email does not exist.")
        return value


class ResendConfirmationSerializer(serializers.Serializer):
    """Сериализатор для повторной отправки подтверждения"""

    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        """Проверяет, что пользователь с таким email существует и не активен"""
        try:
            user = User.objects.get(email=value)
            if user.is_active:
                raise serializers.ValidationError("User is already activated.")
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")
        return value
