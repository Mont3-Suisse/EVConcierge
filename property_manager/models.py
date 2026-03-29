"""
Property Manager models for EVConcierge.

Covers: Properties, Categories, Services, Bookings,
        Orders, Push Notifications, Chat, and Specials.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

# Save built-in 'property' before model fields shadow it
_property = property


# ---------------------------------------------------------------------------
# Property
# ---------------------------------------------------------------------------

class Property(models.Model):
    """A vacation rental property managed by a property manager."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="properties",
    )
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    description = models.TextField(blank=True)
    house_rules = models.TextField(blank=True)
    wifi_network = models.CharField(max_length=100, blank=True)
    wifi_password = models.CharField(max_length=100, blank=True)
    check_in_time = models.TimeField(default="15:00")
    check_out_time = models.TimeField(default="10:00")
    emergency_contacts = models.TextField(
        blank=True,
        help_text="Emergency phone numbers and contacts, one per line.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "properties"
        ordering = ["name"]

    def __str__(self):
        return self.name

    @_property
    def active_bookings(self):
        today = timezone.now().date()
        return self.bookings.filter(
            check_in_date__lte=today,
            check_out_date__gte=today,
        )


class PropertyPhoto(models.Model):
    """Photo attached to a property."""

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="photos",
    )
    image = models.ImageField(upload_to="properties/photos/%Y/%m/")
    caption = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.property.name} — photo {self.order}"


# ---------------------------------------------------------------------------
# Categories & Services
# ---------------------------------------------------------------------------

class Category(models.Model):
    """
    Service category displayed on the guest home screen.
    e.g. Food & Drinks, Experiences, Discover, Wellness, Transport, Add-ons.
    """

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="categories",
    )
    name = models.CharField(max_length=100)
    icon = models.CharField(
        max_length=10,
        blank=True,
        help_text="Emoji or icon code for the category card.",
    )
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["order", "name"]
        unique_together = [("property", "name")]

    def __str__(self):
        return f"{self.name} ({self.property.name})"


class ServiceItem(models.Model):
    """An individual item or service within a category."""

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="items",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    photo = models.ImageField(
        upload_to="services/photos/%Y/%m/",
        blank=True,
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_available = models.BooleanField(default=True)
    is_special = models.BooleanField(
        default=False,
        help_text="Mark as a promoted/special item on the home screen.",
    )
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.name} (€{self.price})"

    @_property
    def linked_property(self):
        return self.category.property


# ---------------------------------------------------------------------------
# Bookings & Guest Documents
# ---------------------------------------------------------------------------

LANGUAGE_CHOICES = [
    ("en", "English"),
    ("it", "Italian"),
    ("de", "German"),
    ("fr", "French"),
    ("es", "Spanish"),
]


class Booking(models.Model):
    """A guest booking with access dates."""

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    guest_name = models.CharField(max_length=200)
    guest_email = models.EmailField(blank=True)
    guest_phone = models.CharField(max_length=50, blank=True)
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    access_code = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        help_text="Unique code for guest app access.",
    )
    language_preference = models.CharField(
        max_length=5,
        choices=LANGUAGE_CHOICES,
        default="en",
    )
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-check_in_date"]

    def __str__(self):
        return f"{self.guest_name} @ {self.property.name} ({self.check_in_date} → {self.check_out_date})"

    @_property
    def is_current(self):
        today = timezone.now().date()
        return self.check_in_date <= today <= self.check_out_date

    @_property
    def stay_day(self):
        """Current day number of the stay (1-based)."""
        today = timezone.now().date()
        if today < self.check_in_date:
            return 0
        return (today - self.check_in_date).days + 1

    @_property
    def total_nights(self):
        return (self.check_out_date - self.check_in_date).days

    @_property
    def total_expenses(self):
        total = self.orders.aggregate(
            total=models.Sum("items__subtotal"),
        )["total"]
        return total or 0


DOCUMENT_TYPE_CHOICES = [
    ("passport", "Passport"),
    ("id_card", "ID Card"),
    ("drivers_license", "Driver's License"),
    ("other", "Other"),
]


class GuestDocument(models.Model):
    """ID/passport upload for a booking."""

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(
        max_length=20,
        choices=DOCUMENT_TYPE_CHOICES,
        default="passport",
    )
    image = models.ImageField(upload_to="guests/documents/%Y/%m/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_document_type_display()} — {self.booking.guest_name}"


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

ORDER_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("confirmed", "Confirmed"),
    ("declined", "Declined"),
    ("fulfilled", "Fulfilled"),
]


class Order(models.Model):
    """An order placed by a guest during their stay."""

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        default="pending",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk} — {self.booking.guest_name} ({self.status})"

    @_property
    def total(self):
        return sum(item.subtotal for item in self.items.all())

    @_property
    def linked_property(self):
        return self.booking.property


class OrderItem(models.Model):
    """A line item within an order."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )
    service_item = models.ForeignKey(
        ServiceItem,
        on_delete=models.SET_NULL,
        null=True,
        related_name="order_items",
    )
    name = models.CharField(
        max_length=200,
        help_text="Snapshot of item name at time of order.",
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.subtotal = self.unit_price * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} x{self.quantity}"


# ---------------------------------------------------------------------------
# Push Notifications
# ---------------------------------------------------------------------------

NOTIFICATION_TARGET_CHOICES = [
    ("all_guests", "All Current Guests"),
    ("specific_booking", "Specific Booking"),
]


class PushNotification(models.Model):
    """A push notification composed by the property manager."""

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    title = models.CharField(max_length=200)
    body = models.TextField()
    target_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TARGET_CHOICES,
        default="all_guests",
    )
    target_booking = models.ForeignKey(
        Booking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="targeted_notifications",
        help_text="Required if target type is 'Specific Booking'.",
    )
    linked_item = models.ForeignKey(
        ServiceItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
        help_text="Deep-link to this item when notification is tapped.",
    )
    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Leave blank to send immediately.",
    )
    recurring_rule = models.CharField(
        max_length=200,
        blank=True,
        help_text="e.g. 'every Tuesday at 17:00'. Free text for now.",
    )
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        status = "Sent" if self.is_sent else "Draft"
        return f"[{status}] {self.title}"


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class ChatConversation(models.Model):
    """A chat thread for a booking."""

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    is_escalated = models.BooleanField(
        default=False,
        help_text="True when guest requested human support.",
    )
    escalated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        tag = " [ESCALATED]" if self.is_escalated else ""
        return f"Chat — {self.booking.guest_name}{tag}"

    @_property
    def last_message(self):
        return self.messages.order_by("-created_at").first()


SENDER_TYPE_CHOICES = [
    ("guest", "Guest"),
    ("ai", "AI Assistant"),
    ("manager", "Property Manager"),
]


class ChatMessage(models.Model):
    """A single message in a chat conversation."""

    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender_type = models.CharField(
        max_length=10,
        choices=SENDER_TYPE_CHOICES,
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.sender_type}] {self.content[:50]}"


# ---------------------------------------------------------------------------
# Specials / Promotions
# ---------------------------------------------------------------------------

class Special(models.Model):
    """A promoted item featured on the guest home screen."""

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="specials",
    )
    service_item = models.ForeignKey(
        ServiceItem,
        on_delete=models.CASCADE,
        related_name="specials",
    )
    title = models.CharField(
        max_length=200,
        blank=True,
        help_text="Override title. Defaults to service item name.",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    linked_notification = models.ForeignKey(
        PushNotification,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="specials",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        display = self.title or self.service_item.name
        return f"⭐ {display} ({self.start_date} → {self.end_date})"

    @_property
    def is_current(self):
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date and self.is_active
