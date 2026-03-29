"""
URL configuration for the property_manager app.
"""

from django.urls import path

from . import views

app_name = "pm"

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),

    # Properties
    path("properties/", views.property_list, name="property_list"),
    path("properties/create/", views.property_create, name="property_create"),
    path("properties/<int:pk>/", views.property_detail, name="property_detail"),

    # Categories & Services
    path("properties/<int:property_pk>/categories/", views.category_manage, name="category_manage"),
    path("categories/<int:pk>/edit/", views.category_edit, name="category_edit"),
    path("categories/<int:pk>/delete/", views.category_delete, name="category_delete"),

    # Bookings
    path("bookings/", views.booking_list, name="booking_list"),
    path("bookings/create/", views.booking_create, name="booking_create"),
    path("bookings/<int:pk>/", views.booking_detail, name="booking_detail"),

    # Orders
    path("orders/", views.order_list, name="order_list"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/update-status/", views.order_update_status, name="order_update_status"),

    # Push Notifications
    path("notifications/", views.notification_list, name="notification_list"),
    path("notifications/create/", views.notification_create, name="notification_create"),
    path("notifications/<int:pk>/edit/", views.notification_edit, name="notification_edit"),
    path("notifications/<int:pk>/delete/", views.notification_delete, name="notification_delete"),

    # Chat
    path("chat/", views.chat_list, name="chat_list"),
    path("chat/<int:pk>/", views.chat_detail, name="chat_detail"),

    # Specials / Promotions
    path("specials/", views.special_list, name="special_list"),
    path("specials/create/", views.special_create, name="special_create"),
    path("specials/<int:pk>/edit/", views.special_edit, name="special_edit"),
    path("specials/<int:pk>/delete/", views.special_delete, name="special_delete"),
]
