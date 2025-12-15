from django.contrib import admin

# Register your models here.
from .models import User, Pembayaran, Anggota, Jadwal, DetailAnggotaJadwal, TimPengangkut, LaporanSampah, Tamu

admin.site.register(User)
admin.site.register(Pembayaran)
admin.site.register(Anggota)
admin.site.register(Jadwal)
admin.site.register(DetailAnggotaJadwal)
admin.site.register(TimPengangkut)
admin.site.register(LaporanSampah)
admin.site.register(Tamu)
