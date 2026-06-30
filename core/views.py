from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse


def index(request):
    """Главная страница API"""
    return JsonResponse({
        'status': 'success',
        'message': 'Welcome to Purchase Automation API',
        'version': '1.0.0',
        'documentation': {
            'swagger': '/swagger/',
            'redoc': '/redoc/'
        },
        'endpoints': {
            'admin': '/admin/',
            'api': '/api/v1/',
            'auth': '/api/v1/auth/',
            'users': '/api/v1/users/',
            'products': '/api/v1/products/',
            'cart': '/api/v1/cart/',
            'orders': '/api/v1/orders/',
            'contacts': '/api/v1/contacts/',
            'import': '/api/v1/import/'
        }
    })