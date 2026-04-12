"""
Guest-facing REST API views for the EV Concierge mobile app.

Authentication is via booking access_code (UUID) passed as X-Access-Code header.
"""

import datetime

from django.conf import settings as django_settings
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import (
    Booking, Category, ServiceItem, Order, OrderItem,
    GuestDocument, ChatConversation, ChatMessage,
    PushNotification, Special, OwnerOffering,
)


# Sections shown in the guest mobile app's category grid (specials are
# served separately by the /specials/ endpoint).
SECTIONS_GRID = [
    ('food_drinks', 'Food & Drinks', '🍴',
     'Meals, snacks, wine & spirits, groceries, coffee, cocktails'),
    ('experiences', 'Experiences', '🏆',
     'Boat trips, cooking classes, yoga, guided tours, excursions'),
    ('discover', 'Discover', '📍',
     'Curated beaches, restaurants, hidden gems'),
    ('wellness', 'Wellness', '💆',
     'Massage, spa, personal trainer'),
    ('transport', 'Transport', '🚗',
     'Airport transfer, car rental, scooter'),
    ('addons', 'Add-ons', '🎁',
     'Extra towels, baby cot, BBQ kit, late checkout'),
]


def _absolute_photo_url(request, image_field):
    if not image_field:
        return None
    try:
        return request.build_absolute_uri(image_field.url) if request else image_field.url
    except Exception:
        return None


def _serialize_offering(offering, request, category_id):
    return {
        'id': offering.id,
        'category': category_id,
        'name': offering.name,
        'description': offering.description,
        'photo_url': _absolute_photo_url(request, offering.photo),
        'price': float(offering.price) if offering.price is not None else 0,
        'is_available': offering.is_active,
        'is_special': offering.section == OwnerOffering.SECTION_SPECIALS,
        'order': offering.order,
    }
from .serializers import (
    PropertySerializer, BookingSerializer, CategorySerializer,
    OrderSerializer, OrderCreateSerializer, GuestDocumentSerializer,
    InstructionSerializer, SpecialSerializer,
    ChatConversationSerializer, ChatMessageSerializer,
    NotificationSerializer,
)


# ─── Helper ───

def _get_booking_from_request(request):
    """Extract and validate booking from X-Access-Code header."""
    access_code = request.headers.get('X-Access-Code', '')
    if not access_code:
        return None, Response(
            {'error': 'Access code required'},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    try:
        booking = Booking.objects.select_related('property').get(
            access_code=access_code,
            is_active=True,
        )
    except Booking.DoesNotExist:
        return None, Response(
            {'error': 'Invalid or expired access code'},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    # Check date validity (skip in development / DEBUG mode)
    if not django_settings.DEBUG:
        today = timezone.now().date()
        if today < booking.check_in_date or today > booking.check_out_date:
            return None, Response(
                {'error': 'Booking access has expired'},
                status=status.HTTP_403_FORBIDDEN,
            )
    return booking, None


# ─── Auth ───

@api_view(['POST'])
def validate_access_code(request):
    """Validate a booking access code and return booking + property data."""
    code = request.data.get('access_code', '')
    if not code:
        return Response(
            {'error': 'Access code is required'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        booking = Booking.objects.select_related('property').get(
            access_code=code,
            is_active=True,
        )
    except Booking.DoesNotExist:
        return Response(
            {'error': 'Invalid access code'},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response({
        'booking': BookingSerializer(booking).data,
        'property': PropertySerializer(
            booking.property, context={'request': request}
        ).data,
    })


# ─── Booking ───

@api_view(['GET'])
def booking_detail(request, pk):
    booking, error = _get_booking_from_request(request)
    if error:
        return error
    if booking.id != pk:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    return Response(BookingSerializer(booking).data)


# ─── Property ───

@api_view(['GET'])
def property_detail(request, pk):
    booking, error = _get_booking_from_request(request)
    if error:
        return error
    if booking.property_id != pk:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    return Response(
        PropertySerializer(booking.property, context={'request': request}).data
    )


# ─── Categories ───

@api_view(['GET'])
def property_categories(request, pk):
    """
    Returns the six guest-facing sections (Food & Drinks, Experiences,
    Discover, Wellness, Transport, Add-ons) populated from OwnerOffering
    rows that the property owner has linked to this property. Today's
    Specials are served by the /specials/ endpoint.
    """
    booking, error = _get_booking_from_request(request)
    if error:
        return error
    if booking.property_id != pk:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    offerings = OwnerOffering.objects.filter(
        properties__id=pk,
        is_active=True,
    ).order_by('order', 'name')

    by_section = {}
    for o in offerings:
        if o.section == OwnerOffering.SECTION_SPECIALS:
            continue
        by_section.setdefault(o.section, []).append(o)

    result = []
    for idx, (section_key, name, icon, desc) in enumerate(SECTIONS_GRID, start=1):
        items = by_section.get(section_key, [])
        result.append({
            'id': idx,
            'name': name,
            'icon': icon,
            'description': desc,
            'order': idx,
            'is_active': True,
            'items': [_serialize_offering(o, request, idx) for o in items],
        })
    return Response(result)


# ─── Specials ───

@api_view(['GET'])
def property_specials(request, pk):
    """
    Returns OwnerOffering rows in the 'specials' section that are linked to
    this property and are within their (optional) availability window.
    """
    booking, error = _get_booking_from_request(request)
    if error:
        return error
    if booking.property_id != pk:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    today = timezone.now().date()
    qs = OwnerOffering.objects.filter(
        properties__id=pk,
        section=OwnerOffering.SECTION_SPECIALS,
        is_active=True,
    ).filter(
        Q(start_date__isnull=True) | Q(start_date__lte=today)
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=today)
    ).order_by('order', 'name')

    far_future = today + datetime.timedelta(days=365)
    result = []
    for o in qs:
        result.append({
            'id': o.id,
            'service_item': o.id,
            'title': o.name,
            'item_name': o.name,
            'item_description': o.description,
            'price': float(o.price) if o.price is not None else 0,
            'photo_url': _absolute_photo_url(request, o.photo),
            'subtitle': None,
            'start_date': (o.start_date or today).isoformat(),
            'end_date': (o.end_date or far_future).isoformat(),
            'is_active': o.is_active,
        })
    return Response(result)


# ─── Instructions ───

@api_view(['GET'])
def property_instructions(request, pk):
    booking, error = _get_booking_from_request(request)
    if error:
        return error
    if booking.property_id != pk:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    from ..models import Instruction
    instructions = Instruction.objects.filter(
        property_id=pk,
    ).prefetch_related('images').order_by('order')
    return Response(
        InstructionSerializer(instructions, many=True, context={'request': request}).data
    )


# ─── Orders ───

@api_view(['GET', 'POST'])
def booking_orders(request, pk):
    booking, error = _get_booking_from_request(request)
    if error:
        return error
    if booking.id != pk:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        orders = Order.objects.filter(booking=booking).prefetch_related('items')
        return Response(OrderSerializer(orders, many=True).data)

    # POST — create order from cart items (OwnerOffering ids)
    serializer = OrderCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    order = Order.objects.create(
        booking=booking,
        notes=serializer.validated_data.get('notes', ''),
    )
    for item_data in serializer.validated_data['items']:
        offering_id = item_data.get('service_item_id') or item_data.get('offering_id')
        try:
            offering = OwnerOffering.objects.get(id=offering_id)
        except OwnerOffering.DoesNotExist:
            continue
        # Verify the offering is actually linked to this booking's property,
        # so a guest can't order an item from another property.
        if not offering.properties.filter(id=booking.property_id).exists():
            continue
        unit_price = offering.price or 0
        qty = int(item_data.get('quantity', 1))
        OrderItem.objects.create(
            order=order,
            service_item=None,
            name=offering.name,
            quantity=qty,
            unit_price=unit_price,
            subtotal=unit_price * qty,
        )
    return Response(
        OrderSerializer(order).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(['POST'])
def cancel_order(request, pk):
    """Cancel a pending order."""
    booking, error = _get_booking_from_request(request)
    if error:
        return error
    try:
        order = Order.objects.get(pk=pk, booking=booking)
    except Order.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    if order.status != 'pending':
        return Response(
            {'error': 'Only pending orders can be cancelled.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    order.status = 'cancelled'
    order.save(update_fields=['status', 'updated_at'])
    return Response(OrderSerializer(order).data)


# ─── Documents ───

@api_view(['GET', 'POST'])
def booking_documents(request, pk):
    booking, error = _get_booking_from_request(request)
    if error:
        return error
    if booking.id != pk:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        docs = GuestDocument.objects.filter(booking=booking)
        return Response(GuestDocumentSerializer(docs, many=True).data)

    # POST — upload document
    serializer = GuestDocumentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(booking=booking)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


# ─── Chat ───

@api_view(['GET', 'POST'])
def booking_chat(request, pk):
    booking, error = _get_booking_from_request(request)
    if error:
        return error
    if booking.id != pk:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    conversation, _ = ChatConversation.objects.get_or_create(booking=booking)

    if request.method == 'GET':
        return Response(
            ChatConversationSerializer(conversation).data
        )

    # POST — send message
    content = request.data.get('content', '')
    sender_type = request.data.get('sender_type', 'guest')
    if not content:
        return Response(
            {'error': 'Message content is required'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    message = ChatMessage.objects.create(
        conversation=conversation,
        sender_type=sender_type,
        content=content,
    )
    return Response(
        ChatMessageSerializer(message).data,
        status=status.HTTP_201_CREATED,
    )


# ─── Notifications ───

@api_view(['GET'])
def booking_notifications(request, pk):
    booking, error = _get_booking_from_request(request)
    if error:
        return error
    if booking.id != pk:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    notifications = PushNotification.objects.filter(
        property=booking.property,
        is_sent=True,
        target_booking__isnull=True,
    ) | PushNotification.objects.filter(
        target_booking=booking,
        is_sent=True,
    )
    notifications = notifications.order_by('-sent_at')
    return Response(
        NotificationSerializer(notifications, many=True).data
    )
