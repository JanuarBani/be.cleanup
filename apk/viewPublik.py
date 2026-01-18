from django.utils import timezone
from datetime import datetime, timedelta, date
from collections import Counter
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
import traceback
import logging
from .models import LaporanSampah

# Setup logger
logger = logging.getLogger(__name__)

class PublicDampakLingkunganView(APIView):
    """
    View publik untuk analisis dampak lingkungan
    Tidak memerlukan autentikasi/token
    """
    
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            logger.info("📢 PublicDampakLingkunganView accessed")
            
            # Default periode: 30 hari terakhir
            end_date = timezone.now().date()
            # start_date = end_date - timedelta(days=470)
            start_date = date(2023, 1, 1)
            
            # Bisa juga menerima parameter dari query string
            # if 'days' in request.GET:
            #     try:
            #         days = int(request.GET.get('days'))
            #         start_date = end_date - timedelta(days=days)
            #     except ValueError:
            #         pass
            
            logger.info(f"📅 Periode: {start_date} sampai {end_date}")
            
            # Query data laporan sampah - TANPA SLICE DI SINI
            try:
                # Query dasar tanpa slicing
                base_query = LaporanSampah.objects.filter(
                    tanggal_lapor__range=[start_date, end_date]
                )
                
                # Hitung total sebelum slicing
                total_laporan = base_query.count()
                logger.info(f"📊 Total laporan dalam periode: {total_laporan}")
                
                # Untuk analisis, gunakan slicing
                laporan_qs = base_query.order_by('-tanggal_lapor')[:1000]
                logger.info(f"📊 Laporan untuk analisis: {len(laporan_qs)} dari {total_laporan}")
                
            except Exception as query_error:
                logger.error(f"❌ Query error: {str(query_error)}")
                return Response({
                    'error': 'Gagal mengambil data dari database',
                    'detail': str(query_error)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            if total_laporan == 0:
                logger.info("ℹ️ Tidak ada data laporan ditemukan")
                return Response({
                    'message': 'Tidak ada data laporan sampah dalam periode ini',
                    'period': {
                        'start_date': start_date.strftime('%Y-%m-%d'),
                        'end_date': end_date.strftime('%Y-%m-%d'),
                        'label': f"30 Hari Terakhir"
                    },
                    'data': {
                        'analisis_dampak_lingkungan': [],
                        'wilayah_terkotor': [],
                        'wilayah_terbersih': [],
                        'ringkasan': {
                            'total_laporan': 0,
                            'pesan': 'Data akan tampil setelah ada laporan dari masyarakat'
                        }
                    }
                })
            
            # Hitung laporan selesai dari QUERY UTAMA (bukan dari sliced)
            try:
                laporan_selesai = base_query.filter(status='selesai').count()
                logger.info(f"✅ Laporan selesai: {laporan_selesai} dari {total_laporan}")
            except Exception as e:
                logger.warning(f"⚠️ Tidak bisa hitung laporan selesai: {str(e)}")
                laporan_selesai = 0
            
            # Hitung persentase
            persentase_selesai = round((laporan_selesai / total_laporan * 100), 1) if total_laporan > 0 else 0
            
            # 1. Analisis Dampak Lingkungan Berdasarkan Jenis Sampah
            try:
                analisis_dampak = self.analisis_dampak_lingkungan_publik(laporan_qs)
                logger.info(f"✅ Analisis dampak berhasil: {len(analisis_dampak.get('detail', []))} jenis")
            except Exception as analisis_error:
                logger.error(f"❌ Analisis error: {str(analisis_error)}")
                traceback.print_exc()
                analisis_dampak = {
                    'detail': [],
                    'total_jenis': 0,
                    'total_berbahaya': 0,
                    'status_lingkungan': 'data_terbatas'
                }
            
            # 2. 5 Wilayah Terkotor
            try:
                wilayah_terkotor = self.wilayah_terkotor_publik(laporan_qs)[:5]
                logger.info(f"✅ Wilayah terkotor berhasil: {len(wilayah_terkotor)} wilayah")
            except Exception as wilayah_error:
                logger.error(f"❌ Wilayah terkotor error: {str(wilayah_error)}")
                traceback.print_exc()
                wilayah_terkotor = []
            
            # 3. 5 Wilayah Terbersih
            try:
                wilayah_terbersih = self.wilayah_terbersih_publik(laporan_qs)[:5]
                logger.info(f"✅ Wilayah terbersih berhasil: {len(wilayah_terbersih)} wilayah")
            except Exception as wilayah_error:
                logger.error(f"❌ Wilayah terbersih error: {str(wilayah_error)}")
                traceback.print_exc()
                wilayah_terbersih = []
            
            # Prepare response data
            data = {
                'period': {
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'label': f"{start_date.strftime('%d %b %Y')} - {end_date.strftime('%d %b %Y')}",
                    'total_hari': (end_date - start_date).days + 1
                },
                'ringkasan': {
                    'total_laporan': total_laporan,
                    'laporan_selesai': laporan_selesai,
                    'persentase_selesai': persentase_selesai,
                    'update_terakhir': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                },
                'analisis_dampak_lingkungan': analisis_dampak,
                'wilayah_terkotor': wilayah_terkotor,
                'wilayah_terbersih': wilayah_terbersih,
                'tips_lingkungan': self.tips_lingkungan(analisis_dampak)
            }
            
            logger.info("✅ PublicDampakLingkunganView selesai")
            return Response(data)
            
        except Exception as e:
            # Print error detail ke terminal Django
            logger.error("="*60)
            logger.error("❌ ERROR in PublicDampakLingkunganView.get():")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error message: {str(e)}")
            logger.error("Traceback:")
            logger.error(traceback.format_exc())
            logger.error("="*60)
            
            # Return error yang friendly untuk publik
            return Response({
                'error': 'Terjadi kesalahan dalam mengambil data',
                'detail': str(e),
                'debug': 'Cek logs di terminal Django'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def identifikasi_jenis_sampah_publik(self, laporan):
        """
        Identifikasi jenis sampah sederhana untuk publik
        Berdasarkan deskripsi atau field jenis_sampah jika ada
        """
        try:
            # Prioritas 1: Field jenis_sampah jika ada
            if hasattr(laporan, 'jenis_sampah') and laporan.jenis_sampah:
                return str(laporan.jenis_sampah)
            
            # Prioritas 2: Analisis deskripsi
            if hasattr(laporan, 'deskripsi') and laporan.deskripsi:
                deskripsi = str(laporan.deskripsi).lower()
                
                # Keyword matching sederhana
                keywords = {
                    'plastik': [
                        'plastik', 'botol', 'botol plastik', 'kresek', 'kantong plastik',
                        'kemasan', 'bungkus plastik', 'plastik botol', 'sachet', 'saset',
                        'sedotan', 'sendok plastik', 'gelas plastik',
                        'mika', 'styrofoam', 'foam', 'plastik bening',
                        'galon', 'tutup botol', 'pipet'
                    ],

                    'organik': [
                        'organik', 'sisa makanan', 'makanan',
                        'daun', 'ranting', 'rumput',
                        'sayur', 'buah', 'kulit buah', 'kulit pisang',
                        'sisa dapur', 'sampah dapur',
                        'nasi', 'lauk', 'tulang',
                        'ampas kopi', 'ampas teh',
                        'ikan', 'daging'
                    ],

                    'kertas': [
                        'kertas', 'koran', 'majalah',
                        'kardus', 'karton', 'dus',
                        'bungkus', 'bungkus kertas',
                        'buku', 'buku tulis',
                        'nota', 'struk', 'brosur',
                        'pamflet', 'arsip'
                    ],

                    'logam': [
                        'logam', 'besi', 'besi tua',
                        'kaleng', 'kaleng minuman',
                        'aluminium', 'alumunium',
                        'tembaga', 'kuningan',
                        'baja', 'seng',
                        'paku', 'kawat',
                        'onderdil', 'sparepart'
                    ],

                    'kaca': [
                        'kaca', 'beling', 'pecahan kaca',
                        'botol kaca', 'gelas',
                        'toples', 'cermin',
                        'lampu', 'bohlam'
                    ],

                    'limbah_berbahaya': [
                        'baterai', 'aki', 'accu',
                        'elektronik', 'e-waste', 'limbah elektronik',
                        'limbah b3', 'b3',
                        'berbahaya', 'racun', 'kimia',
                        'oli', 'minyak mesin',
                        'cat', 'tiner',
                        'pestisida', 'aerosol'
                    ],

                    'campuran': [
                        'campur', 'campuran',
                        'beragam', 'macam-macam',
                        'bercampur', 'campur aduk',
                        'acak', 'tidak dipilah'
                    ],

                    'konstruksi': [
                        'bangunan', 'konstruksi',
                        'puing', 'puing bangunan',
                        'semen', 'pasir', 'kerikil',
                        'batu', 'batako', 'bata',
                        'genteng', 'beton',
                        'keramik', 'ubin',
                        'kayu', 'papan'
                    ],

                    'medis': [
                        'medis', 'limbah medis',
                        'suntik', 'jarum', 'jarum suntik',
                        'infus', 'selang infus',
                        'obat', 'obat kadaluarsa',
                        'farmasi',
                        'masker medis',
                        'sarung tangan medis',
                        'perban', 'kapas'
                    ],

                    'lainnya': [
                        'lainnya', 'lain-lain',
                        'umum', 'tidak diketahui',
                        'misc'
                    ]
                    };
                
                for jenis, kata_kunci in keywords.items():
                    for kata in kata_kunci:
                        if kata in deskripsi:
                            return jenis
                
                return 'lainnya'
            
            return 'tidak_diketahui'
            
        except Exception as e:
            logger.warning(f"⚠️ Gagal identifikasi jenis sampah: {str(e)}")
            return 'tidak_diketahui'
    
    def get_dampak_lingkungan_publik(self, jenis_sampah):
        """
        Dampak lingkungan berdasarkan jenis sampah (versi sederhana untuk publik)
        """
        dampak_map = {
            'plastik': 'Pencemaran tanah dan air, butuh ratusan tahun terurai',
            'organik': 'Gas metana, bau tidak sedap, tapi bisa dikompos',
            'kertas': 'Penggunaan air tinggi untuk produksi, bisa didaur ulang',
            'logam': 'Pencemaran tanah, butuh energi besar untuk daur ulang',
            'kaca': 'Tidak terurai, bisa melukai, tapi bisa didaur ulang utuh',
            'limbah_berbahaya': 'Racun bagi manusia dan ekosistem, bahaya jangka panjang',
            'campuran': 'Sulit didaur ulang, memerlukan pemilahan',
            'konstruksi': 'Volume besar, bisa menyumbat saluran air',
            'medis': 'Risiko infeksi dan penyebaran penyakit',
            'lainnya': 'Dampak bervariasi tergantung komposisi',
            'tidak_diketahui': 'Dampak tidak dapat diidentifikasi'
        }
        
        return dampak_map.get(jenis_sampah, 'Dampak lingkungan sedang')
    
    def get_tingkat_bahaya_publik(self, jenis_sampah):
        """
        Tingkat bahaya untuk publik
        """
        tingkat_tinggi = ['limbah_berbahaya', 'medis']
        tingkat_menengah = ['logam', 'kaca', 'campuran']
        tingkat_rendah = ['plastik', 'organik', 'kertas', 'konstruksi', 'lainnya', 'tidak_diketahui']
        
        if jenis_sampah in tingkat_tinggi:
            return 'tinggi'
        elif jenis_sampah in tingkat_menengah:
            return 'menengah'
        else:
            return 'rendah'
    
    def get_rekomendasi_sederhana(self, jenis_sampah):
        """
        Rekomendasi sederhana untuk publik
        """
        rekomendasi_map = {
            'plastik': 'Kurangi penggunaan, pilah untuk daur ulang',
            'organik': 'Komposkan di rumah atau TPS organik',
            'kertas': 'Kumpulkan untuk didaur ulang',
            'logam': 'Bawa ke pengepul logam bekas',
            'kaca': 'Hati-hati saat membuang, kumpulkan utuh',
            'limbah_berbahaya': 'Bawa ke drop point khusus B3',
            'campuran': 'Pilah terlebih dahulu sebelum dibuang',
            'konstruksi': 'Hubungi pengangkut sampah konstruksi',
            'medis': 'Jangan buang sembarangan, berikan ke fasilitas kesehatan',
            'lainnya': 'Periksa aturan pembuangan di wilayah Anda',
            'tidak_diketahui': 'Laporkan ke petugas kebersihan'
        }
        
        return rekomendasi_map.get(jenis_sampah, 'Konsultasikan dengan petugas kebersihan')
    
    def get_ikon_jenis(self, jenis_sampah):
        """
        Ikon untuk jenis sampah
        """
        ikon_map = {
            'plastik': '♻️',
            'organik': '🍃',
            'kertas': '📄',
            'logam': '🔩',
            'kaca': '🥃',
            'limbah_berbahaya': '⚠️',
            'campuran': '🗑️',
            'konstruksi': '🏗️',
            'medis': '🏥',
            'lainnya': '📦',
            'tidak_diketahui': '❓'
        }
        
        return ikon_map.get(jenis_sampah, '📊')
    
    def get_warna_jenis(self, jenis_sampah):
        """
        Warna untuk jenis sampah
        """
        warna_map = {
            'plastik': '#ff6b6b',
            'organik': '#51cf66',
            'kertas': '#339af0',
            'logam': '#ff922b',
            'kaca': '#94d82d',
            'limbah_berbahaya': '#ff4757',
            'campuran': '#868e96',
            'konstruksi': '#7950f2',
            'medis': '#e64980',
            'lainnya': '#adb5bd',
            'tidak_diketahui': '#ced4da'
        }
        
        return warna_map.get(jenis_sampah, '#868e96')
    
    def analisis_dampak_lingkungan_publik(self, queryset):
        """
        Analisis dampak lingkungan versi sederhana untuk publik
        """
        try:
            # Konversi queryset menjadi list jika sudah sliced
            if hasattr(queryset, '_result_cache'):
                laporan_list = queryset
            else:
                laporan_list = list(queryset)
            
            # Klasifikasi jenis sampah
            klasifikasi = {}
            for laporan in laporan_list:
                try:
                    jenis = self.identifikasi_jenis_sampah_publik(laporan)
                    if jenis not in klasifikasi:
                        klasifikasi[jenis] = {
                            'jumlah': 0,
                            'dampak': '',
                            'ikon': self.get_ikon_jenis(jenis),
                            'warna': self.get_warna_jenis(jenis)
                        }
                    klasifikasi[jenis]['jumlah'] += 1
                except Exception as e:
                    logger.warning(f"⚠️ Gagal proses laporan {getattr(laporan, 'idLaporan', 'unknown')}: {str(e)}")
                    continue
            
            total = sum(item['jumlah'] for item in klasifikasi.values())
            
            # Format hasil
            hasil = []
            for jenis, data in klasifikasi.items():
                persentase = round((data['jumlah'] / total * 100), 1) if total > 0 else 0
                hasil.append({
                    'jenis': jenis,
                    'jumlah': data['jumlah'],
                    'persentase': persentase,
                    'dampak_lingkungan': self.get_dampak_lingkungan_publik(jenis),
                    'rekomendasi_sederhana': self.get_rekomendasi_sederhana(jenis),
                    'ikon': data['ikon'],
                    'warna': data['warna'],
                    'tingkat_bahaya': self.get_tingkat_bahaya_publik(jenis)
                })
            
            # Urutkan berdasarkan jumlah terbanyak
            hasil.sort(key=lambda x: x['jumlah'], reverse=True)
            
            # Hitung total dampak
            total_berbahaya = sum(1 for item in hasil if item['tingkat_bahaya'] == 'tinggi')
            
            return {
                'detail': hasil[:10],  # Tampilkan 10 jenis teratas
                'total_jenis': len(hasil),
                'total_berbahaya': total_berbahaya,
                'status_lingkungan': self.get_status_lingkungan(total_berbahaya, total)
            }
        except Exception as e:
            logger.error(f"❌ Error in analisis_dampak_lingkungan_publik: {str(e)}")
            raise
    
    def identifikasi_wilayah_publik(self, laporan):
        """
        Identifikasi wilayah sederhana untuk publik
        """
        try:
            # Prioritas 1: Field wilayah jika ada
            if hasattr(laporan, 'wilayah') and laporan.wilayah:
                return str(laporan.wilayah)
            
            # Prioritas 2: Bagian dari alamat
            if hasattr(laporan, 'alamat') and laporan.alamat:
                alamat = str(laporan.alamat)
                # Coba ambil 2 kata pertama sebagai identifikasi wilayah
                words = alamat.split()
                if len(words) >= 2:
                    return ' '.join(words[:2])
                else:
                    return alamat
            
            # Prioritas 3: Koordinat grid
            if hasattr(laporan, 'latitude') and hasattr(laporan, 'longitude'):
                try:
                    lat = float(laporan.latitude)
                    lon = float(laporan.longitude)
                    # Bulatkan untuk privacy dan grouping
                    return f"Area {round(lat, 3)},{round(lon, 3)}"
                except (ValueError, TypeError):
                    pass
            
            return 'Lokasi Tidak Diketahui'
        except Exception as e:
            logger.warning(f"⚠️ Error identifikasi wilayah: {str(e)}")
            return 'Lokasi Tidak Jelas'
    
    def wilayah_terkotor_publik(self, queryset):
        """
        5 Wilayah terkotor untuk publik
        """
        try:
            # Konversi queryset menjadi list
            if hasattr(queryset, '_result_cache'):
                laporan_list = queryset
            else:
                laporan_list = list(queryset)
            
            # Kelompokkan berdasarkan wilayah sederhana
            wilayah_counter = {}
            
            for laporan in laporan_list:
                try:
                    # Coba ambil informasi wilayah dari alamat atau koordinat
                    wilayah = self.identifikasi_wilayah_publik(laporan)
                    
                    if wilayah not in wilayah_counter:
                        wilayah_counter[wilayah] = {
                            'total': 0,
                            'selesai': 0,
                            'alamat_terakhir': '',
                            'tanggal_terakhir': None
                        }
                    
                    wilayah_counter[wilayah]['total'] += 1
                    
                    # Gunakan getattr untuk menghindari error jika field tidak ada
                    if getattr(laporan, 'status', None) == 'selesai':
                        wilayah_counter[wilayah]['selesai'] += 1
                    
                    # Update info terakhir
                    alamat = getattr(laporan, 'alamat', '')
                    wilayah_counter[wilayah]['alamat_terakhir'] = str(alamat)[:30] if alamat else 'Tidak ada alamat'
                    
                    tanggal_lapor = getattr(laporan, 'tanggal_lapor', None)
                    if tanggal_lapor:
                        wilayah_counter[wilayah]['tanggal_terakhir'] = tanggal_lapor.strftime('%d-%m-%Y')
                        
                except Exception as e:
                    logger.warning(f"⚠️ Gagal proses wilayah untuk laporan {getattr(laporan, 'idLaporan', 'unknown')}: {str(e)}")
                    continue
            
            # Hitung skor kekotoran (semakin tinggi total, semakin kotor)
            hasil = []
            for wilayah, data in wilayah_counter.items():
                if data['total'] > 0:
                    skor_kotor = data['total'] * 2  # Bobot untuk total laporan
                    if data['selesai'] > 0:
                        # Kurangi skor jika banyak yang selesai
                        skor_kotor -= data['selesai']
                    
                    hasil.append({
                        'wilayah': wilayah,
                        'total_laporan': data['total'],
                        'laporan_selesai': data['selesai'],
                        'persentase_selesai': round((data['selesai'] / data['total'] * 100), 1),
                        'alamat_terakhir': data['alamat_terakhir'],
                        'tanggal_terakhir': data['tanggal_terakhir'],
                        'skor_kotor': skor_kotor
                    })
            
            # Urutkan dari terkotor (skor tertinggi)
            hasil.sort(key=lambda x: x['skor_kotor'], reverse=True)
            
            # Tambahkan ranking dan kategori
            for i, item in enumerate(hasil[:5]):
                item['peringkat'] = i + 1
                item['kategori'] = self.get_kategori_kotor(item['skor_kotor'])
            
            return hasil[:5]
        except Exception as e:
            logger.error(f"❌ Error in wilayah_terkotor_publik: {str(e)}")
            return []
    
    def wilayah_terbersih_publik(self, queryset):
        """
        5 Wilayah terbersih untuk publik
        """
        try:
            # Konversi queryset menjadi list
            if hasattr(queryset, '_result_cache'):
                laporan_list = queryset
            else:
                laporan_list = list(queryset)
            
            # Kelompokkan berdasarkan wilayah sederhana
            wilayah_counter = {}
            
            for laporan in laporan_list:
                try:
                    wilayah = self.identifikasi_wilayah_publik(laporan)
                    
                    if wilayah not in wilayah_counter:
                        wilayah_counter[wilayah] = {
                            'total': 0,
                            'selesai': 0,
                            'alamat_terakhir': '',
                            'tanggal_terakhir': None
                        }
                    
                    wilayah_counter[wilayah]['total'] += 1
                    
                    if getattr(laporan, 'status', None) == 'selesai':
                        wilayah_counter[wilayah]['selesai'] += 1
                    
                    alamat = getattr(laporan, 'alamat', '')
                    wilayah_counter[wilayah]['alamat_terakhir'] = str(alamat)[:30] if alamat else 'Tidak ada alamat'
                    
                    tanggal_lapor = getattr(laporan, 'tanggal_lapor', None)
                    if tanggal_lapor:
                        wilayah_counter[wilayah]['tanggal_terakhir'] = tanggal_lapor.strftime('%d-%m-%Y')
                        
                except Exception as e:
                    logger.warning(f"⚠️ Gagal proses wilayah untuk laporan {getattr(laporan, 'idLaporan', 'unknown')}: {str(e)}")
                    continue
            
            # Hitung skor kebersihan (semakin rendah total, semakin bersih)
            hasil = []
            for wilayah, data in wilayah_counter.items():
                if data['total'] > 0:
                    # Skor kebersihan: persentase selesai minus total laporan
                    persentase_selesai = (data['selesai'] / data['total'] * 100) if data['total'] > 0 else 0
                    skor_bersih = persentase_selesai - (data['total'] * 0.5)  # Total laporan mengurangi skor
                    
                    hasil.append({
                        'wilayah': wilayah,
                        'total_laporan': data['total'],
                        'laporan_selesai': data['selesai'],
                        'persentase_selesai': round(persentase_selesai, 1),
                        'alamat_terakhir': data['alamat_terakhir'],
                        'tanggal_terakhir': data['tanggal_terakhir'],
                        'skor_bersih': skor_bersih
                    })
            
            # Urutkan dari terbersih (skor tertinggi)
            hasil.sort(key=lambda x: x['skor_bersih'], reverse=True)
            
            # Tambahkan ranking dan kategori
            for i, item in enumerate(hasil[:5]):
                item['peringkat'] = i + 1
                item['kategori'] = self.get_kategori_bersih(item['skor_bersih'])
            
            return hasil[:5]
        except Exception as e:
            logger.error(f"❌ Error in wilayah_terbersih_publik: {str(e)}")
            return []
    
    def get_status_lingkungan(self, total_berbahaya, total_laporan):
        """
        Status lingkungan keseluruhan
        """
        if total_laporan == 0:
            return 'data_terbatas'
        
        persentase_berbahaya = (total_berbahaya / total_laporan * 100) if total_laporan > 0 else 0
        
        if persentase_berbahaya > 10:
            return 'perhatian'
        elif persentase_berbahaya > 5:
            return 'waspada'
        else:
            return 'baik'
    
    def get_kategori_kotor(self, skor):
        """
        Kategori kekotoran
        """
        if skor > 50:
            return 'Sangat Kotor'
        elif skor > 30:
            return 'Kotor'
        elif skor > 15:
            return 'Cukup Kotor'
        else:
            return 'Sedang'
    
    def get_kategori_bersih(self, skor):
        """
        Kategori kebersihan
        """
        if skor > 50:
            return 'Sangat Bersih'
        elif skor > 30:
            return 'Bersih'
        elif skor > 15:
            return 'Cukup Bersih'
        else:
            return 'Sedang'
    
    def tips_lingkungan(self, analisis_dampak):
        """
        Tips lingkungan berdasarkan analisis
        """
        tips = [
            "Pilah sampah organik dan non-organik di rumah",
            "Kurangi penggunaan plastik sekali pakai",
            "Gunakan tas belanja reusable",
            "Daur ulang kertas, plastik, dan logam",
            "Buat kompos dari sampah organik"
        ]
        
        # Tambahkan tips khusus berdasarkan jenis sampah dominan
        try:
            if analisis_dampak.get('detail'):
                jenis_dominan = analisis_dampak['detail'][0]['jenis']
                if jenis_dominan == 'plastik':
                    tips.append("Gunakan botol minum reusable, hindari air kemasan")
                elif jenis_dominan == 'limbah_berbahaya':
                    tips.append("Bawa limbah B3 ke drop point khusus, jangan buang sembarangan")
        except:
            pass
        
        return tips[:5]  # Maksimal 5 tips


# Versi SIMPLE untuk landing page (tidak butuh query database)
class PublicLandingPageView(APIView):
    """
    View SUPER SEDERHANA untuk landing page
    Hanya menampilkan statistik ringkas
    """
    
    permission_classes = [AllowAny]

    def get(self, request):
        # Data dummy/stub untuk landing page
        # Dalam implementasi nyata, bisa diambil dari cache atau database ringkas
        
        data = {
            'last_update': timezone.now().strftime('%d %B %Y'),
            'statistics': {
                'total_laporan_30hari': 1500,
                'wilayah_tercover': 45,
                'rata_penyelesaian': '72%',
                'sampah_terkelola': '85 ton'
            },
            'top_issues': [
                {'jenis': 'plastik', 'persentase': '35%', 'ikon': '♻️'},
                {'jenis': 'organik', 'persentase': '28%', 'ikon': '🍃'},
                {'jenis': 'campuran', 'persentase': '20%', 'ikon': '🗑️'},
                {'jenis': 'kertas', 'persentase': '12%', 'ikon': '📄'},
                {'jenis': 'lainnya', 'persentase': '5%', 'ikon': '📊'}
            ],
            'wilayah_performa': {
                'terbersih': ['Kebon Jeruk', 'Menteng', 'Senayan', 'Kuningan', 'Sudirman'],
                'terkotor': ['Pasar Minggu', 'Tanjung Priok', 'Cakung', 'Duren Sawit', 'Kebayoran Lama']
            },
            'call_to_action': {
                'title': 'Laporkan Sampah di Sekitarmu',
                'description': 'Bantu kami menjaga lingkungan dengan melaporkan timbunan sampah',
                'button_text': 'Buat Laporan'
            },
            'features': [
                'Analisis dampak lingkungan real-time',
                'Monitoring wilayah terkotor & terbersih',
                'Tips pengelolaan sampah harian',
                'Progress penanganan transparan'
            ]
        }
        
        return Response(data)