"""
DRF Serializers for the guest-facing mobile API.
"""

from rest_framework import serializers
from ..models import (
    Property, PropertyImage, Booking, GuestDocument,
    Category, ServiceItem, Order, OrderItem,
    Instruction, InstructionImage, Special,
    ChatConversation, ChatMessage, PushNotification,
)


class PropertyImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyImage
        fields = ['id', 'image', 'caption', 'order']


class PropertySerializer(serializers.ModelSerializer):
    image_urls = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            'id', 'name', 'nickname', 'description', 'address', 'city',
            'phone', 'email', 'property_manager_name', 'property_manager_phone',
            'wifi_network', 'wifi_password', 'house_rules', 'emergency_contacts',
            'welcome_message', 'check_in_time', 'check_out_time',
            'property_type', 'capacity', 'bedrooms', 'bathrooms',
            'pets_allowed', 'smoking_allowed', 'image_urls',
        ]

    def get_image_urls(self, obj):
        request = self.context.get('request')
        images = obj.images.order_by('order').all()
        if request:
            return [request.build_absolute_uri(img.image.url) for img in images if img.image]
        return [img.image.url for img in images if img.image]


class ServiceItemSerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = ServiceItem
        fields = ['id', 'name', 'description', 'photo_url', 'price',
                  'is_available', 'is_special', 'order']

    def get_photo_url(self, obj):
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        return None


class CategorySerializer(serializers.ModelSerializer):
    items = ServiceItemSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'icon', 'description', 'order', 'is_active', 'items']


class BookingSerializer(serializers.ModelSerializer):
    stay_day = serializers.ReadOnlyField()
    total_nights = serializers.ReadOnlyField()
    total_expenses = serializers.ReadOnlyField()

    class Meta:
        model = Booking
        fields = [
            'id', 'property', 'guest_name', 'guest_email', 'guest_phone',
            'check_in_date', 'check_out_date', 'num_guests', 'access_code',
            'language_preference', 'notes', 'is_active',
            'stay_day', 'total_nights', 'total_expenses',
        ]


class GuestDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuestDocument
        fields = ['id', 'document_type', 'image', 'uploaded_at']


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'service_item', 'name', 'quantity', 'unit_price', 'subtotal']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    total = serializers.ReadOnlyField()

    class Meta:
        model = Order
        fields = ['id', 'booking', 'status', 'notes', 'items', 'total',
                  'created_at', 'updated_at']


class InstructionImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstructionImage
        fields = ['id', 'image', 'caption', 'is_main', 'order']


class InstructionSerializer(serializers.ModelSerializer):
    images = InstructionImageSerializer(many=True, read_only=True)
    image_urls = serializers.SerializerMethodField()

    class Meta:
        model = Instruction
        fields = ['id', 'title', 'content', 'instruction_type', 'video',
                  'order', 'images', 'image_urls']

    def get_image_urls(self, obj):
        request = self.context.get('request')
        images = obj.images.order_by('order').all()
        if request:
            return [request.build_absolute_uri(img.image.url) for img in images if img.image]
        return [img.image.url for img in images if img.image]


class SpecialSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='service_item.name', read_only=True)
    item_description = serializers.CharField(source='service_item.description', read_only=True)
    price = serializers.DecimalField(source='service_item.price',
                                     max_digits=10, decimal_places=2, read_only=True)
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Special
        fields = ['id', 'service_item', 'title', 'item_name', 'item_description',
                  'price', 'photo_url', 'start_date', 'end_date', 'is_active']

    def get_photo_url(self, obj):
        if obj.service_item.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.service_item.photo.url)
            return obj.service_item.photo.url
        return None


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'sender_type', 'content', 'created_at']


class ChatConversationSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta:
        model = ChatConversation
        fields = ['id', 'booking', 'is_escalated', 'escalated_at',
                  'created_at', 'messages']


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushNotification
        fields = ['id', 'title', 'body', 'linked_item', 'scheduled_at',
                  'is_sent', 'sent_at', 'created_at']


class OrderCreateSerializer(serializers.Serializer):
    """Serializer for creating an order from cart items."""
    items = serializers.ListField(child=serializers.DictField())
    notes = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item is required.")
        for item in value:
            if 'service_item_id' not in item or 'quantity' not in item:
                raise serializers.ValidationError(
                    "Each item must have 'service_item_id' and 'quantity'."
                )
        return value
