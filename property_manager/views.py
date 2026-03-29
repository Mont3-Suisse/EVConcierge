"""
Views for the property_manager dashboard webapp.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    BookingForm,
    CategoryForm,
    ChatReplyForm,
    OrderStatusForm,
    PropertyForm,
    PropertyPhotoFormSet,
    PushNotificationForm,
    ServiceItemForm,
    ServiceItemFormSet,
    SpecialForm,
)
from .models import (
    Booking,
    Category,
    ChatConversation,
    ChatMessage,
    Order,
    Property,
    PushNotification,
    ServiceItem,
    Special,
)


def _user_properties(user):
    """Get properties owned by user."""
    return Property.objects.filter(owner=user)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def dashboard(request):
    properties = _user_properties(request.user)
    today = timezone.now().date()

    # Stats
    total_properties = properties.count()
    active_bookings = Booking.objects.filter(
        property__in=properties,
        check_in_date__lte=today,
        check_out_date__gte=today,
    )
    pending_orders = Order.objects.filter(
        booking__property__in=properties,
        status="pending",
    )
    escalated_chats = ChatConversation.objects.filter(
        booking__property__in=properties,
        is_escalated=True,
    )
    recent_orders = Order.objects.filter(
        booking__property__in=properties,
    ).select_related("booking", "booking__property").order_by("-created_at")[:5]
    upcoming_notifications = PushNotification.objects.filter(
        property__in=properties,
        is_sent=False,
    ).order_by("scheduled_at")[:5]

    context = {
        "total_properties": total_properties,
        "active_bookings": active_bookings,
        "active_bookings_count": active_bookings.count(),
        "pending_orders": pending_orders,
        "pending_orders_count": pending_orders.count(),
        "escalated_chats_count": escalated_chats.count(),
        "recent_orders": recent_orders,
        "upcoming_notifications": upcoming_notifications,
    }
    return render(request, "property_manager/dashboard.html", context)


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

@login_required
def property_list(request):
    properties = _user_properties(request.user).annotate(
        bookings_count=Count("bookings"),
        categories_count=Count("categories"),
    )
    return render(request, "property_manager/properties/list.html", {
        "properties": properties,
    })


@login_required
def property_create(request):
    if request.method == "POST":
        form = PropertyForm(request.POST)
        if form.is_valid():
            prop = form.save(commit=False)
            prop.owner = request.user
            prop.save()
            messages.success(request, f"Property '{prop.name}' created.")
            return redirect("pm:property_detail", pk=prop.pk)
    else:
        form = PropertyForm()
    return render(request, "property_manager/properties/form.html", {
        "form": form,
        "title": "Create Property",
    })


@login_required
def property_detail(request, pk):
    prop = get_object_or_404(Property, pk=pk, owner=request.user)
    if request.method == "POST":
        form = PropertyForm(request.POST, instance=prop)
        photo_formset = PropertyPhotoFormSet(request.POST, request.FILES, instance=prop)
        if form.is_valid() and photo_formset.is_valid():
            form.save()
            photo_formset.save()
            messages.success(request, "Property updated.")
            return redirect("pm:property_detail", pk=prop.pk)
    else:
        form = PropertyForm(instance=prop)
        photo_formset = PropertyPhotoFormSet(instance=prop)

    return render(request, "property_manager/properties/detail.html", {
        "property": prop,
        "form": form,
        "photo_formset": photo_formset,
    })


# ---------------------------------------------------------------------------
# Categories & Services
# ---------------------------------------------------------------------------

@login_required
def category_manage(request, property_pk):
    prop = get_object_or_404(Property, pk=property_pk, owner=request.user)
    categories = prop.categories.prefetch_related("items").all()

    # Handle new category creation
    if request.method == "POST" and "create_category" in request.POST:
        cat_form = CategoryForm(request.POST)
        if cat_form.is_valid():
            cat = cat_form.save(commit=False)
            cat.property = prop
            cat.save()
            messages.success(request, f"Category '{cat.name}' created.")
            return redirect("pm:category_manage", property_pk=prop.pk)
    else:
        cat_form = CategoryForm()

    return render(request, "property_manager/categories/manage.html", {
        "property": prop,
        "categories": categories,
        "cat_form": cat_form,
    })


@login_required
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk, property__owner=request.user)
    if request.method == "POST":
        cat_form = CategoryForm(request.POST, instance=category)
        item_formset = ServiceItemFormSet(request.POST, request.FILES, instance=category)
        if cat_form.is_valid() and item_formset.is_valid():
            cat_form.save()
            item_formset.save()
            messages.success(request, f"Category '{category.name}' updated.")
            return redirect("pm:category_manage", property_pk=category.property.pk)
    else:
        cat_form = CategoryForm(instance=category)
        item_formset = ServiceItemFormSet(instance=category)

    return render(request, "property_manager/categories/edit.html", {
        "category": category,
        "property": category.property,
        "cat_form": cat_form,
        "item_formset": item_formset,
    })


@login_required
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk, property__owner=request.user)
    prop_pk = category.property.pk
    if request.method == "POST":
        name = category.name
        category.delete()
        messages.success(request, f"Category '{name}' deleted.")
    return redirect("pm:category_manage", property_pk=prop_pk)


# ---------------------------------------------------------------------------
# Bookings
# ---------------------------------------------------------------------------

@login_required
def booking_list(request):
    properties = _user_properties(request.user)
    bookings = Booking.objects.filter(property__in=properties).select_related("property")

    # Filters
    status_filter = request.GET.get("status", "")
    property_filter = request.GET.get("property", "")

    if status_filter == "current":
        today = timezone.now().date()
        bookings = bookings.filter(check_in_date__lte=today, check_out_date__gte=today)
    elif status_filter == "upcoming":
        bookings = bookings.filter(check_in_date__gt=timezone.now().date())
    elif status_filter == "past":
        bookings = bookings.filter(check_out_date__lt=timezone.now().date())

    if property_filter:
        bookings = bookings.filter(property_id=property_filter)

    return render(request, "property_manager/bookings/list.html", {
        "bookings": bookings,
        "properties": properties,
        "status_filter": status_filter,
        "property_filter": property_filter,
    })


@login_required
def booking_create(request):
    if request.method == "POST":
        form = BookingForm(request.POST, user=request.user)
        if form.is_valid():
            booking = form.save()
            messages.success(request, f"Booking for '{booking.guest_name}' created.")
            return redirect("pm:booking_detail", pk=booking.pk)
    else:
        form = BookingForm(user=request.user)
    return render(request, "property_manager/bookings/form.html", {
        "form": form,
        "title": "Create Booking",
    })


@login_required
def booking_detail(request, pk):
    booking = get_object_or_404(
        Booking, pk=pk, property__owner=request.user,
    )
    if request.method == "POST":
        form = BookingForm(request.POST, instance=booking, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Booking updated.")
            return redirect("pm:booking_detail", pk=booking.pk)
    else:
        form = BookingForm(instance=booking, user=request.user)

    orders = booking.orders.all()
    documents = booking.documents.all()

    return render(request, "property_manager/bookings/detail.html", {
        "booking": booking,
        "form": form,
        "orders": orders,
        "documents": documents,
    })


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

@login_required
def order_list(request):
    properties = _user_properties(request.user)
    orders = Order.objects.filter(
        booking__property__in=properties,
    ).select_related("booking", "booking__property").prefetch_related("items")

    status_filter = request.GET.get("status", "")
    if status_filter:
        orders = orders.filter(status=status_filter)

    return render(request, "property_manager/orders/list.html", {
        "orders": orders,
        "status_filter": status_filter,
    })


@login_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order, pk=pk, booking__property__owner=request.user,
    )
    if request.method == "POST":
        form = OrderStatusForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, f"Order #{order.pk} updated to '{order.get_status_display()}'.")
            return redirect("pm:order_detail", pk=order.pk)
    else:
        form = OrderStatusForm(instance=order)

    return render(request, "property_manager/orders/detail.html", {
        "order": order,
        "form": form,
    })


@login_required
def order_update_status(request, pk):
    """Quick status update via POST (from list view)."""
    order = get_object_or_404(Order, pk=pk, booking__property__owner=request.user)
    if request.method == "POST":
        new_status = request.POST.get("status", "")
        if new_status in dict(Order._meta.get_field("status").choices):
            order.status = new_status
            order.save()
            messages.success(request, f"Order #{order.pk} → {order.get_status_display()}")
    return redirect("pm:order_list")


# ---------------------------------------------------------------------------
# Push Notifications
# ---------------------------------------------------------------------------

@login_required
def notification_list(request):
    properties = _user_properties(request.user)
    notifications = PushNotification.objects.filter(
        property__in=properties,
    ).select_related("property", "target_booking", "linked_item")
    return render(request, "property_manager/notifications/list.html", {
        "notifications": notifications,
    })


@login_required
def notification_create(request):
    if request.method == "POST":
        form = PushNotificationForm(request.POST, user=request.user)
        if form.is_valid():
            notif = form.save()
            messages.success(request, f"Notification '{notif.title}' created.")
            return redirect("pm:notification_list")
    else:
        form = PushNotificationForm(user=request.user)
    return render(request, "property_manager/notifications/form.html", {
        "form": form,
        "title": "Create Notification",
    })


@login_required
def notification_edit(request, pk):
    notif = get_object_or_404(PushNotification, pk=pk, property__owner=request.user)
    if request.method == "POST":
        form = PushNotificationForm(request.POST, instance=notif, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Notification updated.")
            return redirect("pm:notification_list")
    else:
        form = PushNotificationForm(instance=notif, user=request.user)
    return render(request, "property_manager/notifications/form.html", {
        "form": form,
        "title": "Edit Notification",
    })


@login_required
def notification_delete(request, pk):
    notif = get_object_or_404(PushNotification, pk=pk, property__owner=request.user)
    if request.method == "POST":
        notif.delete()
        messages.success(request, "Notification deleted.")
    return redirect("pm:notification_list")


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

@login_required
def chat_list(request):
    properties = _user_properties(request.user)
    conversations = ChatConversation.objects.filter(
        booking__property__in=properties,
    ).select_related("booking", "booking__property")

    show_escalated = request.GET.get("escalated", "")
    if show_escalated:
        conversations = conversations.filter(is_escalated=True)

    return render(request, "property_manager/chat/list.html", {
        "conversations": conversations,
        "show_escalated": show_escalated,
    })


@login_required
def chat_detail(request, pk):
    conversation = get_object_or_404(
        ChatConversation, pk=pk, booking__property__owner=request.user,
    )
    if request.method == "POST":
        form = ChatReplyForm(request.POST)
        if form.is_valid():
            ChatMessage.objects.create(
                conversation=conversation,
                sender_type="manager",
                content=form.cleaned_data["content"],
            )
            messages.success(request, "Reply sent.")
            return redirect("pm:chat_detail", pk=conversation.pk)
    else:
        form = ChatReplyForm()

    chat_messages = conversation.messages.all()

    return render(request, "property_manager/chat/detail.html", {
        "conversation": conversation,
        "chat_messages": chat_messages,
        "form": form,
    })


# ---------------------------------------------------------------------------
# Specials / Promotions
# ---------------------------------------------------------------------------

@login_required
def special_list(request):
    properties = _user_properties(request.user)
    specials = Special.objects.filter(
        property__in=properties,
    ).select_related("property", "service_item", "linked_notification")
    return render(request, "property_manager/specials/list.html", {
        "specials": specials,
    })


@login_required
def special_create(request):
    if request.method == "POST":
        form = SpecialForm(request.POST, user=request.user)
        if form.is_valid():
            special = form.save()
            messages.success(request, "Special/promotion created.")
            return redirect("pm:special_list")
    else:
        form = SpecialForm(user=request.user)
    return render(request, "property_manager/specials/form.html", {
        "form": form,
        "title": "Create Special",
    })


@login_required
def special_edit(request, pk):
    special = get_object_or_404(Special, pk=pk, property__owner=request.user)
    if request.method == "POST":
        form = SpecialForm(request.POST, instance=special, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Special updated.")
            return redirect("pm:special_list")
    else:
        form = SpecialForm(instance=special, user=request.user)
    return render(request, "property_manager/specials/form.html", {
        "form": form,
        "title": "Edit Special",
    })


@login_required
def special_delete(request, pk):
    special = get_object_or_404(Special, pk=pk, property__owner=request.user)
    if request.method == "POST":
        special.delete()
        messages.success(request, "Special deleted.")
    return redirect("pm:special_list")
