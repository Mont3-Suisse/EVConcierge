#!/usr/bin/env python
"""
Migrate every Experience row into the new OwnerOffering model, then delete
the Experience rows (cascading to ExperienceImage, PropertyExperience, and
ExperienceTranslation).

Usage:
    uv run python migrate_experiences_to_offerings.py            # dry run
    uv run python migrate_experiences_to_offerings.py --apply    # commit

Mapping (Experience -> OwnerOffering):
    owner, title->name, description, price, is_active,
    created_at, updated_at preserved.
    category -> section via CATEGORY_TO_SECTION below.
    First ExperienceImage (lowest order) -> OwnerOffering.photo (cover).
    Remaining ExperienceImages -> OwnerOfferingImage rows (gallery).
    PropertyExperience rows -> OwnerOffering.properties M2M.

    Image files are not duplicated on disk — the new rows reference the
    existing files under media/experience_images/.

Dropped: ai_summary, duration, address, latitude, longitude,
    manual_geolocalization, group_size, ical_url, booking_method,
    booking_phone, booking_link, referral_code, view_count, is_featured,
    ExperienceTranslation rows.
"""

import argparse
import os
import sys

import django
from django.db import transaction

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "EVConcierge.settings")
django.setup()

from property_manager.models import (  # noqa: E402
    Experience,
    OwnerOffering,
    OwnerOfferingImage,
)


CATEGORY_TO_SECTION = {
    "food": OwnerOffering.SECTION_FOOD_DRINKS,
    "nature": OwnerOffering.SECTION_DISCOVER,
    "experiences": OwnerOffering.SECTION_EXPERIENCES,
    "services": OwnerOffering.SECTION_ADDONS,
}


def migrate(apply: bool) -> int:
    created = 0
    skipped = 0
    total = Experience.objects.count()
    print(f"Found {total} Experience row(s) to migrate.")

    with transaction.atomic():
        for exp in Experience.objects.all().order_by("id"):
            section = CATEGORY_TO_SECTION.get(exp.category)
            if section is None:
                print(f"  SKIP exp#{exp.id} '{exp.title}' — unknown category '{exp.category}'")
                skipped += 1
                continue

            offering = OwnerOffering(
                owner=exp.owner,
                section=section,
                name=exp.title,
                description=exp.description or "",
                price=exp.price,
                is_active=exp.is_active,
            )

            source_images = list(exp.images.order_by("order", "id"))
            if source_images and source_images[0].image:
                offering.photo.name = source_images[0].image.name

            offering.save()

            OwnerOffering.objects.filter(pk=offering.pk).update(
                created_at=exp.created_at,
                updated_at=exp.updated_at,
            )

            property_ids = list(
                exp.property_experiences.values_list("property_id", flat=True)
            )
            if property_ids:
                offering.properties.set(property_ids)

            extras = 0
            for idx, src_img in enumerate(source_images[1:], start=1):
                if not src_img.image:
                    continue
                gallery = OwnerOfferingImage(
                    offering=offering,
                    caption=src_img.caption or "",
                    order=src_img.order or idx,
                )
                gallery.image.name = src_img.image.name
                gallery.save()
                extras += 1

            print(
                f"  OK   exp#{exp.id} '{exp.title}' -> offering#{offering.pk} "
                f"[{section}] (props: {len(property_ids)}, "
                f"cover: {'yes' if source_images else 'no'}, "
                f"extra images: {extras})"
            )
            created += 1

        deleted, _ = Experience.objects.all().delete()
        print(f"\nDeleting Experience rows (and cascaded children): {deleted} object(s).")

        if not apply:
            print("\nDRY RUN — rolling back. Re-run with --apply to commit.")
            transaction.set_rollback(True)

    print(f"\nSummary: created={created}, skipped={skipped}, total={total}")
    return 0 if skipped == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually commit the migration. Without this flag the script runs as a dry-run.",
    )
    args = parser.parse_args()
    return migrate(apply=args.apply)


if __name__ == "__main__":
    sys.exit(main())
