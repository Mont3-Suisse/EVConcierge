"""
URL configuration for the guest-facing REST API.
"""

from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    # Auth
    path('v1/auth/access-code/', views.validate_access_code, name='validate_access_code'),

    # Booking
    path('v1/bookings/<int:pk>/', views.booking_detail, name='booking_detail'),

    # Property
    path('v1/properties/<int:pk>/', views.property_detail, name='property_detail'),
    path('v1/properties/<int:pk>/categories/', views.property_categories, name='property_categories'),
    path('v1/properties/<int:pk>/specials/', views.property_specials, name='property_specials'),
    path('v1/properties/<int:pk>/instructions/', views.property_instructions, name='property_instructions'),

    # Orders
    path('v1/bookings/<int:pk>/orders/', views.booking_orders, name='booking_orders'),
    path('v1/orders/<int:pk>/cancel/', views.cancel_order, name='cancel_order'),

    # Documents
    path('v1/bookings/<int:pk>/documents/', views.booking_documents, name='booking_documents'),

    # Chat
    path('v1/bookings/<int:pk>/chat/', views.booking_chat, name='booking_chat'),

    # Notifications
    path('v1/bookings/<int:pk>/notifications/', views.booking_notifications, name='booking_notifications'),
]
