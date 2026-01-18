# serializers.py - Tambahkan di akhir file

from rest_framework import serializers
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta
import json

# ============================
#       REPORT SERIALIZERS
# ============================

class ReportDateRangeSerializer(serializers.Serializer):
    """Serializer untuk filter tanggal"""
    start_date = serializers.DateField(required=True)
    end_date = serializers.DateField(required=True)
    
    def validate(self, data):
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("Start date harus sebelum end date")
        
        # Validasi range maksimal 1 tahun
        date_range = (data['end_date'] - data['start_date']).days
        if date_range > 365:
            raise serializers.ValidationError("Range tanggal maksimal 1 tahun")
        
        return data

class ReportStatusFilterSerializer(serializers.Serializer):
    """Serializer untuk filter status"""
    status = serializers.ChoiceField(
        choices=['all', 'active', 'inactive', 'pending', 'completed'],
        default='all'
    )

class ReportSummarySerializer(serializers.Serializer):
    """Serializer untuk summary report"""
    total = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2, allow_null=True)
    average = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    status_counts = serializers.DictField()

class KeuanganSummarySerializer(serializers.Serializer):
    """Ringkasan Laporan Pembayaran"""
    period = serializers.CharField()
    total_pendapatan = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_lunas = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_pending = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_gagal = serializers.DecimalField(max_digits=15, decimal_places=2)
    metode_bayar_stats = serializers.DictField()
    tanggal_generate = serializers.DateTimeField()


class KeuanganTableSerializer(serializers.Serializer):
    """Tabel Pembayaran Anggota"""
    tanggal_bayar = serializers.DateField()
    nama_anggota = serializers.CharField()
    jumlah_bayar = serializers.DecimalField(max_digits=15, decimal_places=2)
    metode_bayar = serializers.CharField()
    status_bayar = serializers.CharField()


class KeuanganReportSerializer(serializers.Serializer):
    info = KeuanganSummarySerializer()
    table = KeuanganTableSerializer(many=True)

    
class AnggotaTableSerializer(serializers.Serializer):
    """Tabel Detail Anggota"""
    nama_anggota = serializers.CharField()
    status = serializers.CharField()
    jenis_sampah = serializers.CharField()
    tanggal_start = serializers.DateField()
    tanggal_end = serializers.DateField(allow_null=True)


class AnggotaSummarySerializer(serializers.Serializer):
    """Ringkasan Laporan Anggota"""
    period = serializers.CharField()
    total_anggota = serializers.IntegerField()
    aktif = serializers.IntegerField()
    non_aktif = serializers.IntegerField()
    akan_expired = serializers.IntegerField()
    baru_bulan_ini = serializers.IntegerField()
    jenis_sampah_stats = serializers.DictField()
    tanggal_generate = serializers.DateTimeField()


class AnggotaReportSerializer(serializers.Serializer):
    info = AnggotaSummarySerializer()
    table = AnggotaTableSerializer(many=True)

class LaporanSampahSummarySerializer(serializers.Serializer):
    """Ringkasan Laporan Sampah"""
    period = serializers.CharField()
    total_laporan = serializers.IntegerField()
    pending = serializers.IntegerField()
    proses = serializers.IntegerField()
    selesai = serializers.IntegerField()
    avg_response_time = serializers.CharField(allow_null=True)
    tanggal_generate = serializers.DateTimeField()


class LaporanSampahTableSerializer(serializers.Serializer):
    """Tabel Detail Laporan Sampah"""
    tanggal_lapor = serializers.DateField()
    nama_pelapor = serializers.CharField()
    alamat = serializers.CharField()
    status = serializers.CharField()


class LaporanSampahReportSerializer(serializers.Serializer):
    info = LaporanSampahSummarySerializer()
    table = LaporanSampahTableSerializer(many=True)

class JadwalSummarySerializer(serializers.Serializer):
    """Ringkasan Laporan Pengangkutan"""
    period = serializers.CharField()
    total_jadwal = serializers.IntegerField()
    total_tim = serializers.IntegerField()
    total_anggota_terjadwal = serializers.IntegerField()
    status_stats = serializers.DictField()
    tanggal_generate = serializers.DateTimeField()

class JadwalAnggotaSerializer(serializers.Serializer):
    tanggal_jadwal = serializers.DateField()
    nama_anggota = serializers.CharField()
    status_pengangkutan = serializers.CharField()

class JadwalPerTimSerializer(serializers.Serializer):
    nama_tim = serializers.CharField()
    total_jadwal = serializers.IntegerField()
    total_anggota = serializers.IntegerField()
    status_stats = serializers.DictField()
    detail = JadwalAnggotaSerializer(many=True)

class JadwalReportSerializer(serializers.Serializer):
    info = JadwalSummarySerializer()
    table = JadwalPerTimSerializer(many=True)


class UserStatTableSerializer(serializers.Serializer):
    username = serializers.CharField()
    email = serializers.EmailField()
    role = serializers.CharField()
    is_active = serializers.BooleanField()
    date_joined = serializers.DateTimeField()

class UserStatSummarySerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    admin_count = serializers.IntegerField()
    anggota_count = serializers.IntegerField()
    tamu_count = serializers.IntegerField()
    tim_angkut_count = serializers.IntegerField()
    active_users = serializers.IntegerField()
    new_users_month = serializers.IntegerField()
    tanggal_generate = serializers.DateTimeField()

class UserStatReportSerializer(serializers.Serializer):
    info = UserStatSummarySerializer()
    table = UserStatTableSerializer(many=True)



class MonthlyReportSerializer(serializers.Serializer):
    """Laporan Bulanan Comprehensive"""
    bulan = serializers.CharField()
    tahun = serializers.IntegerField()
    
    # Keuangan
    total_pendapatan = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_transaksi = serializers.IntegerField()
    
    # Anggota
    total_anggota = serializers.IntegerField()
    anggota_baru = serializers.IntegerField()
    anggota_expired = serializers.IntegerField()
    
    # Layanan
    total_jadwal = serializers.IntegerField()
    anggota_dilayani = serializers.IntegerField()
    success_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    
    # Laporan Sampah
    total_laporan = serializers.IntegerField()
    resolution_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    
    # Summary
    summary = serializers.DictField()
    tanggal_generate = serializers.DateTimeField()

class ExportRequestSerializer(serializers.Serializer):
    """Serializer untuk request export"""
    report_type = serializers.ChoiceField(choices=[
        ('keuangan', 'Laporan Keuangan'),
        ('anggota', 'Laporan Anggota'),
        ('laporan-sampah', 'Laporan Sampah'),
        ('jadwal', 'Laporan Jadwal'),
        ('user-stats', 'Statistik User'),
        ('monthly', 'Laporan Bulanan'),
    ])
    format = serializers.ChoiceField(choices=['pdf', 'excel', 'json'], default='pdf')
    filters = serializers.DictField(required=False, default=dict)