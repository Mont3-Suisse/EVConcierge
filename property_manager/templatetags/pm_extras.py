"""Custom template tags for the property_manager app."""

from django import template

register = template.Library()


@register.filter
def status_badge_class(status):
    """Return CSS class for a status value."""
    mapping = {
        "pending": "badge-pending",
        "confirmed": "badge-confirmed",
        "fulfilled": "badge-fulfilled",
        "declined": "badge-declined",
    }
    return mapping.get(status, "badge-draft")


@register.filter
def initials(name):
    """Return initials from a full name."""
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    elif parts:
        return parts[0][0].upper()
    return "?"


@register.filter
def euro(value):
    """Format a value as euros."""
    try:
        return f"€{value:,.2f}"
    except (ValueError, TypeError):
        return f"€{value}"
