from django.core.management.base import BaseCommand
from django.utils.timezone import now
from datetime import timedelta

from apk.models import Anggota
from apk.utils.notifications import NotificationService


class Command(BaseCommand):
    help = "Reminder perpanjangan keanggotaan"

    def handle(self, *args, **kwargs):
        today = now().date()

        targets = Anggota.objects.filter(
            tanggalEnd__in=[
                today,
                today + timedelta(days=3),
                today + timedelta(days=7),
            ]
        )

        for anggota in targets:
            if not anggota.user:
                continue

            NotificationService.send_notification_to_user(
                user=anggota.user,
                title="⏰ Masa Keanggotaan Hampir Berakhir",
                body=f"Keanggotaan Anda berakhir pada {anggota.tanggalEnd}. Silakan perpanjang.",
                notification_type="membership_expired",
                url="/pembayaran/",
                data={"anggota_id": anggota.pk},
            )

        self.stdout.write(self.style.SUCCESS("✅ Reminder terkirim"))
