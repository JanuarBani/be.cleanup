from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .filters import (
    AnggotaFilter,
    TimPengangkutFilter,
    TamuFilter,
    JadwalFilter,
    PembayaranFilter,
    DetailAnggotaJadwalFilter,
    LaporanSampahFilter
)

class AnggotaViewSet(ModelViewSet):
    queryset = Anggota.objects.select_related("user", "idTim")
    serializer_class = AnggotaSerializer
    permission_classes = [PermissionAnggota]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = AnggotaFilter
    search_fields = ["nama", "alamat", "user__username"]
    ordering_fields = ["nama", "tanggal_join", "idAnggota"]
    ordering = ["nama"]

class TimPengangkutViewSet(ModelViewSet):
    queryset = TimPengangkut.objects.all()
    serializer_class = TimPengangkutSerializer
    permission_classes = [PermissionTimPengangkut]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = TimPengangkutFilter
    search_fields = ["nama_tim", "user__username"]
    ordering_fields = ["nama_tim", "idTim"]

class TamuViewSet(ModelViewSet):
    queryset = Tamu.objects.select_related("user")
    serializer_class = TamuSerializer
    permission_classes = [PermissionTamu]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = TamuFilter
    search_fields = ["nama", "user__username"]
    ordering_fields = ["nama", "idTamu"]

class JadwalViewSet(ModelViewSet):
    serializer_class = JadwalSerializer
    permission_classes = [PermissionJadwal]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = JadwalFilter
    search_fields = ["idTim__nama_tim"]
    ordering_fields = ["tanggal", "idJadwal"]

    def get_queryset(self):
        user = self.request.user
        qs = Jadwal.objects.select_related("idTim")
        role = getattr(user, "role", None)

        if role == "admin":
            return qs
        if role == "tim_angkut":
            return qs.filter(idTim__user=user)
        if role == "anggota":
            return qs.filter(detailanggottajadwal__idAnggota__user=user)

        return qs.none()

class PembayaranViewSet(ModelViewSet):
    serializer_class = PembayaranSerializer
    permission_classes = [PermissionPembayaran]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = PembayaranFilter
    search_fields = ["status", "idAnggota__nama"]
    ordering_fields = ["tanggal_bayar", "jumlah", "idPembayaran"]

    def get_queryset(self):
        user = self.request.user
        qs = Pembayaran.objects.select_related("idAnggota")
        role = getattr(user, "role", None)

        if role == "admin":
            return qs
        if role == "anggota":
            return qs.filter(idAnggota__user=user)
        if role == "tim_angkut":
            return qs

        return qs.none()

class DetailAnggotaJadwalViewSet(ModelViewSet):
    serializer_class = DetailAnggotaJadwalSerializer
    permission_classes = [PermissionDetailAnggotaJadwal]

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = DetailAnggotaJadwalFilter
    ordering_fields = ["idAnggota", "idJadwal"]

    def get_queryset(self):
        user = self.request.user
        qs = DetailAnggotaJadwal.objects.select_related(
            "idAnggota", "idJadwal", "idJadwal__idTim"
        )
        role = getattr(user, "role", None)

        if role == "admin":
            return qs
        if role == "tim_angkut":
            return qs.filter(idJadwal__idTim__user=user)
        if role == "anggota":
            return qs.filter(idAnggota__user=user)

        return qs.none()

class LaporanSampahViewSet(ModelViewSet):
    serializer_class = LaporanSampahSerializer
    permission_classes = [PermissionLaporanSampah]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = LaporanSampahFilter
    search_fields = ["nama", "alamat"]
    ordering_fields = ["tanggal_lapor", "idLaporan"]

    def get_queryset(self):
        user = self.request.user
        qs = LaporanSampah.objects.select_related("idAnggota")
        role = getattr(user, "role", None)

        if role == "admin":
            return qs
        if role == "tim_angkut":
            return qs
        if role in ("anggota", "tamu"):
            return qs.filter(idAnggota__user=user)

        return qs.none()

    def perform_create(self, serializer):
        user = self.request.user

        if user.role not in ("anggota", "tamu", "admin"):
            raise PermissionDenied("Tidak boleh membuat laporan.")

        anggota = Anggota.objects.filter(user=user).first()
        if not anggota:
            raise PermissionDenied("User tidak memiliki anggota terkait.")

        serializer.save(idAnggota=anggota)
