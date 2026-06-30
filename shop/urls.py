from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    # Товары
    path('products/', views.ProductListView.as_view(), name='product-list'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product-detail'),

    # Категории
    path('categories/', views.CategoryListView.as_view(), name='category-list'),

    # Магазины
    path('shops/', views.ShopListView.as_view(), name='shop-list'),
    path('shops/<int:pk>/toggle/', views.ShopToggleView.as_view(), name='shop-toggle'),

    # Контакты
    path('contacts/', views.ContactListView.as_view(), name='contact-list'),
    path('contacts/<int:pk>/', views.ContactDetailView.as_view(), name='contact-detail'),

    # Заказы
    path('orders/', views.OrderListView.as_view(), name='order-list'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('orders/create/', views.OrderCreateView.as_view(), name='order-create'),

    # Корзина
    path('cart/', views.CartView.as_view(), name='cart'),
    path('cart/add/', views.CartAddView.as_view(), name='cart-add'),
    path('cart/remove/', views.CartRemoveView.as_view(), name='cart-remove'),

    # Импорт товаров
    path('import/', views.PartnerImportView.as_view(), name='partner-import'),

    # Экспорт товаров
    path('export/', views.PartnerExportView.as_view(), name='partner-export'),
]