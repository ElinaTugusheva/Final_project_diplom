from django.contrib import admin
from .models import (
    Shop, Category, Product, ProductInfo,
    Parameter, ProductParameter, Order, OrderItem, Contact
)


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    """Административная панель для модели Shop"""
    list_display = ('name', 'url', 'state', 'user')
    list_filter = ('state',)
    search_fields = ('name', 'user__email')
    readonly_fields = ('user',)

    def save_model(self, request, obj, form, change):
        if not obj.user:
            obj.user = request.user
        super().save_model(request, obj, form, change)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Административная панель для модели Category"""
    list_display = ('name',)
    search_fields = ('name',)
    filter_horizontal = ('shops',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Административная панель для модели Product"""
    list_display = ('name', 'category')
    search_fields = ('name',)
    list_filter = ('category',)


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    """Административная панель для модели ProductInfo"""
    list_display = ('product', 'shop', 'price', 'quantity', 'external_id')
    list_filter = ('shop',)
    search_fields = ('product__name', 'shop__name', 'model')
    list_editable = ('price', 'quantity')
    readonly_fields = ('external_id',)


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    """Административная панель для модели Parameter"""
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(ProductParameter)
class ProductParameterAdmin(admin.ModelAdmin):
    """Административная панель для модели ProductParameter"""
    list_display = ('product_info', 'parameter', 'value')
    search_fields = ('product_info__product__name', 'parameter__name', 'value')
    list_filter = ('parameter',)


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """Административная панель для модели Contact"""
    list_display = ('user', 'last_name', 'first_name', 'city', 'phone', 'email')
    search_fields = ('user__email', 'last_name', 'first_name', 'phone')
    list_filter = ('city',)
    fieldsets = (
        ('Информация о пользователе', {
            'fields': ('user', 'first_name', 'last_name', 'middle_name', 'email', 'phone')
        }),
        ('Адрес', {
            'fields': ('city', 'street', 'house', 'structure', 'building', 'apartment')
        }),
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Административная панель для модели Order"""
    list_display = ('id', 'user', 'dt', 'state', 'total_price_display', 'contact')
    list_filter = ('state', 'dt')
    search_fields = ('user__email', 'id')
    readonly_fields = ('dt',)
    fieldsets = (
        ('Информация о заказе', {
            'fields': ('user', 'state', 'contact', 'dt')
        }),
    )

    def total_price_display(self, obj):
        return f"{obj.total_price} ₽"

    total_price_display.short_description = 'Общая сумма'

    def get_readonly_fields(self, request, obj=None):
        if obj:  # При редактировании существующего объекта
            return self.readonly_fields + ('user', 'contact')
        return self.readonly_fields


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Административная панель для модели OrderItem"""
    list_display = ('order', 'product_info', 'quantity', 'total_price_display')
    search_fields = ('order__id', 'product_info__product__name')
    list_filter = ('order__state',)
    readonly_fields = ('order', 'product_info')

    def total_price_display(self, obj):
        return f"{obj.quantity * obj.product_info.price} ₽"

    total_price_display.short_description = 'Сумма'