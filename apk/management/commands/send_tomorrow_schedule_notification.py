from django.core.management.base import BaseCommand
from apk.utils.notifications import NotificationService


class Command(BaseCommand):
    help = "Kirim notifikasi jadwal pengangkutan BESOK ke Tim Angkut"

    def handle(self, *args, **options):
        self.stdout.write("🔔 Mengirim notifikasi jadwal besok ke Tim Angkut...")
        
        try:
            # Panggil fungsi yang SUDAH BENAR
            results = NotificationService.notify_team_tomorrow_schedule()
            
            # Log hasil
            if results:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Notifikasi jadwal besok berhasil dikirim"
                    )
                )
                self.stdout.write(f"📊 Detail: {len(results)} push notifications terkirim")
            else:
                self.stdout.write("ℹ Tidak ada notifikasi yang perlu dikirim")
                
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(
                    f"❌ Gagal mengirim notifikasi: {e}"
                )
            )
