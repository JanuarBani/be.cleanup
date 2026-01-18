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
    PushSubscriptionViewSet,
    NotificationViewSet,
    vapid_public_key,
    RegisterAnggotaView,
    handle_payment_success
)

from .reports import (
    KeuanganReportView,
    AnggotaReportView,
    LaporanSampahReportView,
    JadwalReportView,
    UserStatReportView,
    MonthlyReportView,
    ExportReportView,
    DampakLingkunganReportView,
)

from .viewPublik import PublicDampakLingkunganView, PublicLandingPageView

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')
router.register(r'tim-pengangkut', TimPengangkutViewSet,
                basename='tim-pengangkut')
router.register(r'anggota', AnggotaViewSet, basename='anggota')
router.register(r'tamu', TamuViewSet, basename='tamu')
router.register(r'jadwal', JadwalViewSet, basename='jadwal')
router.register(r'pembayaran', PembayaranViewSet, basename='pembayaran')
router.register(r'detail-anggota-jadwal',
                DetailAnggotaJadwalViewSet, basename='detail-anggota-jadwal')
router.register(r'laporan-sampah', LaporanSampahViewSet,
                basename='laporan-sampah')
router.register(r'push-subscriptions', PushSubscriptionViewSet,
                basename='push-subscription')
router.register(r'notifications', NotificationViewSet, basename='notification')

app_name = 'cleanapk'

# Report URLs
report_urlpatterns = [
    path('reports/keuangan/', KeuanganReportView.as_view(), name='report-keuangan'),
    path('reports/anggota/', AnggotaReportView.as_view(), name='report-anggota'),
    path('reports/laporan-sampah/', LaporanSampahReportView.as_view(),
         name='report-laporan-sampah'),
    path('reports/jadwal/', JadwalReportView.as_view(), name='report-jadwal'),
    path('reports/user-stats/', UserStatReportView.as_view(),
         name='report-user-stats'),
    path('reports/monthly/', MonthlyReportView.as_view(), name='report-monthly'),
    path('reports/dampak-lingkungan/', DampakLingkunganReportView.as_view(),
         name='dampak-lingkungan-report'),
    path('reports/export/', ExportReportView.as_view(), name='report-export'),
]

urlpatterns = [
    path('register/', RegisterTamuView.as_view(), name="register_tamu"),
    path('register-anggota/', RegisterAnggotaView.as_view(),
         name="register_anggota"),
    path("upgrade-anggota/", UpgradeAnggotaView.as_view(), name="upgrade_anggota"),
    path('api/public/analisis-lingkungan/', PublicDampakLingkunganView.as_view(), name='public-analisis'),
    path('api/public/landing-stats/', PublicLandingPageView.as_view(), name='public-landing'),
    path('', include(router.urls)),
    path('api/vapid-key/', vapid_public_key, name='vapid-key-public'),
    path('api/pembayaran/<int:payment_id>/success/',
         handle_payment_success,
         name='payment_success'),
] + report_urlpatterns
