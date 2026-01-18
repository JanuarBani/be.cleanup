# utils/notifications.py
import json
import logging
from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from pywebpush import webpush, WebPushException
from django.utils import timezone
from datetime import timedelta

from ..models import PushSubscription, Notification, LaporanSampah, TimPengangkut

logger = logging.getLogger(__name__)
User = get_user_model()


class NotificationService:
    """
    Centralized Web Push Notification Service
    """

    # =====================================================
    # CORE SENDER
    # =====================================================

    @staticmethod
    def send_notification_to_user(
        user,
        title,
        body,
        notification_type="general",
        url="/",
        data=None,
        create_db_notification=True,
    ):
        """
        Kirim push notification ke SATU user
        """
        # ✅ SIMPAN KE DATABASE NOTIFICATION DENGAN URL
        if create_db_notification:
            try:
                Notification.objects.create(
                    user=user,
                    title=title,
                    message=body,
                    notification_type=notification_type,
                    priority="high" if notification_type in ["payment_new", "laporan_new", "alert"] else "normal",
                    url=url,  # ✅ TAMBAHKAN URL DI SINI
                    data=data or {},
                    read=False
                )
                logger.info(f"📝 Database notification created for {user.username} with URL: {url}")
            except Exception as e:
                logger.error(f"❌ Failed to create database notification: {e}")
        
        subscriptions = PushSubscription.objects.filter(user=user)

        if not subscriptions.exists():
            logger.warning("❌ No subscription for user %s", user.username)
            return []

        payload = {
            "title": title,
            "body": body,
            "icon": "/icons/icon-192x192.png",
            "url": url,
            "type": notification_type,
            "data": data or {},
        }

        results = []

        for subscription in subscriptions:
            try:
                webpush(
                    subscription_info=subscription.to_dict(),
                    data=json.dumps(payload),
                    vapid_private_key=settings.WEBPUSH_SETTINGS["VAPID_PRIVATE_KEY"],
                    vapid_claims={
                        "sub": f"mailto:{settings.WEBPUSH_SETTINGS['VAPID_ADMIN_EMAIL']}"
                    },
                )

                results.append({
                    "status": "success",
                    "endpoint": subscription.endpoint,
                })

                logger.info("✅ Notification sent to %s with URL: %s", user.username, url)

            except WebPushException as ex:
                # Subscription expired / gone
                if ex.response and ex.response.status_code in (404, 410):
                    subscription.delete()
                    logger.warning("🧹 Deleted expired subscription for %s", user.username)

                logger.error("❌ WebPush error (%s): %s", user.username, ex)
                results.append({"status": "failed", "error": str(ex)})

            except Exception as e:
                logger.exception("❌ Unknown push error: %s", e)

        return results

    # =====================================================
    # ADMIN HELPERS
    # =====================================================

    @staticmethod
    def _get_admin_users():
        """
        Ambil semua user dengan role='admin' DAN/ATAU is_staff=True
        """
        admin_users = User.objects.filter(
            models.Q(role='admin') | models.Q(is_staff=True),
            is_active=True
        ).distinct()
        
        return admin_users
    
    @staticmethod
    def _get_admin_users_with_push():
        """
        Ambil admin users YANG MEMILIKI PUSH SUBSCRIPTION
        """
        all_admins = User.objects.filter(
            models.Q(role='admin') | models.Q(is_staff=True),
            is_active=True
        ).distinct()
        
        admin_ids_with_push = PushSubscription.objects.filter(
            user__in=all_admins
        ).values_list('user_id', flat=True).distinct()
        
        return User.objects.filter(id__in=admin_ids_with_push)

    @staticmethod
    def notify_admin(
        title,
        body,
        notification_type="admin",
        url="http://localhost:5173/#/dashboard",
        data=None,
    ):
        """
        Notifikasi ke SEMUA USER DENGAN ROLE='admin'
        """
        from django.db import models
        from ..models import Notification
        
        # 1. Database notification untuk SEMUA admin DENGAN URL
        all_admins = User.objects.filter(
            models.Q(role='admin') | models.Q(is_staff=True),
            is_active=True
        ).distinct()
        
        logger.info(f"👮 Found {all_admins.count()} admin users")
        
        db_notifications = []
        
        for admin in all_admins:
            notification = Notification.objects.create(
                user=admin,
                title=title,
                message=body,
                notification_type=notification_type,
                priority="high" if notification_type in ["payment_new", "laporan_new"] else "normal",
                url=url,  # ✅ TAMBAHKAN URL DI SINI
                data=data or {},
                read=False
            )
            db_notifications.append(notification.id)
        
        # 2. Push notification HANYA untuk admin dengan subscription
        admins_with_push = NotificationService._get_admin_users_with_push()
        logger.info(f"📱 Admins with push subscription: {admins_with_push.count()}")
        
        push_results = []
        
        for admin in admins_with_push:
            results = NotificationService.send_notification_to_user(
                user=admin,
                title=title,
                body=body,
                notification_type=notification_type,
                url=url,
                data=data,
                create_db_notification=False
            )
            push_results.extend(results)
        
        return {
            "database_notifications": db_notifications,
            "push_notifications": push_results,
            "total_admins": all_admins.count(),
            "admins_with_push": admins_with_push.count(),
        }

    # =====================================================
    # PAYMENT NOTIFICATIONS
    # =====================================================

    @staticmethod
    def send_payment_status_update(pembayaran):
        """
        Notifikasi ke ANGGOTA saat status pembayaran berubah
        """
        anggota = pembayaran.idAnggota
        user = anggota.user

        status_map = {
            "pending": "menunggu konfirmasi",
            "lunas": "telah dikonfirmasi",
            "gagal": "ditolak",
        }

        title = "💳 Status Pembayaran Diperbarui"
        body = (
            f"Pembayaran Rp {pembayaran.jumlahBayar:,} "
            f"{status_map.get(pembayaran.statusBayar, '')}"
        )

        return NotificationService.send_notification_to_user(
            user=user,
            title=title,
            body=body,
            notification_type="payment_update",
            url=f"http://localhost:5173/#/dashboard",  # ✅ URL untuk pembayaran spesifik
            data={
                "pembayaran_id": pembayaran.pk,
                "status": pembayaran.statusBayar,
                "amount": pembayaran.jumlahBayar,
            },
        )

    @staticmethod
    def notify_admin_payment_pending(pembayaran):
        """
        Notifikasi ADMIN saat ada pembayaran baru (pending)
        """
        title = "💰 Pembayaran Baru"
        body = (
            f"Anggota {pembayaran.idAnggota.nama} "
            f"mengirim pembayaran Rp {pembayaran.jumlahBayar:,}"
        )

        return NotificationService.notify_admin(
            title=title,
            body=body,
            notification_type="payment_new",
            url="http://localhost:5173/#/dashboard",
            data={"pembayaran_id": pembayaran.pk},
        )

    # =====================================================
    # PICKUP / JADWAL
    # =====================================================

    @staticmethod
    def send_pickup_status_update(detail_jadwal):
        """
        Notifikasi ke ANGGOTA saat status pengangkutan berubah
        """
        anggota = detail_jadwal.idAnggota
        user = anggota.user
        jadwal = detail_jadwal.idJadwal

        status_map = {
            "terjadwal": "Terjadwal",
            "dalam_proses": "Sedang diproses",
            "selesai": "Telah selesai",
            "dibatalkan": "Dibatalkan",
        }

        title = "🚛 Status Pengangkutan Diperbarui"
        body = (
            f"Pengangkutan pada {jadwal.tanggalJadwal} "
            f"{status_map.get(detail_jadwal.status_pengangkutan)}"
        )

        if detail_jadwal.catatan:
            body += f"\n📝 {detail_jadwal.catatan}"

        return NotificationService.send_notification_to_user(
            user=user,
            title=title,
            body=body,
            notification_type="pickup_update",
            url="http://localhost:5173/#/dashboard",  # ✅ URL untuk jadwal spesifik
            data={
                "jadwal_id": jadwal.pk,
                "status": detail_jadwal.status_pengangkutan,
            },
        )

    @staticmethod
    def notify_admin_new_schedule(detail_jadwal):
        """
        Notifikasi ADMIN saat detail jadwal baru dibuat
        """
        title = "📅 Jadwal Pengangkutan Baru"
        body = (
            f"Jadwal baru untuk anggota "
            f"{detail_jadwal.idAnggota.nama} "
            f"pada {detail_jadwal.idJadwal.tanggalJadwal}"
        )

        return NotificationService.notify_admin(
            title=title,
            body=body,
            notification_type="schedule_new",
            url="http://localhost:5173/#/dashboard",
            data={"jadwal_id": detail_jadwal.idJadwal.pk},
        )
    
    #=====================================================
    # LAPORAN SAMPAH NOTIFICATIONS
    # =====================================================

    @staticmethod
    def notify_pelapor_laporan_diterima(laporan):
        """
        Kirim notifikasi ke PELAPOR (tamu/anggota) saat laporan baru dibuat
        """
        if not laporan.idUser:
            logger.warning(f"❌ Laporan {laporan.idLaporan} tidak memiliki user terkait")
            return []
        
        user = laporan.idUser
        
        title = "✅ Laporan Sampah Diterima"
        body = f"Laporan sampah Anda di {laporan.alamat[:50] if laporan.alamat else 'lokasi tersebut'} telah diterima"
        
        if laporan.deskripsi:
            body += f": {laporan.deskripsi[:50]}..."
        
        logger.info(f"📝 Memberi notifikasi ke {user.username} tentang laporan baru")
        
        return NotificationService.send_notification_to_user(
            user=user,
            title=title,
            body=body,
            notification_type='laporan_new',
            url=f"http://localhost:5173/#/dashboard",  # ✅ URL untuk laporan spesifik
            data={
                'laporan_id': laporan.idLaporan,
                'status': 'pending',
                'alamat': laporan.alamat,
                'timestamp': timezone.now().isoformat()
            }
        )

    @staticmethod
    def notify_pelapor_status_berubah(laporan, old_status=None):
        """
        Kirim notifikasi ke PELAPOR saat status laporan berubah
        """
        if not laporan.idUser:
            logger.warning(f"❌ Laporan {laporan.idLaporan} tidak memiliki user terkait")
            return []
        
        user = laporan.idUser
        
        # Mapping status untuk teks yang lebih ramah
        status_map = {
            "pending": "menunggu",
            "proses": "sedang diproses",
            "selesai": "telah selesai",
            "diproses": "sedang diproses",
            "ditolak": "ditolak"
        }
        
        status_text = status_map.get(laporan.status, laporan.status)
        
        title = "📢 Status Laporan Diperbarui"
        body = f"Laporan sampah Anda sekarang berstatus: {status_text}"
        
        # Tambahkan alamat jika ada
        if laporan.alamat:
            body += f"\n📍 {laporan.alamat[:100]}"
        
        # PERBAIKAN: Hapus atau modifikasi bagian catatan_admin
        # Opsi 1: Hapus bagian catatan_admin
        # Opsi 2: Gunakan try-except
        try:
            # Coba akses catatan_admin jika ada
            if hasattr(laporan, 'catatan_admin') and laporan.catatan_admin:
                body += f"\n📝 Catatan admin: {laporan.catatan_admin[:100]}..."
        except AttributeError:
            # Jika tidak ada atribut catatan_admin, lewati saja
            pass
        
        logger.info(f"📝 Memberi notifikasi ke {user.username} tentang perubahan status: {old_status} → {laporan.status}")
        
        return NotificationService.send_notification_to_user(
            user=user,
            title=title,
            body=body,
            notification_type='laporan_update',
            url=f"http://localhost:5173/#/dashboard",
            data={
                'laporan_id': laporan.idLaporan,
                'status': laporan.status,
                'status_text': status_text,
                'old_status': old_status,
                'alamat': laporan.alamat,
                'timestamp': timezone.now().isoformat()
            }
        )

    @staticmethod
    def notify_admin_laporan_baru(laporan):
        """
        Notifikasi ADMIN saat ada laporan sampah baru (pending)
        """
        title = "🗑️ Laporan Sampah Baru"
        
        # Get user info safely
        user_info = f"oleh {laporan.idUser.username}" if laporan.idUser else "oleh tamu"
        
        body = (
            f"Laporan sampah baru {user_info} "
            f"di {laporan.alamat[:100] if laporan.alamat else 'lokasi'}"
        )
        
        # Tambahkan deskripsi singkat jika ada
        if laporan.deskripsi:
            body += f"\n📄 {laporan.deskripsi[:80]}..."

        return NotificationService.notify_admin(
            title=title,
            body=body,
            notification_type="laporan_new",
            url=f"http://localhost:5173/#/dashboard",
            data={
                "laporan_id": laporan.idLaporan,
                "user_id": laporan.idUser.id if laporan.idUser else None,
                "username": laporan.idUser.username if laporan.idUser else "Tamu",
                "alamat": laporan.alamat,
                "status": laporan.status
            },
        )

    @staticmethod
    def notify_admin_laporan_selesai(laporan):
        """
        Notifikasi ADMIN saat laporan sampah selesai
        """
        title = "✅ Laporan Sampah Selesai"
        
        user_info = f"oleh {laporan.idUser.username}" if laporan.idUser else "oleh tamu"
        
        body = (
            f"Laporan sampah {user_info} "
            f"telah diselesaikan"
        )
        
        if laporan.alamat:
            body += f"\n📍 {laporan.alamat[:100]}"

        return NotificationService.notify_admin(
            title=title,
            body=body,
            notification_type="laporan_selesai",
            url=f"http://localhost:5173/#/dashboard",
            data={
                "laporan_id": laporan.idLaporan,
                "user_id": laporan.idUser.id if laporan.idUser else None,
                "username": laporan.idUser.username if laporan.idUser else "Tamu",
                "alamat": laporan.alamat,
                "status": laporan.status
            },
        )

    # =====================================================
    # HELPER METHODS UNTUK LAPORAN
    # =====================================================

    @staticmethod
    def get_laporan_status_display(status):
        """
        Helper untuk mendapatkan teks status yang lebih ramah
        """
        status_display = {
            "pending": "Menunggu",
            "diproses": "Sedang Diproses",
            "selesai": "Selesai",
            "ditolak": "Ditolak"
        }
        return status_display.get(status, status)

    @staticmethod
    def send_laporan_status_update(laporan):
        """
        Method kompatibilitas untuk kode lama
        (notify pelapor tentang perubahan status)
        """
        return NotificationService.notify_pelapor_status_berubah(laporan)
    

    # =====================================================
    # TIM ANGKUT NOTIFICATIONS
    # =====================================================

    @staticmethod
    def notify_team_new_schedule(detail_jadwal):
        """
        Notifikasi ke TIM ANGKUT untuk jadwal BESOK (SPESIFIK PER TIM)
        """
        from ..models import DetailAnggotaJadwal

        if not isinstance(detail_jadwal, DetailAnggotaJadwal):
            raise ValueError(
                f"Object is not DetailAnggotaJadwal: {type(detail_jadwal)}"
            )

        jadwal = detail_jadwal.idJadwal
        tim = jadwal.idTim

        if not tim:
            return []

        # 🔑 AMBIL USER TIM ANGKUT UNTUK TIM INI SAJA (SPESIFIK)
        # Cari user yang terkait dengan tim ini MELALUI idUser
        tim_users = User.objects.filter(
            role="tim_angkut",
            is_active=True,
            id=tim.idUser.id  # Ambil user yang terkait langsung dengan tim
        )

        if not tim_users.exists():
            # Jika tidak ada user yang langsung terkait, coba cari berdasarkan nama tim
            tim_users = User.objects.filter(
                role="tim_angkut",
                is_active=True,
                username__icontains=tim.namaTim.lower().replace(" ", "_")
            )
            
            if not tim_users.exists():
                logger.warning(f"⚠ Tidak ditemukan user tim angkut untuk tim: {tim.namaTim}")
                return []

        results = []

        for user in tim_users:
            # Format username untuk pesan yang lebih personal
            display_name = user.username.split('_')[-1] if '_' in user.username else user.username
            
            results.extend(
                NotificationService.send_notification_to_user(
                    user=user,
                    title=f"🚛 Jadwal Baru - {tim.namaTim}",
                    body=(
                        f"Halo {display_name}! "
                        f"Tim {tim.namaTim} memiliki jadwal baru "
                        f"pada {jadwal.tanggalJadwal}"
                    ),
                    notification_type="schedule_new",
                    url=f"http://localhost:5173/#/dashboard",
                    data={
                        "jadwal_id": jadwal.pk,
                        "detail_id": detail_jadwal.pk,
                        "tim": tim.namaTim,
                        "tim_id": tim.idTim,
                        "user_username": user.username
                    },
                )
            )
            
            logger.info(f"✓ Notifikasi dikirim ke {user.username} untuk tim {tim.namaTim}")

        return results

    @staticmethod
    def notify_team_tomorrow_schedule():
        """
        Notifikasi TIM ANGKUT tentang jadwal besok (SPESIFIK PER TIM)
        """
        from ..models import Jadwal, User, Notification, TimPengangkut
        from django.db.models import Count
        
        tomorrow = timezone.now().date() + timedelta(days=1)
        
        # 1. Ambil semua jadwal untuk besok dengan hitung lokasi
        jadwals_tomorrow = (
            Jadwal.objects
            .filter(tanggalJadwal=tomorrow)
            .select_related('idTim')
            .annotate(
                lokasi_count=Count('detailanggotajadwal')
            )
            .filter(lokasi_count__gt=0)
        )
        
        if not jadwals_tomorrow.exists():
            logger.info(f"ℹ Tidak ada jadwal untuk besok ({tomorrow})")
            return []
        
        logger.info(f"📅 {jadwals_tomorrow.count()} jadwal aktif untuk besok")
        
        # 2. Kelompokkan per tim dan hitung total
        tim_summary = {}
        
        for jadwal in jadwals_tomorrow:
            tim = jadwal.idTim
            tim_id = tim.idTim
            
            if tim_id not in tim_summary:
                tim_summary[tim_id] = {
                    'tim': tim,
                    'total_lokasi': 0,
                    'jadwal_ids': []
                }
            
            tim_summary[tim_id]['total_lokasi'] += jadwal.lokasi_count
            tim_summary[tim_id]['jadwal_ids'].append(jadwal.idJadwal)
        
        # 3. Untuk setiap tim, kirim notifikasi hanya ke user tim tersebut
        results = []
        
        for tim_id, tim_data in tim_summary.items():
            tim = tim_data['tim']
            
            # CARI USER UNTUK TIM INI SAJA
            # Cari user yang terkait langsung dengan tim melalui idUser
            if tim.idUser:
                tim_users = User.objects.filter(
                    role='tim_angkut', 
                    is_active=True,
                    id=tim.idUser.id
                )
            else:
                # Jika tim tidak punya idUser, cari berdasarkan nama tim
                tim_name_clean = tim.namaTim.lower().replace(" ", "")
                tim_users = User.objects.filter(
                    role='tim_angkut',
                    is_active=True,
                    username__iregex=f'({tim_name_clean}|tim.*{tim_name_clean}|{tim_name_clean}.*tim)'
                )
            
            if not tim_users.exists():
                logger.warning(f"⚠ Tidak ditemukan user untuk tim: {tim.namaTim}")
                continue
            
            logger.info(f"👥 Ditemukan {tim_users.count()} user untuk tim {tim.namaTim}")
            
            # 4. Format pesan khusus untuk tim ini
            title = f"📋 Jadwal Besok - {tim.namaTim}"
            
            # 5. URL khusus untuk tim ini
            target_url = f"http://localhost:5173/#/dashboard?tim={tim_id}"
            
            # 6. Kirim notifikasi ke setiap user TIM INI SAJA
            for user in tim_users:
                try:
                    # Format username untuk pesan personal
                    display_name = user.username
                    if '_' in user.username:
                        display_name = user.username.split('_')[-1]
                    elif user.username.startswith('tim'):
                        display_name = user.username[3:] if len(user.username) > 3 else user.username
                    
                    personal_body = f"Halo {display_name}! Tim {tim.namaTim} memiliki {tim_data['total_lokasi']} lokasi besok"
                    
                    # Buat notifikasi database DENGAN URL
                    notification = Notification.objects.create(
                        user=user,
                        title=title,
                        message=personal_body,
                        notification_type="schedule_reminder",
                        priority="high",
                        url=target_url,
                        data={
                            'tim_id': tim_id,
                            'tim_nama': tim.namaTim,
                            'total_lokasi': tim_data['total_lokasi'],
                            'jadwal_ids': tim_data['jadwal_ids'],
                            'date': tomorrow.isoformat(),
                            'user_username': user.username,
                            'user_id': user.id
                        }
                    )
                    logger.debug(f"✓ Database notification created for {user.username} (tim: {tim.namaTim})")
                    
                    # 7. Kirim PUSH NOTIFICATION yang bisa diklik
                    try:
                        push_results = NotificationService.send_notification_to_user(
                            user=user,
                            title=title,
                            body=personal_body,
                            notification_type="schedule_reminder",
                            url=target_url,
                            data={
                                'action': 'open_url',
                                'url': target_url,
                                'notification_id': notification.id,
                                'date': tomorrow.isoformat(),
                                'click_action': target_url,
                                'tim_id': tim_id,
                                'tim_nama': tim.namaTim,
                                'user_specific': True
                            },
                            create_db_notification=False
                        )
                        
                        if push_results:
                            results.extend(push_results)
                            logger.debug(f"✓ Push notification sent to {user.username} untuk tim {tim.namaTim}")
                        
                    except Exception as push_error:
                        # Handle push errors
                        error_msg = str(push_error)
                        if "410 Gone" in error_msg:
                            from ..models import PushSubscription
                            PushSubscription.objects.filter(user=user).delete()
                            logger.info(f"🗑️ Subscription expired dihapus untuk {user.username}")
                        else:
                            logger.error(f"❌ Push error untuk {user.username} (tim: {tim.namaTim}): {push_error}")
                    
                except Exception as e:
                    logger.error(f"❌ Error untuk {user.username} (tim: {tim.namaTim}): {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            
            logger.info(f"✓ Notifikasi untuk tim {tim.namaTim} selesai: {tim_users.count()} user")
        
        # 8. Notifikasi untuk admin (opsional)
        if results:
            # Kirim notifikasi ringkasan ke admin
            admin_users = User.objects.filter(
                role='admin',
                is_active=True
            )
            
            if admin_users.exists():
                total_all_lokasi = sum(data['total_lokasi'] for data in tim_summary.values())
                tim_list = ", ".join([f"{data['tim'].namaTim} ({data['total_lokasi']})" 
                                    for data in tim_summary.values()])
                
                admin_title = "📋 Ringkasan Jadwal Besok"
                admin_message = f"{len(tim_summary)} tim memiliki total {total_all_lokasi} lokasi besok"
                
                for admin in admin_users:
                    try:
                        Notification.objects.create(
                            user=admin,
                            title=admin_title,
                            message=admin_message,
                            notification_type="system_summary",
                            priority="normal",
                            url="http://localhost:5173/#/admin/jadwal",
                            data={
                                'total_tim': len(tim_summary),
                                'total_lokasi': total_all_lokasi,
                                'tim_list': tim_list,
                                'date': tomorrow.isoformat()
                            }
                        )
                        logger.debug(f"✓ Ringkasan dikirim ke admin: {admin.username}")
                    except Exception as e:
                        logger.error(f"❌ Error ringkasan untuk admin {admin.username}: {e}")
        
        logger.info(f"✓ Selesai: {len(results)} push notifications terkirim untuk {len(tim_summary)} tim")
        
        return results

# # utils/notifications.py
# import json
# import logging
# from django.db import models
# from django.conf import settings
# from django.contrib.auth import get_user_model
# from pywebpush import webpush, WebPushException
# from django.utils import timezone
# from datetime import timedelta

# from ..models import PushSubscription, Notification

# logger = logging.getLogger(__name__)
# User = get_user_model()


# class NotificationService:
#     """
#     Centralized Web Push Notification Service
#     """

#     # =====================================================
#     # CORE SENDER
#     # =====================================================

#     @staticmethod
#     def send_notification_to_user(
#         user,
#         title,
#         body,
#         notification_type="general",
#         url="/",
#         data=None,
#         create_db_notification=True,  # ✅ Parameter baru
#     ):
#         """
#         Kirim push notification ke SATU user
#         """
#         # ✅ SIMPAN KE DATABASE NOTIFICATION
#         if create_db_notification:
#             try:
#                 Notification.objects.create(
#                     user=user,
#                     title=title,
#                     message=body,
#                     notification_type=notification_type,
#                     priority="high" if notification_type in ["payment_new", "laporan_new", "alert"] else "normal",
#                     data=data or {},
#                     read=False
#                 )
#                 logger.info(f"📝 Database notification created for {user.username}")
#             except Exception as e:
#                 logger.error(f"❌ Failed to create database notification: {e}")
        
#         subscriptions = PushSubscription.objects.filter(user=user)

#         if not subscriptions.exists():
#             logger.warning("❌ No subscription for user %s", user.username)
#             return []

#         payload = {
#             "title": title,
#             "body": body,
#             "icon": "/icons/icon-192x192.png",
#             "url": url,
#             "type": notification_type,
#             "data": data or {},
#         }

#         results = []

#         for subscription in subscriptions:
#             try:
#                 webpush(
#                     subscription_info=subscription.to_dict(),
#                     data=json.dumps(payload),
#                     vapid_private_key=settings.WEBPUSH_SETTINGS["VAPID_PRIVATE_KEY"],
#                     vapid_claims={
#                         "sub": f"mailto:{settings.WEBPUSH_SETTINGS['VAPID_ADMIN_EMAIL']}"
#                     },
#                 )

#                 results.append({
#                     "status": "success",
#                     "endpoint": subscription.endpoint,
#                 })

#                 logger.info("✅ Notification sent to %s", user.username)

#             except WebPushException as ex:
#                 # Subscription expired / gone
#                 if ex.response and ex.response.status_code in (404, 410):
#                     subscription.delete()
#                     logger.warning("🧹 Deleted expired subscription for %s", user.username)

#                 logger.error("❌ WebPush error (%s): %s", user.username, ex)
#                 results.append({"status": "failed", "error": str(ex)})

#             except Exception as e:
#                 logger.exception("❌ Unknown push error: %s", e)

#         return results

#     # =====================================================
#     # ADMIN HELPERS
#     # =====================================================

#     @staticmethod
#     def _get_admin_users():
#         """
#         Ambil semua user dengan role='admin' DAN/ATAU is_staff=True
#         """
#         # Gunakan OR untuk cover kedua kemungkinan
#         admin_users = User.objects.filter(
#             models.Q(role='admin') | models.Q(is_staff=True),
#             is_active=True
#         ).distinct()
        
#         return admin_users
    
#     @staticmethod
#     def _get_admin_users_with_push():
#         """
#         Ambil admin users YANG MEMILIKI PUSH SUBSCRIPTION
#         """
#         # Dapatkan semua admin
#         all_admins = User.objects.filter(
#             models.Q(role='admin') | models.Q(is_staff=True),
#             is_active=True
#         ).distinct()
        
#         # Filter hanya yang punya subscription
#         admin_ids_with_push = PushSubscription.objects.filter(
#             user__in=all_admins
#         ).values_list('user_id', flat=True).distinct()
        
#         return User.objects.filter(id__in=admin_ids_with_push)

#     @staticmethod
#     def notify_admin(
#         title,
#         body,
#         notification_type="admin",
#         url="/admin/",
#         data=None,
#     ):
#         """
#         Notifikasi ke SEMUA USER DENGAN ROLE='admin'
#         """
#         from django.db import models
#         from ..models import Notification
        
#         # 1. Database notification untuk SEMUA admin (role='admin')
#         all_admins = User.objects.filter(
#             models.Q(role='admin') | models.Q(is_staff=True),
#             is_active=True
#         ).distinct()
        
#         logger.info(f"👮 Found {all_admins.count()} admin users")
#         logger.info(f"   Admin list: {list(all_admins.values_list('username', flat=True))}")
        
#         db_notifications = []
        
#         for admin in all_admins:
#             logger.info(f"   📝 Creating notification for: {admin.username} (role: {admin.role}, is_staff: {admin.is_staff})")
            
#             notification = Notification.objects.create(
#                 user=admin,
#                 title=title,
#                 message=body,
#                 notification_type=notification_type,
#                 priority="high" if notification_type in ["payment_new", "laporan_new"] else "normal",
#                 data=data or {},
#                 read=False
#             )
#             db_notifications.append(notification.id)
        
#         # 2. Push notification HANYA untuk admin dengan subscription
#         admins_with_push = NotificationService._get_admin_users_with_push()
#         logger.info(f"📱 Admins with push subscription: {admins_with_push.count()}")
        
#         push_results = []
        
#         for admin in admins_with_push:
#             logger.info(f"   📤 Sending push to: {admin.username}")
            
#             results = NotificationService.send_notification_to_user(
#                 user=admin,
#                 title=title,
#                 body=body,
#                 notification_type=notification_type,
#                 url=url,
#                 data=data,
#                 create_db_notification=False
#             )
#             push_results.extend(results)
        
#         return {
#             "database_notifications": db_notifications,
#             "push_notifications": push_results,
#             "total_admins": all_admins.count(),
#             "admins_with_push": admins_with_push.count(),
#             "admins_list": list(all_admins.values_list('username', flat=True)),
#             "admins_with_push_list": list(admins_with_push.values_list('username', flat=True))
#         }

#     # =====================================================
#     # PAYMENT NOTIFICATIONS
#     # =====================================================

#     @staticmethod
#     def send_payment_status_update(pembayaran):
#         """
#         Notifikasi ke ANGGOTA saat status pembayaran berubah
#         """
#         anggota = pembayaran.idAnggota
#         user = anggota.user

#         status_map = {
#             "pending": "menunggu konfirmasi",
#             "lunas": "telah dikonfirmasi",
#             "gagal": "ditolak",
#         }

#         title = "💳 Status Pembayaran Diperbarui"
#         body = (
#             f"Pembayaran Rp {pembayaran.jumlahBayar:,} "
#             f"{status_map.get(pembayaran.statusBayar, '')}"
#         )

#         return NotificationService.send_notification_to_user(
#             user=user,
#             title=title,
#             body=body,
#             notification_type="payment_update",
#             url=f"/pembayaran/{pembayaran.pk}/",
#             data={
#                 "pembayaran_id": pembayaran.pk,
#                 "status": pembayaran.statusBayar,
#                 "amount": pembayaran.jumlahBayar,
#             },
#         )

#     @staticmethod
#     def notify_admin_payment_pending(pembayaran):
#         """
#         Notifikasi ADMIN saat ada pembayaran baru (pending)
#         """
#         title = "💰 Pembayaran Baru"
#         body = (
#             f"Anggota {pembayaran.idAnggota.nama} "
#             f"mengirim pembayaran Rp {pembayaran.jumlahBayar:,}"
#         )

#         return NotificationService.notify_admin(
#             title=title,
#             body=body,
#             notification_type="payment_new",
#             url="/admin/pembayaran/",
#             data={"pembayaran_id": pembayaran.pk},
#         )

#     # =====================================================
#     # PICKUP / JADWAL
#     # =====================================================

#     @staticmethod
#     def send_pickup_status_update(detail_jadwal):
#         """
#         Notifikasi ke ANGGOTA saat status pengangkutan berubah
#         """
#         anggota = detail_jadwal.idAnggota
#         user = anggota.user
#         jadwal = detail_jadwal.idJadwal

#         status_map = {
#             "terjadwal": "Terjadwal",
#             "dalam_proses": "Sedang diproses",
#             "selesai": "Telah selesai",
#             "dibatalkan": "Dibatalkan",
#         }

#         title = "🚛 Status Pengangkutan Diperbarui"
#         body = (
#             f"Pengangkutan pada {jadwal.tanggalJadwal} "
#             f"{status_map.get(detail_jadwal.status_pengangkutan)}"
#         )

#         if detail_jadwal.catatan:
#             body += f"\n📝 {detail_jadwal.catatan}"

#         return NotificationService.send_notification_to_user(
#             user=user,
#             title=title,
#             body=body,
#             notification_type="pickup_update",
#             url=f"/jadwal/{jadwal.pk}/",
#             data={
#                 "jadwal_id": jadwal.pk,
#                 "status": detail_jadwal.status_pengangkutan,
#             },
#         )

#     @staticmethod
#     def notify_admin_new_schedule(detail_jadwal):
#         """
#         Notifikasi ADMIN saat detail jadwal baru dibuat
#         """
#         title = "📅 Jadwal Pengangkutan Baru"
#         body = (
#             f"Jadwal baru untuk anggota "
#             f"{detail_jadwal.idAnggota.nama} "
#             f"pada {detail_jadwal.idJadwal.tanggalJadwal}"
#         )

#         return NotificationService.notify_admin(
#             title=title,
#             body=body,
#             notification_type="schedule_new",
#             url="/admin/jadwal/",
#             data={"jadwal_id": detail_jadwal.idJadwal.pk},
#         )
    
#     @staticmethod
#     def send_laporan_status_update(laporan):
#         """
#         TAMU / PELAPOR
#         """
#         if not laporan.user:
#             return []

#         title = "🚨 Status Laporan Sampah"
#         body = f"Laporan Anda sekarang berstatus: {laporan.get_status_display()}"

#         return NotificationService.send_notification_to_user(
#             user=laporan.user,
#             title=title,
#             body=body,
#             notification_type="laporan_update",
#             url=f"/laporan/{laporan.pk}/",
#             data={
#                 "laporan_id": laporan.pk,
#                 "status": laporan.status,
#             },
#         )
    
#     # Tambahkan di bagian setelah send_laporan_status_update()

#     @staticmethod
#     def notify_tamu_laporan_diterima(laporan):
#         """
#         Kirim notifikasi ke TAMU saat laporan baru diterima
#         """
#         if not laporan.user:
#             logger.warning(f"❌ Laporan {laporan.id} has no user associated")
#             return []
        
#         user = laporan.user
        
#         title = "✅ Laporan Sampah Diterima"
#         body = f"Laporan sampah Anda di {laporan.alamat or 'lokasi tersebut'} telah diterima"
        
#         if laporan.deskripsi:
#             body += f": {laporan.deskripsi[:50]}..."
        
#         logger.info(f"📝 Notifying user {user.username} about new laporan")
        
#         return NotificationService.send_notification_to_user(
#             user=user,
#             title=title,
#             body=body,
#             notification_type='report',
#             url=f'/laporan/{laporan.id}/',
#             data={
#                 'laporan_id': laporan.id,
#                 'status': 'diterima',
#                 'alamat': laporan.alamat,
#                 'timestamp': timezone.now().isoformat()
#             }
#         )

#     @staticmethod
#     def notify_tamu_laporan_status(laporan):
#         """
#         Kirim notifikasi ke TAMU saat status laporan berubah
#         """
#         if not laporan.user:
#             logger.warning(f"❌ Laporan {laporan.id} has no user associated")
#             return []
        
#         user = laporan.user
        
#         # Map status ke bahasa Indonesia
#         status_map = {
#             'pending': 'menunggu verifikasi',
#             'proses': 'sedang diproses',
#             'selesai': 'telah selesai',
#             'ditolak': 'ditolak'
#         }
        
#         title = "📢 Status Laporan Diperbarui"
#         status_display = laporan.get_status_display() or status_map.get(laporan.status, laporan.status)
#         body = f"Laporan sampah Anda sekarang berstatus: {status_display}"
        
#         # Tambahkan alamat jika ada
#         if laporan.alamat:
#             body += f"\n📍 {laporan.alamat}"
        
#         logger.info(f"📝 Notifying user {user.username} about laporan status update: {laporan.status}")
        
#         return NotificationService.send_notification_to_user(
#             user=user,
#             title=title,
#             body=body,
#             notification_type='laporan_update',
#             url=f'/laporan/{laporan.id}/',
#             data={
#                 'laporan_id': laporan.id,
#                 'status': laporan.status,
#                 'status_display': status_display,
#                 'alamat': laporan.alamat,
#                 'timestamp': timezone.now().isoformat()
#             }
#         )
    
#     @staticmethod
#     def notify_team_new_schedule(detail_jadwal):
#         """
#         Notifikasi ke TIM ANGKUT untuk jadwal BESOK
#         """
#         from apk.models import DetailAnggotaJadwal
#         from django.contrib.auth import get_user_model

#         User = get_user_model()

#         if not isinstance(detail_jadwal, DetailAnggotaJadwal):
#             raise ValueError(
#                 f"Object is not DetailAnggotaJadwal: {type(detail_jadwal)}"
#             )

#         jadwal = detail_jadwal.idJadwal
#         tim = jadwal.idTim

#         if not tim:
#             return []

#         # 🔑 AMBIL USER TIM ANGKUT (GLOBAL)
#         tim_users = User.objects.filter(
#             role="tim_angkut",
#             is_active=True
#         )

#         if not tim_users.exists():
#             return []

#         results = []

#         for user in tim_users:
#             results.extend(
#                 NotificationService.send_notification_to_user(
#                     user=user,
#                     title="🚛 Jadwal Pengangkutan Besok",
#                     body=(
#                         f"Besok ({jadwal.tanggalJadwal}) ada jadwal "
#                         f"pengangkutan untuk tim {tim.namaTim}"
#                     ),
#                     notification_type="schedule_reminder",
#                     url=f"/tim-angkut/jadwal/{jadwal.pk}/",
#                     data={
#                         "jadwal_id": jadwal.pk,
#                         "detail_id": detail_jadwal.pk,
#                         "tim": tim.namaTim,
#                     },
#                 )
#             )

#         return results

#     @staticmethod
#     def notify_team_tomorrow_schedule():
#         """Notify Tim Angkut about tomorrow's schedule"""
#         try:
#             from ..models import Jadwal, DetailAnggotaJadwal  # ✅ Tambahkan import
            
#             tomorrow = timezone.now().date() + timedelta(days=1)
#             jadwals_tomorrow = Jadwal.objects.filter(tanggalJadwal=tomorrow)
            
#             if not jadwals_tomorrow.exists():
#                 logger.info("ℹ No schedules for tomorrow")
#                 return []
            
#             results = []
            
#             for jadwal in jadwals_tomorrow:
#                 count_locations = DetailAnggotaJadwal.objects.filter(
#                     idJadwal=jadwal
#                 ).count()
                
#                 tim_angkut_users = User.objects.filter(role='tim_angkut')
                
#                 for user in tim_angkut_users:
#                     # ✅ Ganti create_notification dengan Notification.objects.create
#                     Notification.objects.create(
#                         user=user,
#                         title="📋 Jadwal Pengangkutan Besok",
#                         message=f"Besok ada {count_locations} lokasi untuk tim {jadwal.idTim.namaTim}",
#                         notification_type="schedule",
#                         url=f"/tim-angkut/jadwal/{jadwal.idJadwal}/"
#                     )
                    
#                     # Juga kirim push notification
#                     results.extend(
#                         NotificationService.send_notification_to_user(
#                             user=user,
#                             title="📋 Jadwal Pengangkutan Besok",
#                             body=f"Besok ada {count_locations} lokasi untuk tim {jadwal.idTim.namaTim}",
#                             notification_type="schedule_reminder",
#                             url=f"/tim-angkut/jadwal/{jadwal.idJadwal}/",
#                             data={
#                                 'jadwal_id': jadwal.idJadwal,
#                                 'count_locations': count_locations,
#                                 'tim_nama': jadwal.idTim.namaTim
#                             }
#                         )
#                     )
            
#             logger.info(f"✓ Notified about {jadwals_tomorrow.count()} tomorrow schedules")
#             return results
            
#         except Exception as e:
#             logger.error(f"✗ Error in notify_team_tomorrow_schedule: {e}")
#             return []