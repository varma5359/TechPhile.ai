"""Management command: populate_day1_lesson

Safely copies the starter lesson content from ``careers/lessons.py`` into the
Data Analytics Day 1 ``LearningDay`` record **only when each field is still
empty**.  Admin-authored content is never overwritten.

Usage::

    python manage.py populate_day1_lesson

Run this command after applying migration 0004 to give the live database its
starter lesson content.  It is safe to run more than once -- subsequent runs
are no-ops if the fields are already populated.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from careers import lessons
from careers.models import LearningDay, LEVEL_BEGINNER


class Command(BaseCommand):
    help = (
        'Populate Data Analytics Day 1 lesson fields from careers/lessons.py, '
        'leaving any field that already contains text untouched.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without writing to the database.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options['dry_run']

        try:
            day = LearningDay.objects.select_related('role').get(
                role__title=lessons.ROLE_TITLE,
                level=LEVEL_BEGINNER,
                day_number=lessons.DAY_NUMBER,
            )
        except LearningDay.DoesNotExist:
            raise CommandError(
                'No LearningDay found for role "%s" day %d. Run seed_careers first.'
                % (lessons.ROLE_TITLE, lessons.DAY_NUMBER)
            )

        # Objectives are handled separately because they have a special
        # "is this still the original seed value?" check.
        from careers.management.commands.seed_careers import ORIGINAL_DAY1_OBJECTIVES
        changed_objectives = False
        if not day.objectives.strip() or day.objectives == ORIGINAL_DAY1_OBJECTIVES:
            if day.objectives != lessons.OBJECTIVES:
                if not dry_run:
                    day.objectives = lessons.OBJECTIVES
                    day.save(update_fields=['objectives'])
                changed_objectives = True
                self.stdout.write('  objectives -> updated')
        else:
            self.stdout.write('  objectives -> kept (admin-edited)')

        # Lesson fields: only populate when the field is empty.
        changed_fields = []
        for field, value in lessons.DAY_FIELDS.items():
            current = getattr(day, field)
            if current:
                # Field already has content -- skip to avoid overwriting admin work.
                self.stdout.write('  %s -> kept (already has content)' % field)
            else:
                if not dry_run:
                    setattr(day, field, value)
                changed_fields.append(field)
                self.stdout.write('  %s -> populated' % field)

        if changed_fields and not dry_run:
            day.save(update_fields=changed_fields)

        if not changed_fields and not changed_objectives:
            self.stdout.write(self.style.SUCCESS(
                'Nothing to do -- all lesson fields for "%s" Day %d already have content.'
                % (lessons.ROLE_TITLE, lessons.DAY_NUMBER)
            ))
        elif dry_run:
            self.stdout.write(self.style.WARNING(
                'Dry-run mode: no changes were written to the database.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                'Done. Populated %d lesson field(s) for "%s" Day %d.'
                % (len(changed_fields), lessons.ROLE_TITLE, lessons.DAY_NUMBER)
            ))

