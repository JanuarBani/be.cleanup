from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.db import transaction
import logging

from .models import Pembayaran, DetailAnggotaJadwal, LaporanSampah
from .utils.notifications import NotificationService

logger = logging.getLogger(__name__)


# =====================================================
# PEMBAYARAN
# =====================================================

@receiver(pre_save, sender=Pembayaran)
def cache_old_payment_status(sender, instance, **kwargs):
    """
    Simpan status lama sebelum update pembayaran
    """
    if not instance.pk:
        return

    try:
        instance._old_status_bayar = (
            Pembayaran.objects
            .only("statusBayar")
            .get(pk=instance.pk)
            .statusBayar
        )
    except Pembayaran.DoesNotExist:
        instance._old_status_bayar = None


@receiver(post_save, sender=Pembayaran)
def payment_notifications(sender, instance, created, **kwargs):
    """
    Notifikasi pembayaran:
    - ADMIN: pembayaran baru (pending)
    - ADMIN + ANGGOTA: status pembayaran berubah
    """

    # 🆕 Pembayaran baru (ADMIN)
    if created:
        if instance.statusBayar == "pending":
            transaction.on_commit(
                lambda: NotificationService.notify_admin_payment_pending(instance)
            )
        return

    # 🔄 Status berubah
    old_status = getattr(instance, "_old_status_bayar", None)
    if old_status == instance.statusBayar:
        return

    transaction.on_commit(
        lambda: NotificationService.send_payment_status_update(instance)
    )


# =====================================================
# DETAIL JADWAL / PENGANGKUTAN
# =====================================================

@receiver(pre_save, sender=DetailAnggotaJadwal)
def cache_old_pickup_status(sender, instance, **kwargs):
    """
    Simpan status pengangkutan lama sebelum update
    """
    if not instance.pk:
        return

    try:
        instance._old_status_pengangkutan = (
            DetailAnggotaJadwal.objects
            .only("status_pengangkutan")
            .get(pk=instance.pk)
            .status_pengangkutan
        )
    except DetailAnggotaJadwal.DoesNotExist:
        instance._old_status_pengangkutan = None


@receiver(post_save, sender=DetailAnggotaJadwal)
def pickup_notifications(sender, instance, created, **kwargs):
    """
    Notifikasi jadwal & pengangkutan:
    - ADMIN: detail jadwal baru dibuat
    - ADMIN + ANGGOTA: status pengangkutan berubah
    """

    # 🆕 Detail jadwal baru (ADMIN)
    if created:
        transaction.on_commit(
            lambda: NotificationService.notify_admin_new_schedule(instance)
        )
        return

    old_status = getattr(instance, "_old_status_pengangkutan", None)
    new_status = instance.status_pengangkutan

    logger.info(
        "🚨 PICKUP SIGNAL | OLD=%s NEW=%s ID=%s",
        old_status, new_status, instance.pk
    )

    if old_status == new_status:
        return

    transaction.on_commit(
        lambda: NotificationService.send_pickup_status_update(instance)
    )

# =====================================================
# LAPORAN SAMPAH
# =====================================================

@receiver(pre_save, sender=LaporanSampah)
def cache_old_laporan_status(sender, instance, **kwargs):
    """
    Simpan status laporan lama sebelum update
    """
    if not instance.pk:
        return

    try:
        instance._old_status = (
            LaporanSampah.objects
            .only("status")
            .get(pk=instance.pk)
            .status
        )
    except LaporanSampah.DoesNotExist:
        instance._old_status = None


@receiver(post_save, sender=LaporanSampah)
def laporan_notifications(sender, instance, created, **kwargs):
    """
    Notifikasi laporan sampah:
    - TAMU: laporan baru dibuat
    - TAMU: status laporan berubah
    - ADMIN: laporan baru (pending)
    """
    
    logger.info(f"🗑️ Laporan notification signal for laporan {instance.idLaporan}")
    logger.info(f"   Created: {created}")
    logger.info(f"   Status: {instance.status}")
    logger.info(f"   User: {instance.idUser.username if instance.idUser else 'Anonymous'}")
    
    # 🆕 Laporan baru dibuat
    if created:
        logger.info("📝 New laporan created")
        
        # 1. Notify TAMU that their report was received
        if instance.idUser and instance.idUser.role in ['tamu', 'anggota']:
            logger.info(f"   Notifying user {instance.idUser.username} about new laporan")
            transaction.on_commit(
                lambda: NotificationService.notify_pelapor_laporan_diterima(instance)
            )
        
        # 2. Notify ADMIN about new laporan (pending)
        if instance.status == 'pending':
            logger.info("   Notifying admins about new pending laporan")
            transaction.on_commit(
                lambda: NotificationService.notify_admin_laporan_baru(instance)
            )
        return
    
    # 🔄 Status berubah
    old_status = getattr(instance, "_old_status", None)
    
    if old_status == instance.status:
        logger.info("   ⏩ Status unchanged, skipping")
        return
    
    logger.info(f"   🔄 Status changed from {old_status} to {instance.status}")
    
    # 1. Notify TAMU about status change
    if instance.idUser and instance.idUser.role in ['tamu', 'anggota']:
        logger.info(f"   Notifying user {instance.idUser.username} about status change")
        transaction.on_commit(
            lambda: NotificationService.notify_pelapor_status_berubah(instance)
        )
    
    # 2. Notify ADMIN if status changed to "selesai"
    if instance.status == 'selesai':
        logger.info("   Notifying admins about completed laporan")
        transaction.on_commit(
            lambda: NotificationService.notify_admin_laporan_selesai(instance)
        )
# =====================================================
# TIM ANGKUT - JADWAL BARU
# =====================================================

@receiver(post_save, sender=DetailAnggotaJadwal)
def notify_team_on_new_schedule(sender, instance, created, **kwargs):
    """
    TIM ANGKUT:
    - Jadwal baru dibuat
    """
    if not created:
        return

    transaction.on_commit(
        lambda: NotificationService.notify_team_new_schedule(instance)
    )

# from django.db.models.signals import pre_save, post_save
# from django.dispatch import receiver
# from django.db import transaction
# import logging

# from .models import Pembayaran, DetailAnggotaJadwal, LaporanSampah
# from .utils.notifications import NotificationService

# logger = logging.getLogger(__name__)


# # =====================================================
# # PEMBAYARAN
# # =====================================================

# @receiver(pre_save, sender=Pembayaran)
# def cache_old_payment_status(sender, instance, **kwargs):
#     """
#     Simpan status lama sebelum update pembayaran
#     """
#     if not instance.pk:
#         return

#     try:
#         instance._old_status_bayar = (
#             Pembayaran.objects
#             .only("statusBayar")
#             .get(pk=instance.pk)
#             .statusBayar
#         )
#     except Pembayaran.DoesNotExist:
#         instance._old_status_bayar = None


# @receiver(post_save, sender=Pembayaran)
# def payment_notifications(sender, instance, created, **kwargs):
#     """
#     Notifikasi pembayaran:
#     - ADMIN: pembayaran baru (pending)
#     - ADMIN + ANGGOTA: status pembayaran berubah
#     """

#     # 🆕 Pembayaran baru (ADMIN)
#     if created:
#         if instance.statusBayar == "pending":
#             transaction.on_commit(
#                 lambda: NotificationService.notify_admin_payment_pending(instance)
#             )
#         return

#     # 🔄 Status berubah
#     old_status = getattr(instance, "_old_status_bayar", None)
#     if old_status == instance.statusBayar:
#         return

#     transaction.on_commit(
#         lambda: NotificationService.send_payment_status_update(instance)
#     )


# # =====================================================
# # DETAIL JADWAL / PENGANGKUTAN
# # =====================================================

# @receiver(pre_save, sender=DetailAnggotaJadwal)
# def cache_old_pickup_status(sender, instance, **kwargs):
#     """
#     Simpan status pengangkutan lama sebelum update
#     """
#     if not instance.pk:
#         return

#     try:
#         instance._old_status_pengangkutan = (
#             DetailAnggotaJadwal.objects
#             .only("status_pengangkutan")
#             .get(pk=instance.pk)
#             .status_pengangkutan
#         )
#     except DetailAnggotaJadwal.DoesNotExist:
#         instance._old_status_pengangkutan = None


# @receiver(post_save, sender=DetailAnggotaJadwal)
# def pickup_notifications(sender, instance, created, **kwargs):
#     """
#     Notifikasi jadwal & pengangkutan:
#     - ADMIN: detail jadwal baru dibuat
#     - ADMIN + ANGGOTA: status pengangkutan berubah
#     """

#     # 🆕 Detail jadwal baru (ADMIN)
#     if created:
#         transaction.on_commit(
#             lambda: NotificationService.notify_admin_new_schedule(instance)
#         )
#         return

#     old_status = getattr(instance, "_old_status_pengangkutan", None)
#     new_status = instance.status_pengangkutan

#     logger.info(
#         "🚨 PICKUP SIGNAL | OLD=%s NEW=%s ID=%s",
#         old_status, new_status, instance.pk
#     )

#     if old_status == new_status:
#         return

#     transaction.on_commit(
#         lambda: NotificationService.send_pickup_status_update(instance)
#     )

# # TAMU – Status Laporan Sampah Berubah
# @receiver(pre_save, sender=LaporanSampah)
# def cache_old_laporan_status(sender, instance, **kwargs):
#     if not instance.pk:
#         return

#     try:
#         instance._old_status = (
#             LaporanSampah.objects
#             .only("status")
#             .get(pk=instance.pk)
#             .status
#         )
#     except LaporanSampah.DoesNotExist:
#         instance._old_status = None


# @receiver(post_save, sender=LaporanSampah)
# def laporan_status_notification(sender, instance, created, **kwargs):
#     """
#     TAMU / PELAPOR:
#     - Status laporan berubah
#     """
#     if created:
#         return

#     old_status = getattr(instance, "_old_status", None)
#     if old_status == instance.status:
#         return

#     transaction.on_commit(
#         lambda: NotificationService.send_laporan_status_update(instance)
#     )

# # TIM ANGKUT – Jadwal Baru Dibuat
# @receiver(post_save, sender=DetailAnggotaJadwal)
# def notify_team_on_new_schedule(sender, instance, created, **kwargs):
#     """
#     TIM ANGKUT:
#     - Jadwal baru dibuat
#     """
#     if not created:
#         return

#     transaction.on_commit(
#         lambda: NotificationService.notify_team_new_schedule(instance)
#     )
