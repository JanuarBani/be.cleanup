from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q, Count
from rest_framework.decorators import action

from .models import (
    User,
    TimPengangkut,
    Anggota,
    Tamu,
    Jadwal,
    Pembayaran,
    DetailAnggotaJadwal,
    LaporanSampah
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
    UpgradeAnggotaSerializer,
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
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterTamuSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Pendaftaran berhasil"}, status=201)

        return Response(serializer.errors, status=400)


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
    serializer_class = TimPengangkutSerializer
    permission_classes = [IsAuthenticated, PermissionTimPengangkut]
    
    def get_queryset(self):
        # Return semua data tanpa filter (karena model sederhana)
        # Admin bisa lihat semua, user lain juga bisa lihat semua
        return TimPengangkut.objects.all()
    
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
    queryset = Anggota.objects.select_related("user")  # hapus "idTim" jika tidak ada
    serializer_class = AnggotaSerializer
    permission_classes = [PermissionAnggota]  # pastikan ini list, bukan tuple

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
                raise PermissionDenied("Anda hanya bisa membuat pembayaran untuk akun Anda sendiri.")
        
        # Simpan pembayaran
        serializer.save()
    
    def perform_update(self, serializer):
        user = self.request.user
        
        if user.role == "anggota":
            # Anggota hanya bisa update pembayaran miliknya sendiri
            instance = self.get_object()
            if instance.idAnggota.user != user:
                raise PermissionDenied("Anda hanya bisa mengupdate pembayaran milik Anda sendiri.")
            
            # Anggota tidak boleh mengubah idAnggota
            if 'idAnggota' in serializer.validated_data:
                if serializer.validated_data['idAnggota'] != instance.idAnggota:
                    raise PermissionDenied("Anda tidak boleh mengubah data anggota.")
        
        serializer.save()
    
    def perform_destroy(self, instance):
        user = self.request.user
        
        if user.role == "anggota":
            # Anggota tidak boleh menghapus pembayaran
            raise PermissionDenied("Anda tidak memiliki izin untuk menghapus pembayaran.")
        
        if user.role == "tim_angkut":
            # Tim angkut tidak boleh menghapus
            raise PermissionDenied("Tim angkut tidak memiliki izin untuk menghapus pembayaran.")
        
        # Hanya admin yang boleh menghapus
        instance.delete()

# ============================
#      DETAIL ANGGOTA JADWAL
# ============================

class DetailAnggotaJadwalViewSet(ModelViewSet):
    serializer_class = DetailAnggotaJadwalSerializer
    permission_classes = [PermissionDetailAnggotaJadwal]

    def get_queryset(self):
        user = self.request.user
        qs = DetailAnggotaJadwal.objects.select_related(
            "idAnggota",
            "idJadwal",
            "idJadwal__idTim",
        )

        role = getattr(user, "role", None)

        if role == "admin":
            return qs

        if role == "tim_angkut":
            return qs

        if role == "anggota":
            return qs.filter(idAnggota__user=user)

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
        # ALL USER (termasuk tidak login) dapat melihat semua laporan
        return LaporanSampah.objects.select_related("idUser")

    def perform_create(self, serializer):
        user = self.request.user

        if not user.is_authenticated:
            raise PermissionDenied("Harus login untuk membuat laporan.")

        if user.role not in ("admin", "anggota", "tamu"):
            raise PermissionDenied("Role tidak diizinkan membuat laporan.")

        serializer.save(idUser=user)
