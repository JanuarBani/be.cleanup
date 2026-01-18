from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.signals import user_logged_in


from .utils.notifications import NotificationService

User = get_user_model()


@receiver(post_save, sender=User)
def notify_admin_new_member(sender, instance, created, **kwargs):
    """
    ADMIN:
    - Anggota baru mendaftar
    """
    if not created:
        return

    if getattr(instance, "role", None) != "anggota":
        return

    transaction.on_commit(
        lambda: NotificationService.notify_admin(
            title="👤 Anggota Baru Terdaftar",
            body=f"Anggota baru: {instance.get_full_name() or instance.username}",
            notification_type="member_new",
            url="/admin/anggota/",
            data={"user_id": instance.pk},
        )
    )


@receiver(user_logged_in)
def welcome_new_member_on_first_login(sender, request, user, **kwargs):
    """
    KIRIM NOTIFIKASI SAAT LOGIN PERTAMA (ANGGOTA)
    TANPA UBAH MODEL
    """

    # Hanya role anggota
    if getattr(user, "role", None) != "anggota":
        return

    # Cegah terkirim lebih dari sekali (pakai session)
    if request.session.get("welcome_notif_sent"):
        return

    transaction.on_commit(
        lambda: NotificationService.send_notification_to_user(
            user=user,
            title="🎉 Selamat Datang di CleanUp!",
            body=(
                "Terima kasih telah login sebagai anggota. "
                "Silakan lengkapi data anggota dan lakukan pembayaran pertama."
            ),
            notification_type="welcome_member",
            url="/dashboard",
            data={
                "user_id": user.pk,
                "welcome_date": timezone.now().isoformat(),
                "next_step": "complete_profile"
            },
        )
    )

    # Tandai di session (bukan di model)
    request.session["welcome_notif_sent"] = True


@receiver(post_save, sender=User)
def notify_anggota_upgraded(sender, instance, created, **kwargs):
    """
    TAMU yang UPGRADE menjadi ANGGOTA:
    - Mendapat notifikasi konfirmasi upgrade
    """
    # Cek jika role berubah dari 'tamu' ke 'anggota'
    if not created and instance.role == "anggota":
        try:
            # Ambil data lama dari database
            old_instance = User.objects.get(pk=instance.pk)
            
            # Jika sebelumnya bukan anggota, sekarang menjadi anggota
            if old_instance.role != "anggota" and instance.role == "anggota":
                transaction.on_commit(
                    lambda: NotificationService.send_notification_to_user(
                        user=instance,
                        title="✅ Upgrade Berhasil!",
                        body="Selamat! Anda sekarang adalah anggota CleanUp. Nikmati layanan angkut sampah reguler.",
                        notification_type="upgrade_success",
                        url="/dashboard",
                        data={
                            "user_id": instance.pk,
                            "upgrade_date": timezone.now().isoformat(),
                            "new_role": "anggota"
                        },
                    )
                )
        except User.DoesNotExist:
            pass
