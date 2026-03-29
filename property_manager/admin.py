"""
Django admin configuration for the property_manager app.

Provides rich admin interfaces with inlines, filters, and bulk actions
for managing the entire property management workflow.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Booking,
    Category,
    ChatConversation,
    ChatMessage,
    GuestDocument,
    Order,
    OrderItem,
    Property,
    PropertyPhoto,
    PushNotification,
    ServiceItem,
    Special,
)


# ---------------------------------------------------------------------------
# Inlines
# ---------------------------------------------------------------------------

class PropertyPhotoInline(admin.TabularInline):
    model = PropertyPhoto
    extra = 1
    fields = ("image", "caption", "order")


class CategoryInline(admin.TabularInline):
    model = Category
    extra = 0
    fields = ("name", "icon", "order", "is_active")
    show_change_link = True


class ServiceItemInline(admin.TabularInline):
    model = ServiceItem
    extra = 1
    fields = ("name", "price", "is_available", "is_special", "order")
    show_change_link = True


class GuestDocumentInline(admin.TabularInline):
    model = GuestDocument
    extra = 0
    fields = ("document_type", "image", "uploaded_at")
    readonly_fields = ("uploaded_at",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    fields = ("service_item", "name", "quantity", "unit_price", "subtotal")
    readonly_fields = ("subtotal",)


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    fields = ("sender_type", "content", "created_at")
    readonly_fields = ("created_at",)


# ---------------------------------------------------------------------------
# Model Admins
# ---------------------------------------------------------------------------

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "address_short", "is_active", "active_bookings_count")
    list_filter = ("is_active", "owner")
    search_fields = ("name", "address", "description")
    inlines = [PropertyPhotoInline, CategoryInline]
    fieldsets = (
        (None, {
            "fields": ("owner", "name", "address", "description", "is_active"),
        }),
        ("Guest Information", {
            "fields": ("house_rules", "wifi_network", "wifi_password",
                       "check_in_time", "check_out_time", "emergency_contacts"),
        }),
    )

    @admin.display(description="Address")
    def address_short(self, obj):
        return obj.address[:60] + "…" if len(obj.address) > 60 else obj.address

    @admin.display(description="Active Bookings")
    def active_bookings_count(self, obj):
        return obj.active_bookings.count()


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "property", "icon", "order", "items_count", "is_active")
    list_filter = ("property", "is_active")
    list_editable = ("order", "is_active")
    search_fields = ("name",)
    inlines = [ServiceItemInline]

    @admin.display(description="Items")
    def items_count(self, obj):
        return obj.items.count()


@admin.register(ServiceItem)
class ServiceItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price_display", "is_available", "is_special")
    list_filter = ("category__property", "category", "is_available", "is_special")
    list_editable = ("is_available", "is_special")
    search_fields = ("name", "description")

    @admin.display(description="Price")
    def price_display(self, obj):
        return f"€{obj.price}"


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "guest_name", "property", "check_in_date", "check_out_date",
        "status_badge", "is_active",
    )
    list_filter = ("property", "is_active", "check_in_date")
    search_fields = ("guest_name", "guest_email", "guest_phone")
    readonly_fields = ("access_code", "created_at")
    inlines = [GuestDocumentInline]
    fieldsets = (
        (None, {
            "fields": ("property", "guest_name", "guest_email", "guest_phone"),
        }),
        ("Stay Dates", {
            "fields": ("check_in_date", "check_out_date"),
        }),
        ("Settings", {
            "fields": ("access_code", "language_preference", "is_active", "notes"),
        }),
    )

    @admin.display(description="Status")
    def status_badge(self, obj):
        if obj.is_current:
            return format_html(
                '<span style="background:#22c55e;color:#fff;padding:2px 8px;'
                'border-radius:8px;font-size:11px">● Current</span>'
            )
        return format_html(
            '<span style="background:#94a3b8;color:#fff;padding:2px 8px;'
            'border-radius:8px;font-size:11px">Upcoming/Past</span>'
        )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "guest_name", "property_name", "status", "total_display", "created_at")
    list_filter = ("status", "booking__property")
    list_editable = ("status",)
    search_fields = ("booking__guest_name",)
    inlines = [OrderItemInline]
    actions = ["mark_confirmed", "mark_fulfilled", "mark_declined"]

    @admin.display(description="Guest")
    def guest_name(self, obj):
        return obj.booking.guest_name

    @admin.display(description="Property")
    def property_name(self, obj):
        return obj.booking.property.name

    @admin.display(description="Total")
    def total_display(self, obj):
        return f"€{obj.total}"

    @admin.action(description="Mark selected orders as Confirmed")
    def mark_confirmed(self, request, queryset):
        queryset.update(status="confirmed")

    @admin.action(description="Mark selected orders as Fulfilled")
    def mark_fulfilled(self, request, queryset):
        queryset.update(status="fulfilled")

    @admin.action(description="Mark selected orders as Declined")
    def mark_declined(self, request, queryset):
        queryset.update(status="declined")


@admin.register(PushNotification)
class PushNotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "property", "target_type", "scheduled_at", "is_sent")
    list_filter = ("property", "is_sent", "target_type")
    search_fields = ("title", "body")
    fieldsets = (
        (None, {
            "fields": ("property", "title", "body"),
        }),
        ("Targeting", {
            "fields": ("target_type", "target_booking", "linked_item"),
        }),
        ("Scheduling", {
            "fields": ("scheduled_at", "recurring_rule"),
        }),
        ("Status", {
            "fields": ("is_sent", "sent_at"),
        }),
    )


@admin.register(ChatConversation)
class ChatConversationAdmin(admin.ModelAdmin):
    list_display = ("booking", "is_escalated", "last_message_preview", "created_at")
    list_filter = ("is_escalated", "booking__property")
    inlines = [ChatMessageInline]

    @admin.display(description="Last Message")
    def last_message_preview(self, obj):
        msg = obj.last_message
        if msg:
            return f"[{msg.sender_type}] {msg.content[:50]}"
        return "—"


@admin.register(Special)
class SpecialAdmin(admin.ModelAdmin):
    list_display = ("display_title", "property", "service_item", "start_date", "end_date", "is_active")
    list_filter = ("property", "is_active")
    search_fields = ("title", "service_item__name")

    @admin.display(description="Title")
    def display_title(self, obj):
        return obj.title or obj.service_item.name


# Register remaining models without custom admin
admin.site.register(PropertyPhoto)
admin.site.register(GuestDocument)
admin.site.register(OrderItem)
admin.site.register(ChatMessage)

# Customize admin site header
admin.site.site_header = "EV Concierge — Property Manager"
admin.site.site_title = "EV Concierge Admin"
admin.site.index_title = "Management Dashboard"
