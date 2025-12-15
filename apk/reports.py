# views/reports.py - VERSI DENGAN DATA ASLI DARI DATABASE
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from datetime import datetime, timedelta
import json
from .models import (
    Pembayaran, Anggota, LaporanSampah, Jadwal, 
    TimPengangkut, DetailAnggotaJadwal  # PASTIKAN DetailAnggotaJadwal diimport
)

from .report import UserStatReportSerializer

# Import models
from django.contrib.auth.models import User
from apk.models import (
    Pembayaran, Anggota, LaporanSampah, Jadwal, 
    TimPengangkut, DetailAnggotaJadwal
)

class ReportViewSet(APIView):
    """Base class untuk semua reports"""
    permission_classes = [IsAuthenticated]
    
    def check_admin_permission(self, request):
        """Check if user is admin"""
        if not hasattr(request.user, 'role') or request.user.role != 'admin':
            raise PermissionDenied("Hanya admin yang bisa mengakses laporan")
        return True
    
    def format_period(self, start_date, end_date):
        """Format period string"""
        return f"{start_date.strftime('%d/%m/%Y')} s/d {end_date.strftime('%d/%m/%Y')}"

class KeuanganReportView(ReportViewSet):
    """View untuk laporan keuangan dengan data asli"""
    
    def post(self, request):
        try:
            self.check_admin_permission(request)
            
            # Validasi input
            start_date = request.data.get('start_date')
            end_date = request.data.get('end_date')
            
            if not start_date or not end_date:
                return Response({'error': 'start_date dan end_date diperlukan'}, status=400)
            
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Format tanggal tidak valid. Gunakan YYYY-MM-DD'}, status=400)
            
            # Query data pembayaran dari database
            pembayaran_qs = Pembayaran.objects.filter(
                tanggalBayar__range=[start_date, end_date]
            )
            
            # Hitung statistics dari data asli
            total_pendapatan = pembayaran_qs.filter(statusBayar='lunas').aggregate(
                total=Sum('jumlahBayar')
            )['total'] or 0
            
            total_pending = pembayaran_qs.filter(statusBayar='pending').aggregate(
                total=Sum('jumlahBayar')
            )['total'] or 0
            
            total_lunas = pembayaran_qs.filter(statusBayar='lunas').count()
            total_gagal = pembayaran_qs.filter(statusBayar='gagal').count()
            
            # Statistik metode bayar dari data asli
            metode_bayar_stats = {}
            metode_qs = pembayaran_qs.values('metodeBayar').annotate(
                count=Count('idPembayaran'),
                total=Sum('jumlahBayar')
            )
            
            for item in metode_qs:
                metode = item['metodeBayar'] or 'Tidak diketahui'
                metode_bayar_stats[metode] = {
                    'count': item['count'],
                    'total': float(item['total'] or 0)
                }
            
            # Prepare response data
            data = {
                'period': self.format_period(start_date, end_date),
                'total_pendapatan': float(total_pendapatan),
                'total_pending': float(total_pending),
                'total_lunas': total_lunas,
                'total_gagal': total_gagal,
                'metode_bayar_stats': metode_bayar_stats,
                'tanggal_generate': timezone.now()
            }
            
            return Response(data)
            
        except PermissionDenied as e:
            return Response({'error': str(e)}, status=403)
        except Exception as e:
            return Response({'error': f'Internal server error: {str(e)}'}, status=500)

class AnggotaReportView(ReportViewSet):
    """View untuk laporan anggota dengan data asli"""
    
    def post(self, request):
        try:
            self.check_admin_permission(request)
            
            # Validasi input
            start_date = request.data.get('start_date')
            end_date = request.data.get('end_date')
            
            if not start_date or not end_date:
                return Response({'error': 'start_date dan end_date diperlukan'}, status=400)
            
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Format tanggal tidak valid. Gunakan YYYY-MM-DD'}, status=400)
            
            # Query data anggota dari database
            anggota_qs = Anggota.objects.filter(
                tanggalStart__range=[start_date, end_date]
            )
            
            # Hitung statistics dari data asli
            total_anggota = anggota_qs.count()
            aktif = anggota_qs.filter(status='aktif').count()
            non_aktif = anggota_qs.filter(status='non-aktif').count()
            
            # Akan expired dalam 30 hari (dari semua anggota, bukan hanya periode)
            today = timezone.now().date()
            future_30 = today + timedelta(days=30)
            akan_expired = Anggota.objects.filter(
                status='aktif',
                tanggalEnd__range=[today, future_30]
            ).count()
            
            # Anggota baru bulan ini (dari semua anggota)
            bulan_ini_start = today.replace(day=1)
            baru_bulan_ini = Anggota.objects.filter(
                tanggalStart__gte=bulan_ini_start
            ).count()
            
            # Statistik jenis sampah dari data asli
            jenis_sampah_stats = {}
            jenis_qs = anggota_qs.values('jenisSampah').annotate(
                count=Count('idAnggota')
            )
            
            for item in jenis_qs:
                jenis = item['jenisSampah'] or 'Tidak diketahui'
                jenis_sampah_stats[jenis] = item['count']
            
            # Prepare response data
            data = {
                'period': self.format_period(start_date, end_date),
                'total_anggota': total_anggota,
                'aktif': aktif,
                'non_aktif': non_aktif,
                'akan_expired': akan_expired,
                'baru_bulan_ini': baru_bulan_ini,
                'jenis_sampah_stats': jenis_sampah_stats,
                'tanggal_generate': timezone.now()
            }
            
            return Response(data)
            
        except PermissionDenied as e:
            return Response({'error': str(e)}, status=403)
        except Exception as e:
            return Response({'error': f'Internal server error: {str(e)}'}, status=500)

class LaporanSampahReportView(ReportViewSet):
    """View untuk laporan sampah dengan data asli"""
    
    def post(self, request):
        try:
            self.check_admin_permission(request)
            
            # Validasi input
            start_date = request.data.get('start_date')
            end_date = request.data.get('end_date')
            
            if not start_date or not end_date:
                return Response({'error': 'start_date dan end_date diperlukan'}, status=400)
            
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Format tanggal tidak valid. Gunakan YYYY-MM-DD'}, status=400)
            
            # Query data laporan sampah dari database
            laporan_qs = LaporanSampah.objects.filter(
                tanggal_lapor__range=[start_date, end_date]
            )
            
            # Hitung statistics dari data asli
            total_laporan = laporan_qs.count()
            pending = laporan_qs.filter(status='pending').count()
            proses = laporan_qs.filter(status='proses').count()
            selesai = laporan_qs.filter(status='selesai').count()
            
            # Hitung rata-rata waktu respons untuk laporan selesai
            avg_response_time = None
            laporan_selesai = laporan_qs.filter(status='selesai')
            if laporan_selesai.exists():
                # Asumsi: ada field tanggal_selesai atau menggunakan tanggal update terakhir
                # Untuk sekarang, kita hitung dari tanggal_lapor ke sekarang
                total_days = 0
                for laporan in laporan_selesai:
                    days_diff = (timezone.now().date() - laporan.tanggal_lapor).days
                    total_days += max(days_diff, 0)  # Jaga agar tidak negatif
                
                if total_days > 0:
                    avg_days = total_days / laporan_selesai.count()
                    avg_response_time = f"{avg_days:.1f} hari"
            
            # Top 10 pelapor dari data asli
            top_pelapor = []
            top_pelapor_qs = laporan_qs.values(
                'idUser__username', 
                'idUser__email'
            ).annotate(
                count=Count('idLaporan')
            ).order_by('-count')[:10]
            
            for item in top_pelapor_qs:
                top_pelapor.append({
                    'username': item['idUser__username'] or 'Tidak diketahui',
                    'email': item['idUser__email'] or '',
                    'jumlah_laporan': item['count']
                })
            
            # Prepare response data
            data = {
                'period': self.format_period(start_date, end_date),
                'total_laporan': total_laporan,
                'pending': pending,
                'proses': proses,
                'selesai': selesai,
                'avg_response_time': avg_response_time,
                'top_pelapor': top_pelapor,
                'tanggal_generate': timezone.now()
            }
            
            return Response(data)
            
        except PermissionDenied as e:
            return Response({'error': str(e)}, status=403)
        except Exception as e:
            return Response({'error': f'Internal server error: {str(e)}'}, status=500)

class JadwalReportView(ReportViewSet):
    """View untuk laporan jadwal dengan data asli"""
    
    def post(self, request):
        try:
            self.check_admin_permission(request)
            
            # Validasi input
            start_date = request.data.get('start_date')
            end_date = request.data.get('end_date')
            
            if not start_date or not end_date:
                return Response({'error': 'start_date dan end_date diperlukan'}, status=400)
            
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Format tanggal tidak valid. Gunakan YYYY-MM-DD'}, status=400)
            
            # Query data jadwal dari database
            jadwal_qs = Jadwal.objects.filter(
                tanggalJadwal__range=[start_date, end_date]
            )
            
            # Hitung statistics dari data asli
            total_jadwal = jadwal_qs.count()
            total_tim = TimPengangkut.objects.count()
            
            # Total anggota terjadwal dalam periode
            total_anggota_terjadwal = DetailAnggotaJadwal.objects.filter(
                idJadwal__tanggalJadwal__range=[start_date, end_date]
            ).count()
            
            # Statistik status pengangkutan dari data asli
            status_stats = {}
            status_qs = DetailAnggotaJadwal.objects.filter(
                idJadwal__tanggalJadwal__range=[start_date, end_date]
            ).values('status_pengangkutan').annotate(
                count=Count('id')
            )
            
            for item in status_qs:
                status = item['status_pengangkutan'] or 'Tidak diketahui'
                status_stats[status] = item['count']
            
            # Top 5 tim pengangkut dari data asli
            top_tim = []
            top_tim_qs = jadwal_qs.values(
                'idTim__namaTim'
            ).annotate(
                jadwal_count=Count('idJadwal'),
                anggota_count=Count('detailanggotajadwal')
            ).order_by('-anggota_count')[:5]
            
            for item in top_tim_qs:
                top_tim.append({
                    'nama_tim': item['idTim__namaTim'] or 'Tidak diketahui',
                    'jumlah_jadwal': item['jadwal_count'],
                    'anggota_dilayani': item['anggota_count']
                })
            
            # Prepare response data
            data = {
                'period': self.format_period(start_date, end_date),
                'total_jadwal': total_jadwal,
                'total_tim': total_tim,
                'total_anggota_terjadwal': total_anggota_terjadwal,
                'status_stats': status_stats,
                'top_tim': top_tim,
                'tanggal_generate': timezone.now()
            }
            
            return Response(data)
            
        except PermissionDenied as e:
            return Response({'error': str(e)}, status=403)
        except Exception as e:
            return Response({'error': f'Internal server error: {str(e)}'}, status=500)

class UserStatReportView(ReportViewSet):
    """View untuk statistik user dengan data asli"""
    
    def get(self, request):
        try:
            # PERBAIKAN: Gunakan permission check yang lebih sederhana
            if not request.user.is_authenticated:
                return Response({'error': 'Silakan login terlebih dahulu'}, status=401)
            
            # Cek permission dengan cara yang lebih aman
            if hasattr(request.user, 'role'):
                # Model User custom dengan field role
                if request.user.role != 'admin':
                    return Response({'error': 'Hanya admin yang bisa mengakses laporan'}, status=403)
            else:
                # Model User standar
                if not request.user.is_superuser and not request.user.is_staff:
                    return Response({'error': 'Hanya admin yang bisa mengakses laporan'}, status=403)
            
            # PERBAIKAN PENTING: Gunakan get_user_model()
            User = get_user_model()
            
            # Query data user dari database
            total_users = User.objects.count()
            admin_count = User.objects.filter(role='admin').count()
            anggota_count = User.objects.filter(role='anggota').count()
            tamu_count = User.objects.filter(role='tamu').count()
            tim_angkut_count = User.objects.filter(role='tim_angkut').count()
            active_users = User.objects.filter(is_active=True).count()
            
            # User baru bulan ini dari database
            today = timezone.now().date()
            bulan_ini_start = today.replace(day=1)
            new_users_month = User.objects.filter(
                date_joined__date__gte=bulan_ini_start
            ).count()
            
            # Serialize data
            serializer = UserStatReportSerializer({
                'total_users': total_users,
                'admin_count': admin_count,
                'anggota_count': anggota_count,
                'tamu_count': tamu_count,
                'tim_angkut_count': tim_angkut_count,
                'active_users': active_users,
                'new_users_month': new_users_month,
                'tanggal_generate': timezone.now()
            })
            
            return Response(serializer.data)
            
        except Exception as e:
            # Log error untuk debugging
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error in UserStatReportView: {e}")
            print(f"Traceback: {error_trace}")
            
            return Response({
                'error': f'Internal server error: {str(e)}',
                'detail': 'Silakan coba lagi nanti atau hubungi administrator'
            }, status=500)

class MonthlyReportView(ReportViewSet):
    """View untuk laporan bulanan dengan data asli"""
  
    def post(self, request):
        try:
            self.check_admin_permission(request)
          
            # Validasi input
            month = request.data.get('month')
            year = request.data.get('year')
            
            if not month or not year:
                return Response({'error': 'month dan year diperlukan'}, status=400)
            
            try:
                month = int(month)
                year = int(year)
                
                if month < 1 or month > 12:
                    return Response({'error': 'Month harus antara 1-12'}, status=400)
                
                if year < 2000 or year > 2100:
                    return Response({'error': 'Year tidak valid'}, status=400)
                    
            except ValueError:
                return Response({'error': 'Month dan year harus angka'}, status=400)
            
            # Hitung range tanggal untuk bulan tersebut
            start_date = datetime(year, month, 1).date()
            if month == 12:
                end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
            
            # Get data keuangan untuk bulan ini
            keuangan_data = self.get_keuangan_data(start_date, end_date)
            
            # Get data anggota untuk bulan ini
            anggota_data = self.get_anggota_data(start_date, end_date)
            
            # Get data jadwal untuk bulan ini
            jadwal_data = self.get_jadwal_data(start_date, end_date)
            
            # Get data laporan sampah untuk bulan ini
            laporan_data = self.get_laporan_data(start_date, end_date)
            
            # Hitung success rate (simplified)
            total_services = jadwal_data.get('total_anggota_terjadwal', 0)
            completed_services = DetailAnggotaJadwal.objects.filter(
                idJadwal__tanggalJadwal__range=[start_date, end_date],
                status_pengangkutan='selesai'
            ).count()
            
            success_rate = (completed_services / total_services * 100) if total_services > 0 else 0
            
            # Hitung resolution rate
            total_reports = laporan_data.get('total_laporan', 0)
            completed_reports = laporan_data.get('selesai', 0)
            resolution_rate = (completed_reports / total_reports * 100) if total_reports > 0 else 0
            
            # PERBAIKAN: Gunakan get_user_model() untuk menghitung user
            User = get_user_model()
            
            # Nama bulan
            month_names = [
                'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
                'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
            ]
            
            # Prepare response data
            data = {
                'bulan': f"{month_names[month-1]} {year}",
                'tahun': year,
                'total_pendapatan': float(keuangan_data.get('total_pendapatan', 0)),
                'total_transaksi': keuangan_data.get('total_lunas', 0),
                'total_anggota': anggota_data.get('total_anggota', 0),
                'anggota_baru': anggota_data.get('baru_bulan_ini', 0),
                'anggota_expired': anggota_data.get('akan_expired', 0),
                'total_jadwal': jadwal_data.get('total_jadwal', 0),
                'anggota_dilayani': jadwal_data.get('total_anggota_terjadwal', 0),
                'success_rate': round(success_rate, 2),
                'total_laporan': laporan_data.get('total_laporan', 0),
                'resolution_rate': round(resolution_rate, 2),
                'summary': {
                    'pendapatan_per_anggota': round(
                        float(keuangan_data.get('total_pendapatan', 0)) / 
                        max(anggota_data.get('aktif', 1), 1), 
                        2
                    ),
                    'laporan_per_user': round(
                        laporan_data.get('total_laporan', 0) / 
                        max(User.objects.count(), 1),  # PERBAIKAN DI SINI
                        2
                    ),
                    'efficiency_rate': round(
                        (success_rate + resolution_rate) / 2, 
                        2
                    ) if total_reports > 0 else 0
                },
                'tanggal_generate': timezone.now()
            }
            
            # OPTIONAL: Gunakan serializer jika mau
            # from .serializers import MonthlyReportSerializer
            # serializer = MonthlyReportSerializer(data)
            # return Response(serializer.data)
            
            return Response(data)
            
        except PermissionDenied as e:
            return Response({'error': str(e)}, status=403)
        except Exception as e:
            # Debug: print error detail
            import traceback
            print(f"Error in MonthlyReportView: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            return Response({'error': f'Internal server error: {str(e)}'}, status=500)
    
    def get_keuangan_data(self, start_date, end_date):
        """Get keuangan data for period"""
        pembayaran_qs = Pembayaran.objects.filter(
            tanggalBayar__range=[start_date, end_date]
        )
        
        # PERBAIKAN: Gunakan proper aggregation
        aggregation = pembayaran_qs.filter(statusBayar='lunas').aggregate(
            total_pendapatan=Sum('jumlahBayar')
        )
        
        total_pendapatan = aggregation['total_pendapatan'] or 0
        total_lunas = pembayaran_qs.filter(statusBayar='lunas').count()
        
        return {
            'total_pendapatan': total_pendapatan,
            'total_lunas': total_lunas
        }
    
    def get_anggota_data(self, start_date, end_date):
        """Get anggota data for period"""
        anggota_qs = Anggota.objects.all()
        
        today = timezone.now().date()
        future_30 = today + timedelta(days=30)
        
        return {
            'total_anggota': anggota_qs.count(),
            'aktif': anggota_qs.filter(status='aktif').count(),
            'baru_bulan_ini': Anggota.objects.filter(
                tanggalStart__range=[start_date, end_date]
            ).count(),
            'akan_expired': Anggota.objects.filter(
                status='aktif',
                tanggalEnd__range=[today, future_30]
            ).count()
        }
    
    def get_jadwal_data(self, start_date, end_date):
        """Get jadwal data for period"""
        jadwal_qs = Jadwal.objects.filter(
            tanggalJadwal__range=[start_date, end_date]
        )
        
        total_anggota_terjadwal = DetailAnggotaJadwal.objects.filter(
            idJadwal__tanggalJadwal__range=[start_date, end_date]
        ).count()
        
        return {
            'total_jadwal': jadwal_qs.count(),
            'total_anggota_terjadwal': total_anggota_terjadwal
        }
    
    def get_laporan_data(self, start_date, end_date):
        """Get laporan data for period"""
        laporan_qs = LaporanSampah.objects.filter(
            tanggal_lapor__range=[start_date, end_date]
        )
        
        return {
            'total_laporan': laporan_qs.count(),
            'selesai': laporan_qs.filter(status='selesai').count()
        }

class ExportReportView(ReportViewSet):
    """View untuk export laporan ke berbagai format"""
    
    def post(self, request):
        try:
            self.check_admin_permission(request)
            
            # Validasi input
            report_type = request.data.get('report_type')
            format_type = request.data.get('format', 'json')
            filters = request.data.get('filters', {})
            
            if not report_type:
                return Response({'error': 'report_type diperlukan'}, status=400)
            
            # Dispatch ke report generator yang sesuai
            if report_type == 'keuangan':
                view = KeuanganReportView()
                view.request = request
                return view.post(request)
            elif report_type == 'anggota':
                view = AnggotaReportView()
                view.request = request
                return view.post(request)
            elif report_type == 'laporan-sampah':
                view = LaporanSampahReportView()
                view.request = request
                return view.post(request)
            elif report_type == 'jadwal':
                view = JadwalReportView()
                view.request = request
                return view.post(request)
            elif report_type == 'user-stats':
                view = UserStatReportView()
                view.request = request
                return view.get(request)
            elif report_type == 'monthly':
                view = MonthlyReportView()
                view.request = request
                return view.post(request)
            else:
                return Response({'error': 'Jenis report tidak valid'}, status=400)
            
        except PermissionDenied as e:
            return Response({'error': str(e)}, status=403)
        except Exception as e:
            return Response({'error': f'Internal server error: {str(e)}'}, status=500)