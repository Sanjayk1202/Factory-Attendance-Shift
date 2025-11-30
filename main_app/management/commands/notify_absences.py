from django.core.management.base import BaseCommand
from django.utils import timezone
from main_app.shift_scheduler import AbsenceNotifier

class Command(BaseCommand):
    help = 'Notify managers about absent employees'

    def handle(self, *args, **options):
        today = timezone.now().date()
        AbsenceNotifier.notify_managers_about_absence(today)
        self.stdout.write(
            self.style.SUCCESS(f"Successfully sent absence notifications for {today}")
        )