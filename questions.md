# Questions for EVConcierge Implementation

## 1. App Name Typo
You wrote `propert_manager` — should it be **`property_manager`** (with the "y")?  
I'll proceed with `property_manager` unless you say otherwise.

## 2. Dashboard Approach
The requirements describe a full "Property Manager Webapp". I'm planning to build:
- **Django models** for the complete data layer
- **Custom Django template-based dashboard views** (a real polished webapp, not just raw Django admin)
- **Django Admin** as a secondary/power-user interface

Should I go with this approach, or would you prefer:
- A) Django Admin only (quickest, but less polished)
- B) A separate frontend (React/Next.js — more work, but more flexible)
- C) Custom Django dashboard ← **my recommendation, the middle ground**

## 3. Authentication
Should I use **Django's built-in authentication** for property managers (username/password, sessions)?  
Or do you plan to integrate an external auth provider (OAuth, Supabase Auth, etc.) later?

## 4. Chat & Push Notifications — Backend Only?
The requirements mention:
- **AI Chat** with escalation to WhatsApp/Telegram
- **Push Notifications** via FCM

For this initial Django build, should I:
- A) Create the **models + admin/dashboard UI** for managing these (compose, schedule, view history) — but **without** actual integrations to Telegram/WhatsApp/FCM
- B) Also build the actual integrations now (requires API keys, external service setup)

**I recommend option A** — get the data layer and management UI right first, add integrations later.

## 5. Media Storage
Property photos, guest documents, and service item images need file uploads.  
For now I'll use Django's local `MEDIA_ROOT` for development.  
For production, you'll want S3 or similar — is that fine to defer to later?

## 6. Multi-tenancy
Can a single property manager manage **multiple properties**?  
The requirements suggest yes ("Create & manage properties" — plural).  
I'll build it as multi-property per manager account. Please confirm.
