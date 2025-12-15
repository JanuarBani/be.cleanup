from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterTamuView,
    UpgradeAnggotaView,
    UserViewSet,
    TimPengangkutViewSet,
    AnggotaViewSet,
    TamuViewSet,
    JadwalViewSet,
    PembayaranViewSet,
    DetailAnggotaJadwalViewSet,
    LaporanSampahViewSet,
)

from .reports import (
    KeuanganReportView,
    AnggotaReportView,
    LaporanSampahReportView,
    JadwalReportView,
    UserStatReportView,
    MonthlyReportView,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')
router.register(r'tim-pengangkut', TimPengangkutViewSet, basename='tim-pengangkut')
router.register(r'anggota', AnggotaViewSet, basename='anggota')
router.register(r'tamu', TamuViewSet, basename='tamu')
router.register(r'jadwal', JadwalViewSet, basename='jadwal')
router.register(r'pembayaran', PembayaranViewSet, basename='pembayaran')
router.register(r'detail-anggota-jadwal', DetailAnggotaJadwalViewSet, basename='detail-anggota-jadwal')
router.register(r'laporan-sampah', LaporanSampahViewSet, basename='laporan-sampah')

app_name = 'cleanapk'

# Report URLs
report_urlpatterns = [
    path('reports/keuangan/', KeuanganReportView.as_view(), name='report-keuangan'),
    path('reports/anggota/', AnggotaReportView.as_view(), name='report-anggota'),
    path('reports/laporan-sampah/', LaporanSampahReportView.as_view(), name='report-laporan-sampah'),
    path('reports/jadwal/', JadwalReportView.as_view(), name='report-jadwal'),
    path('reports/user-stats/', UserStatReportView.as_view(), name='report-user-stats'),
    path('reports/monthly/', MonthlyReportView.as_view(), name='report-monthly'),
]

urlpatterns = [
    path('register/', RegisterTamuView.as_view(), name="register_tamu"),
    path("upgrade-anggota/", UpgradeAnggotaView.as_view(), name="upgrade_anggota"),
    path('', include(router.urls)),
] + report_urlpatterns
