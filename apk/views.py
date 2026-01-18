from rest_framework import permissions
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q, Count
from rest_framework.decorators import action
from django.conf import settings
from .utils.notifications import NotificationService
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from django.db import transaction


from .models import (
    User,
    TimPengangkut,
    Anggota,
    Tamu,
    Jadwal,
    Pembayaran,
    DetailAnggotaJadwal,
    LaporanSampah,
    PushSubscription,
    Notification
)

from .serializers import (
    UserSerializer,
    TimPengangkutSerializer,
    AnggotaSerializer,
    TamuSerializer,
    JadwalSerializer,
    PembayaranSerializer,
    DetailAnggotaJadwalSerializer,
    LaporanSampahSerializer,
    RegisterTamuSerializer,
    RegisterAnggotaSerializer,
    UpgradeAnggotaSerializer,
    PushSubscriptionSerializer,
    NotificationSerializer,
)

from .permissions import (
    PermissionTimPengangkut,
    PermissionAnggota,
    PermissionTamu,
    PermissionJadwal,
    PermissionPembayaran,
    PermissionDetailAnggotaJadwal,
    PermissionLaporanSampah,
    PublicReadPermission
)


class RegisterTamuView(APIView):
    permission_classes = [AllowAny]  # Bisa diakses tanpa login

    def post(self, request):
        # 1. Validasi data dengan serializer
        serializer = RegisterTamuSerializer(data=request.data)

        # 2. Cek apakah data valid
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 3. Simpan data (create() di serializer akan dipanggil)
        result = serializer.save()

        # 4. Return response ke client
        return Response({
            'message': 'Registrasi berhasil',
            'user_id': result['user'].id,
            'tamu_id': result['tamu'].idTamu,
            'username': result['user'].username
        }, status=status.HTTP_201_CREATED)


class RegisterAnggotaView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterAnggotaSerializer(data=request.data)

        if serializer.is_valid():
            result = serializer.save()
            return Response({
                "message": "Registrasi anggota berhasil",
                "user_id": result["user"].id,
                "anggota_id": result["anggota"].idAnggota,
                "username": result["user"].username,
                "role": result["user"].role
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ============================
#            USER
# ============================


class UserViewSet(ModelViewSet):
    """ViewSet User untuk kebutuhan admin (CRUD user)."""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filter queryset berdasarkan role user yang sedang login.
        Admin bisa lihat semua user, user lain hanya lihat dirinya sendiri.
        """
        user = self.request.user

        # Jika user adalah admin
        if hasattr(user, 'role') and user.role == 'admin':
            return User.objects.all().order_by('-date_joined')

        # Jika bukan admin, hanya bisa lihat profil sendiri
        return User.objects.filter(id=user.id)

    def create(self, request, *args, **kwargs):
        """
        Create user baru - HANYA ADMIN yang bisa
        """
        # Cek jika user adalah admin
        if not (hasattr(request.user, 'role') and request.user.role == 'admin'):
            return Response(
                {"error": "Hanya admin yang bisa membuat user baru"},
                status=status.HTTP_403_FORBIDDEN
            )

        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """
        Update user - admin bisa update semua, user hanya bisa update diri sendiri
        """
        instance = self.get_object()
        user = request.user

        # Cek permission
        if not (user.role == 'admin' or user.id == instance.id):
            return Response(
                {"error": "Anda tidak memiliki izin untuk mengupdate user ini"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Jika bukan admin, hanya bisa update email dan password
        if user.role != 'admin':
            allowed_fields = ['email', 'password']
            for field in list(request.data.keys()):
                if field not in allowed_fields:
                    del request.data[field]

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
        Delete user - HANYA ADMIN yang bisa, dan tidak bisa delete diri sendiri
        """
        instance = self.get_object()
        user = request.user

        # Hanya admin yang bisa delete
        if not (hasattr(user, 'role') and user.role == 'admin'):
            return Response(
                {"error": "Hanya admin yang bisa menghapus user"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Cegah admin menghapus diri sendiri
        if instance.id == user.id:
            return Response(
                {"error": "Tidak bisa menghapus akun sendiri"},
                status=status.HTTP_400_BAD_REQUEST
            )

        return super().destroy(request, *args, **kwargs)

    # ==========================
    #   SOFT DELETE (DEACTIVATE)
    # ==========================
    @action(detail=True, methods=["patch"], url_path="deactivate")
    def deactivate(self, request, pk=None):
        user = self.get_object()
        current_user = request.user

        if current_user.role != "admin":
            return Response(
                {"detail": "Hanya admin yang bisa menonaktifkan user"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if user.id == current_user.id:
            return Response(
                {"detail": "Tidak bisa menonaktifkan akun sendiri"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = False
        user.save(update_fields=["is_active"])

        return Response(
            {"message": "User berhasil dinonaktifkan"},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Endpoint untuk mendapatkan data user yang sedang login"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        """Endpoint untuk update profil user yang sedang login"""
        user = request.user
        serializer = self.get_serializer(user, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def stats(self, request):
        """Get statistics (admin only)"""
        if not (hasattr(request.user, 'role') and request.user.role == 'admin'):
            return Response(
                {"error": "Hanya admin yang bisa melihat statistik"},
                status=status.HTTP_403_FORBIDDEN
            )

        from django.utils import timezone

        total = User.objects.count()
        active = User.objects.filter(is_active=True).count()
        today = timezone.now().date()
        new_today = User.objects.filter(date_joined__date=today).count()

        return Response({
            "total_users": total,
            "active_users": active,
            "new_users_today": new_today,
            "timestamp": timezone.now()
        })

# ============================
#      TIM PENGANGKUT
# ============================


class TimPengangkutViewSet(ModelViewSet):
    """
    ViewSet sederhana untuk TimPengangkut.
    Hanya menggunakan 1 serializer.
    """
    queryset = TimPengangkut.objects.all()
    serializer_class = TimPengangkutSerializer
    permission_classes = [IsAuthenticated, PermissionTimPengangkut]

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'success': True,
                'data': serializer.data,
                'count': queryset.count()
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'success': True,
                    'message': 'Tim berhasil dibuat',
                    'data': serializer.data
                }, status=status.HTTP_201_CREATED)
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ============================
#          ANGGOTA
# ============================


class AnggotaViewSet(ModelViewSet):
    queryset = Anggota.objects.select_related("user")
    serializer_class = AnggotaSerializer
    permission_classes = [PermissionAnggota]

    def get_queryset(self):
        """
        Filter anggota berdasarkan query param 'user' jika ada.
        Contoh: /api/anggota/?user=6
        """
        queryset = super().get_queryset()
        user_id = self.request.query_params.get("user")
        if user_id:
            queryset = queryset.filter(user__id=user_id)
        return queryset

    @action(detail=True, methods=['post'])
    def activate_schedules(self, request, pk=None):
        """Aktifkan kembali semua jadwal untuk anggota ini"""
        anggota = self.get_object()

        if anggota.status != 'aktif':
            return Response({
                'error': 'Anggota harus berstatus aktif untuk mengaktifkan jadwal'
            }, status=status.HTTP_400_BAD_REQUEST)

        detail_jadwals = DetailAnggotaJadwal.objects.filter(
            idAnggota=anggota,
            status_pengangkutan='dibatalkan'
        )

        today = timezone.now().date()
        reactivated_count = 0

        for detail in detail_jadwals:
            if detail.idJadwal.tanggalJadwal >= today:
                detail.status_pengangkutan = 'terjadwal'
                detail.catatan = f"Status pengangkutan diaktifkan kembali (ID Anggota: {anggota.idAnggota})"
                detail.save()
                reactivated_count += 1

        return Response({
            'success': True,
            'message': f'{reactivated_count} jadwal berhasil diaktifkan kembali',
            'reactivated_count': reactivated_count,
            'anggota_id': anggota.idAnggota,
            'anggota_nama': anggota.nama
        })

    @action(detail=True, methods=['get'])
    def schedule_summary(self, request, pk=None):
        """Get summary jadwal untuk anggota"""
        anggota = self.get_object()

        detail_jadwals = DetailAnggotaJadwal.objects.filter(idAnggota=anggota)

        # Grupkan berdasarkan status
        status_counts = detail_jadwals.values('status_pengangkutan').annotate(
            count=Count('id')
        )

        # Jadwal mendatang
        upcoming = detail_jadwals.filter(
            status_pengangkutan='terjadwal',
            idJadwal__tanggalJadwal__gte=timezone.now().date()
        ).order_by('idJadwal__tanggalJadwal')

        upcoming_data = [
            {
                'id': detail.id,
                'tanggal': detail.idJadwal.tanggalJadwal,
                'tim': detail.idJadwal.idTim.namaTim,
                'status': detail.status_pengangkutan,
                'catatan': detail.catatan
            }
            for detail in upcoming[:5]  # Limit 5 jadwal mendatang
        ]

        return Response({
            'anggota_id': anggota.idAnggota,
            'anggota_nama': anggota.nama,
            'status_anggota': anggota.status,
            'total_jadwal': detail_jadwals.count(),
            'status_counts': list(status_counts),
            'upcoming_schedules': upcoming_data,
            'last_updated': timezone.now()
        })

# class AnggotaViewSet(ModelViewSet):
#     queryset = Anggota.objects.select_related("user")  # hapus "idTim" jika tidak ada
#     serializer_class = AnggotaSerializer
#     permission_classes = [PermissionAnggota]  # pastikan ini list, bukan tuple

#     def get_queryset(self):
#         """
#         Filter anggota berdasarkan query param 'user' jika ada.
#         Contoh: /api/anggota/?user=6
#         """
#         queryset = super().get_queryset()
#         user_id = self.request.query_params.get("user")
#         if user_id:
#             queryset = queryset.filter(user__id=user_id)
#         return queryset


class UpgradeAnggotaView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != "tamu":
            return Response(
                {"error": "Hanya tamu yang bisa upgrade"},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = UpgradeAnggotaSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Upgrade berhasil!"}, status=201)

        return Response(serializer.errors, status=400)


# ============================
#            TAMU
# ============================

class TamuViewSet(ModelViewSet):
    queryset = Tamu.objects.select_related("idUser")
    serializer_class = TamuSerializer
    permission_classes = [PermissionTamu]

    def get_queryset(self):
        user = self.request.user

        # Jika user adalah admin, tampilkan SEMUA tamu
        if user.role == "admin":
            return Tamu.objects.all()

        # Jika bukan admin, tampilkan hanya tamu milik user tersebut
        return Tamu.objects.filter(idUser_id=user.id)


# ============================
#            JADWAL
# ============================
class JadwalViewSet(ModelViewSet):
    serializer_class = JadwalSerializer
    permission_classes = [PermissionJadwal]

    def get_queryset(self):
        user = self.request.user
        qs = Jadwal.objects.select_related("idTim")

        role = getattr(user, "role", None)

        if role == "admin":
            return qs

        if role == "tim_angkut":
            return qs.filter(idTim__user=user)

        if role == "anggota":
            return qs

        return qs.none()


# ============================
#          PEMBAYARAN
# ============================

class PembayaranViewSet(ModelViewSet):
    queryset = Pembayaran.objects.all()
    serializer_class = PembayaranSerializer

    def get_permissions(self):
        # Semua method memerlukan autentikasi (tidak ada public access)
        return [PermissionPembayaran()]

    def get_queryset(self):
        user = self.request.user

        # Semua user harus authenticated untuk pembayaran
        if not user.is_authenticated:
            return Pembayaran.objects.none()

        # Filter berdasarkan role
        qs = Pembayaran.objects.select_related("idAnggota")
        role = getattr(user, "role", None)

        if role == "admin":
            return qs  # Admin lihat semua

        if role == "anggota":
            # Anggota hanya lihat pembayaran miliknya sendiri
            return qs.filter(idAnggota__user=user)

        if role == "tim_angkut":
            # Tim angkut bisa lihat semua (readonly)
            return qs

        # Role lain tidak bisa lihat apa-apa
        return Pembayaran.objects.none()

    def perform_create(self, serializer):
        user = self.request.user

        if not user.is_authenticated:
            raise PermissionDenied("Harus login untuk membuat pembayaran.")

        if user.role not in ("admin", "anggota"):
            raise PermissionDenied("Role tidak diizinkan membuat pembayaran.")

        # Validasi tambahan untuk anggota
        if user.role == "anggota":
            # Pastikan anggota hanya membuat pembayaran untuk dirinya sendiri
            anggota = serializer.validated_data.get('idAnggota')
            if anggota.user != user:
                raise PermissionDenied(
                    "Anda hanya bisa membuat pembayaran untuk akun Anda sendiri.")

        # Simpan pembayaran
        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user

        if user.role == "anggota":
            # Anggota hanya bisa update pembayaran miliknya sendiri
            instance = self.get_object()
            if instance.idAnggota.user != user:
                raise PermissionDenied(
                    "Anda hanya bisa mengupdate pembayaran milik Anda sendiri.")

            # Anggota tidak boleh mengubah idAnggota
            if 'idAnggota' in serializer.validated_data:
                if serializer.validated_data['idAnggota'] != instance.idAnggota:
                    raise PermissionDenied(
                        "Anda tidak boleh mengubah data anggota.")

        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user

        if user.role == "anggota":
            # Anggota tidak boleh menghapus pembayaran
            raise PermissionDenied(
                "Anda tidak memiliki izin untuk menghapus pembayaran.")

        if user.role == "tim_angkut":
            # Tim angkut tidak boleh menghapus
            raise PermissionDenied(
                "Tim angkut tidak memiliki izin untuk menghapus pembayaran.")

        # Hanya admin yang boleh menghapus
        instance.delete()

# views.py - Perbaikan handle_payment_success


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def handle_payment_success(request, payment_id):
    """
    Handle pembayaran sukses dan update status anggota serta jadwal
    """
    try:
        pembayaran = get_object_or_404(Pembayaran, idPembayaran=payment_id)
        user = request.user

        # Validasi permission
        if user.role != 'admin' and pembayaran.idAnggota.user != user:
            return Response({
                'error': 'Anda tidak memiliki izin untuk mengkonfirmasi pembayaran ini'
            }, status=status.HTTP_403_FORBIDDEN)

        # Update pembayaran
        pembayaran.statusBayar = 'lunas'
        pembayaran.save()

        # Update anggota
        anggota = pembayaran.idAnggota

        # Hitung tanggal baru
        today = timezone.now().date()

        # Jika tanggalEnd sudah lewat, mulai dari hari ini
        if anggota.tanggalEnd < today:
            anggota.tanggalStart = today
            new_end_date = today + timedelta(days=30)
        else:
            # Tambah 30 hari dari tanggalEnd
            new_end_date = anggota.tanggalEnd + timedelta(days=30)

        anggota.tanggalEnd = new_end_date
        anggota.status = 'aktif'
        anggota.save()

        # Aktifkan kembali semua detail jadwal yang dibatalkan
        detail_jadwals = DetailAnggotaJadwal.objects.filter(
            idAnggota=anggota,
            status_pengangkutan='dibatalkan'
        )

        reactivated_count = 0
        upcoming_jadwals = []

        for detail in detail_jadwals:
            if detail.idJadwal.tanggalJadwal >= today:
                detail.status_pengangkutan = 'terjadwal'
                detail.catatan = f"Status pengangkutan diaktifkan kembali setelah pembayaran (Pembayaran ID: {payment_id})"
                detail.save()
                reactivated_count += 1

                # Tambah ke list jadwal mendatang
                upcoming_jadwals.append({
                    'id': detail.id,
                    'tanggal': detail.idJadwal.tanggalJadwal,
                    'tim': detail.idJadwal.idTim.namaTim
                })

        # Create notification for user
        if anggota.user:
            Notification.objects.create(
                user=anggota.user,
                title='🎉 Pembayaran Berhasil Dikonfirmasi',
                message=f'Pembayaran Anda telah dikonfirmasi. Keanggotaan aktif hingga {anggota.tanggalEnd}. {reactivated_count} jadwal diaktifkan kembali.',
                notification_type='payment',
                priority='high',
                data={
                    'payment_id': payment_id,
                    'anggota_id': anggota.idAnggota,
                    'tanggal_end': anggota.tanggalEnd.strftime('%Y-%m-%d'),
                    'reactivated_schedules': reactivated_count
                }
            )

        return Response({
            'status': 'success',
            'message': f'Pembayaran berhasil diproses. {reactivated_count} jadwal diaktifkan kembali.',
            'anggota': {
                'id': anggota.idAnggota,
                'nama': anggota.nama,
                'status': 'aktif',
                'tanggal_start': anggota.tanggalStart,
                'tanggal_end': anggota.tanggalEnd
            },
            'payment': {
                'id': pembayaran.idPembayaran,
                'jumlah': pembayaran.jumlahBayar,
                'metode': pembayaran.metodeBayar,
                'tanggal': pembayaran.tanggalBayar
            },
            'reactivated_schedules': reactivated_count,
            'upcoming_schedules': upcoming_jadwals
        })

    except Pembayaran.DoesNotExist:
        return Response({'error': 'Pembayaran tidak ditemukan'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

# ============================
#      DETAIL ANGGOTA JADWAL
# ============================


class DetailAnggotaJadwalViewSet(ModelViewSet):
    serializer_class = DetailAnggotaJadwalSerializer
    permission_classes = [PermissionDetailAnggotaJadwal]

    def get_queryset(self):
        user = self.request.user

        # DEBUG: Log user info
        print(
            f"🔍 get_queryset called - User: {user.username}, ID: {user.id}, Role: {getattr(user, 'role', 'N/A')}")

        # Gunakan select_related untuk optimasi query
        qs = DetailAnggotaJadwal.objects.select_related(
            "idAnggota",           # Load Anggota
            "idAnggota__user",     # Load User dari Anggota ← INI YANG DITAMBAHKAN
            "idJadwal",
            "idJadwal__idTim",
        ).order_by('-created_at')  # Tambahkan ordering

        role = getattr(user, "role", None)

        print(f"🔍 User role: {role}")

        if role == "admin":
            print("🔍 Returning ALL records for admin")
            return qs

        if role == "tim_angkut":
            print("🔍 Returning ALL records for tim_angkut")
            return qs

        if role == "anggota":
            # Filter hanya untuk anggota ini
            print(f"🔍 Filtering for anggota with user ID: {user.id}")

            # Cara 1: Filter langsung
            anggota_qs = qs.filter(idAnggota__user=user)
            print(f"🔍 Found {anggota_qs.count()} records for this anggota")

            # Debug: lihat data yang ditemukan
            if anggota_qs.exists():
                for item in anggota_qs[:3]:  # Lihat 3 pertama
                    print(
                        f"   - {item.id}: {item.idAnggota.nama} (User ID: {item.idAnggota.user.id if item.idAnggota.user else 'No user'})")

            return anggota_qs

        print(f"⚠️ No role or unknown role: {role}")
        return qs.none()

    # def perform_create(self, serializer):
    #     anggota = Anggota.objects.get(user=self.request.user)
    #     serializer.save(idAnggota=anggota)

    # def perform_update(self, serializer):
    #     anggota = Anggota.objects.get(user=self.request.user)
    #     serializer.save(idAnggota=anggota)

# ============================
#        LAPORAN SAMPAH
# ============================


class LaporanSampahViewSet(ModelViewSet):
    queryset = LaporanSampah.objects.all()
    serializer_class = LaporanSampahSerializer

    def get_permissions(self):
        # Public boleh GET
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [PublicReadPermission()]
        # Selain GET harus login dan role valid
        return [PermissionLaporanSampah()]

    def get_queryset(self):
        return LaporanSampah.objects.select_related("idUser").all()

    def perform_create(self, serializer):
        user = self.request.user

        if not user.is_authenticated:
            raise PermissionDenied("Harus login untuk membuat laporan.")

        if user.role not in ("admin", "anggota", "tamu"):
            raise PermissionDenied("Role tidak diizinkan membuat laporan.")

        serializer.save(idUser=user)

    def update(self, request, *args, **kwargs):
        """Override update untuk logging"""
        instance = self.get_object()

        # LOG: Data sebelum update
        print(f"🔍 BEFORE UPDATE - ID: {instance.idLaporan}")
        print(
            f"🔍 BEFORE - Latitude: {instance.latitude}, Longitude: {instance.longitude}")
        print(f"🔍 REQUEST DATA: {request.data}")

        # Handle file upload khusus
        if 'foto_bukti' in request.data:
            # Untuk file upload, gunakan request.FILES
            pass

        response = super().update(request, *args, **kwargs)

        # LOG: Data setelah update
        instance.refresh_from_db()
        print(f"✅ AFTER UPDATE - ID: {instance.idLaporan}")
        print(
            f"✅ AFTER - Latitude: {instance.latitude}, Longitude: {instance.longitude}")
        print(f"✅ RESPONSE DATA: {response.data}")

        return response

# class PushSubscriptionViewSet(ModelViewSet):
#     queryset = PushSubscription.objects.all()
#     serializer_class = PushSubscriptionSerializer

#     def create(self, request, *args, **kwargs):
#         data = request.data.copy()

#         subscription, created = PushSubscription.objects.update_or_create(
#             endpoint=data.get('endpoint'),
#             defaults={
#                 'auth': data.get('auth'),
#                 'p256dh': data.get('p256dh'),
#                 'user': request.user if request.user.is_authenticated else None
#             }
#         )

#         serializer = self.get_serializer(subscription)
#         return Response(
#             serializer.data,
#             status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
#         )


class PushSubscriptionViewSet(ModelViewSet):
    queryset = PushSubscription.objects.all()
    serializer_class = PushSubscriptionSerializer
    permission_classes = [IsAuthenticated]  # Hanya user terautentikasi

    def get_queryset(self):
        # User hanya bisa melihat subscription mereka sendiri
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Auto-assign user yang sedang login
        serializer.save(user=self.request.user)

    # @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    # def vapid_public_key(self, request):
    #     """
    #     Public endpoint untuk mendapatkan VAPID public key
    #     Tidak memerlukan autentikasi
    #     """
    #     public_key = getattr(settings, 'VAPID_PUBLIC_KEY', '')

    #     if not public_key:
    #         return Response({
    #             "error": "VAPID_PUBLIC_KEY is not configured"
    #         }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    #     return Response({
    #         "public_key": public_key,
    #         "admin_email": getattr(settings, 'VAPID_ADMIN_EMAIL', 'admin@cleanupkupang.id'),
    #         "key_length": len(public_key)
    #     })

    # Perbaikan import - gunakan absolute import
    @action(detail=False, methods=['post'], url_path='test_notification')
    def test_notification(self, request):
        """
        Send test notification to current user
        """
        try:
            from django.conf import settings
            import json
            from pywebpush import webpush, WebPushException
            from datetime import datetime

            print(
                f"🧪 Test notification requested by user: {request.user.username}")

            # Cek apakah user sudah subscribe
            subscriptions = self.get_queryset()

            if not subscriptions.exists():
                print(f"❌ User {request.user.username} has no subscription")
                return Response({
                    "success": False,
                    "message": "Anda belum berlangganan notifikasi push. Silakan aktifkan terlebih dahulu."
                }, status=status.HTTP_400_BAD_REQUEST)

            print(
                f"✅ User {request.user.username} has {subscriptions.count()} subscription(s)")

            # VAPID settings
            vapid_private_key = settings.WEBPUSH_SETTINGS.get(
                "VAPID_PRIVATE_KEY")
            vapid_admin_email = settings.WEBPUSH_SETTINGS.get(
                "VAPID_ADMIN_EMAIL")

            if not vapid_private_key or not vapid_admin_email:
                print("❌ VAPID keys not configured")
                return Response({
                    "success": False,
                    "message": "Server configuration error: VAPID keys missing"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Payload
            payload = {
                "title": "🧪 Test Notification - CleanUp",
                "body": "Ini adalah notifikasi test dari sistem CleanUp",
                "icon": "/icons/icon-192x192.png",
                "badge": "/icons/badge-72x72.png",
                "url": "/dashboard",
                "type": "test",
                "data": {
                    "test": True,
                    "timestamp": datetime.now().isoformat(),
                    "user": request.user.username
                }
            }

            results = []

            for subscription in subscriptions:
                try:
                    print(
                        f"   Sending to endpoint: {subscription.endpoint[:50]}...")

                    webpush(
                        subscription_info={
                            "endpoint": subscription.endpoint,
                            "keys": {
                                "p256dh": subscription.p256dh,
                                "auth": subscription.auth
                            }
                        },
                        data=json.dumps(payload),
                        vapid_private_key=vapid_private_key,
                        vapid_claims={
                            "sub": f"mailto:{vapid_admin_email}"
                        },
                    )

                    results.append({
                        "status": "success",
                        "endpoint": subscription.endpoint,
                    })

                    print(f"   ✅ Success!")

                except WebPushException as ex:
                    print(f"   ❌ WebPushException: {ex}")

                    # Subscription expired / gone
                    if ex.response and ex.response.status_code in (404, 410):
                        subscription.delete()
                        print(f"   🧹 Deleted expired subscription")

                    results.append({
                        "status": "failed",
                        "error": str(ex),
                        "type": "WebPushException"
                    })

                except Exception as e:
                    print(f"   ❌ Unknown error: {str(e)}")
                    results.append({
                        "status": "failed",
                        "error": str(e),
                        "type": "Unknown"
                    })

            success_count = sum(
                1 for r in results if r.get("status") == "success")

            if success_count > 0:
                return Response({
                    "success": True,
                    "message": f"Test notification sent successfully ({success_count} delivered)",
                    "results": results
                })
            else:
                error_message = results[0].get(
                    "error", "Unknown error") if results else "No subscriptions"
                return Response({
                    "success": False,
                    "message": f"Failed to send test notification: {error_message}",
                    "results": results
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print(f"❌ Error sending test notification: {str(e)}")
            import traceback
            traceback.print_exc()

            return Response({
                "success": False,
                "message": f"Server error: {str(e)}",
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def check_subscription(self, request):
        """
        Check if current user has subscription
        """
        has_subscription = self.get_queryset().exists()

        return Response({
            "has_subscription": has_subscription,
            "count": self.get_queryset().count()
        })

    @action(detail=False, methods=['post'])
    def reset(self, request):
        """
        Reset all subscriptions for current user
        """
        count = self.get_queryset().count()
        self.get_queryset().delete()

        return Response({
            "success": True,
            "message": f"Deleted {count} subscription(s) for {request.user.username}"
        })


class NotificationPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class NotificationViewSet(ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = NotificationPagination

    def get_queryset(self):
        user = self.request.user

        # Mulai dengan queryset dasar
        queryset = Notification.objects.filter(user=user)

        # Filter berdasarkan parameter query
        user_type = self.request.query_params.get('user_type', None)
        if user_type:
            queryset = queryset.filter(user__role=user_type)

        read_param = self.request.query_params.get('read', None)
        if read_param is not None:
            read_bool = read_param.lower() == 'true'
            queryset = queryset.filter(read=read_bool)

        notification_type = self.request.query_params.get('type', None)
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)

        priority = self.request.query_params.get('priority', None)
        if priority:
            queryset = queryset.filter(priority=priority)

        # Order by sebelum pagination
        queryset = queryset.order_by('-created_at')

        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = Notification.objects.filter(
            user=request.user, read=False).count()
        return Response({'count': count})

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.mark_as_read()
        return Response({'status': 'marked as read'})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        notifications = Notification.objects.filter(
            user=request.user, read=False)
        updated_count = notifications.update(
            read=True, updated_at=timezone.now())
        return Response({'status': 'marked as read', 'count': updated_count})

    @action(detail=False, methods=['post'])
    def test(self, request):
        """Endpoint untuk mengirim test notification"""
        user = request.user

        # Create test notification
        notification = Notification.objects.create(
            user=user,
            title='Test Notifikasi Admin',
            message='Ini adalah notifikasi test untuk panel admin. Semua sistem berjalan normal.',
            notification_type='test',
            priority='normal',
            data={
                'timestamp': timezone.now().isoformat(),
                'adminId': user.id,
                'version': '1.0.0',
                'user_agent': request.META.get('HTTP_USER_AGENT', '')
            }
        )

        serializer = self.get_serializer(notification)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent notifications (last 7 days)"""
        seven_days_ago = timezone.now() - timedelta(days=7)
        notifications = Notification.objects.filter(
            user=request.user,
            created_at__gte=seven_days_ago
        ).order_by('-created_at')

        page = self.paginate_queryset(notifications)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(notifications, many=True)
        return Response(serializer.data)

    def list(self, request):
        """Override list untuk menangani limit parameter"""
        queryset = self.get_queryset()

        # Handle limit parameter tanpa menggunakan slicing pada queryset
        limit = request.query_params.get('limit', None)
        if limit:
            try:
                limit_int = int(limit)
                # Gunakan pagination untuk limit
                self.pagination_class.page_size = limit_int
            except ValueError:
                pass

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def vapid_public_key(request):
    """
    Public endpoint untuk mendapatkan VAPID public key
    """
    from django.conf import settings

    public_key = getattr(settings, 'VAPID_PUBLIC_KEY', '')

    if not public_key:
        return Response({
            "error": "VAPID_PUBLIC_KEY is not configured in settings",
            "note": "Please add VAPID_PUBLIC_KEY to your Django settings"
        }, status=500)

    # Bersihkan key dari whitespace
    public_key = public_key.strip()

    return Response({
        "public_key": public_key,
        "key_length": len(public_key),
        "admin_email": getattr(settings, 'VAPID_ADMIN_EMAIL', 'admin@cleanupkupang.id'),
        "format": "base64 URL-safe",
        "note": "Use this key for Web Push subscriptions in browser"
    })
