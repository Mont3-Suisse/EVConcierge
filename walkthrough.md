# EVConcierge — Property Manager Webapp Walkthrough

## What Was Built

A complete Django 6.x project using UV package manager, with a `property_manager` app implementing the full **Property Manager Webapp** requirements from `home-proposals.html`.

## Project Structure

```
EVConcierge/                    # Django project config
├── settings.py                 # Configured: app, media, auth, timezone
├── urls.py                     # Admin + auth + property_manager routes
├── wsgi.py / asgi.py

property_manager/               # The main app
├── models.py                   # 12 models (see below)
├── admin.py                    # Rich admin with inlines & bulk actions
├── forms.py                    # 10 ModelForms + 2 FormSets
├── views.py                    # 20+ views (all @login_required)
├── urls.py                     # Named URL patterns under "pm:" namespace
├── templatetags/pm_extras.py   # Custom filters (status_badge_class, initials, euro)
├── templates/property_manager/
│   ├── base.html               # Layout with sidebar nav
│   ├── auth/login.html
│   ├── dashboard.html
│   ├── properties/{list,form,detail}.html
│   ├── categories/{manage,edit}.html
│   ├── bookings/{list,form,detail}.html
│   ├── orders/{list,detail}.html
│   ├── notifications/{list,form}.html
│   ├── chat/{list,detail}.html
│   └── specials/{list,form}.html
├── static/property_manager/
│   ├── css/style.css           # 700+ lines, premium dark theme
│   └── js/app.js               # Mobile sidebar, alerts, animations
└── migrations/
    └── 0001_initial.py
```

## Data Models (12 total)

| Model | Purpose |
|---|---|
| **Property** | Vacation rental with name, address, house rules, wifi, check-in/out times |
| **PropertyPhoto** | Photos attached to a property |
| **Category** | Service category (Food & Drinks, Experiences, etc.) |
| **ServiceItem** | Individual service/item with name, description, photo, price |
| **Booking** | Guest booking with access dates (A to B), access code |
| **GuestDocument** | ID/passport uploads |
| **Order** | Guest order with status (pending→confirmed→fulfilled/declined) |
| **OrderItem** | Line items within an order |
| **PushNotification** | Notifications with targeting, scheduling, recurring rules |
| **ChatConversation** | Chat thread with escalation flag |
| **ChatMessage** | Individual messages (guest/ai/manager sender types) |
| **Special** | Promoted items featured on guest home screen |

## Features Implemented

All 7 requirements from the "💻 Property Manager Webapp" section:

1. ✅ **Create & manage properties** — full CRUD with photos, house rules, WiFi info
2. ✅ **Configure categories & services** — create/rename/reorder categories, inline service items with prices
3. ✅ **Manage bookings** — guest access dates, UUID access codes, document viewer
4. ✅ **Order management** — view orders, quick-action confirm/decline/fulfill from list view
5. ✅ **Push notifications** — compose, schedule, target (all guests or specific booking), recurring rules
6. ✅ **Chat overview** — view AI conversations, respond to escalated chats, escalation filter
7. ✅ **Specials / promotions** — feature items with date ranges, link to push notifications

## How to Run

```bash
# Install UV if not present
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# Install dependencies & run migrations
uv sync
uv run python manage.py migrate
uv run python manage.py createsuperuser

# Start the dev server
uv run python manage.py runserver

# Login at http://localhost:8000/accounts/login/
# Django admin also available at http://localhost:8000/admin/
```

## Verification Results

| Check | Result |
|---|---|
| `manage.py check` | ✅ 0 issues |
| `makemigrations` | ✅ 13 models created |
| `migrate` | ✅ All applied |
| Login page | ✅ 200 OK, renders correctly |
| Dashboard | ✅ 200 OK, stat cards + tables |
| Properties | ✅ 200 OK, card grid with CTA |
| Bookings | ✅ 200 OK, filter bar + table |
| Orders | ✅ 200 OK, status filters + quick actions |
| Notifications | ✅ 200 OK, compose + scheduling |
| Chat | ✅ 200 OK, escalation filter |
| Specials | ✅ 200 OK, create + manage |
| Admin (`/admin/`) | ✅ 200 OK |

## Technology Stack

- **UV** 0.11.2 — Python package manager
- **Python** 3.12
- **Django** 6.0.3
- **Pillow** 12.1.1 — image handling
- **SQLite** — development database
- **Vanilla CSS** — premium dark theme with Inter font, glassmorphism, micro-animations
