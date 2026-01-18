from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
from django.conf import settings
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

class User(AbstractUser):
    ROLE_CHOICES = (
        ("anggota", "Anggota"),
        ("tim_angkut", "Tim Angkut"),
        ("tamu", "Tamu"),
        ("admin", "Admin"),
    )

    role = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES, default="tamu"
    )

    def __str__(self):
        return f"{self.id}, {self.username} ({self.role})"

class TimPengangkut(models.Model):
    idTim = models.AutoField(primary_key=True)
    namaTim = models.CharField(max_length=100, null=False)
    noWhatsapp = models.CharField(max_length=12, null=False)  # Changed to CharField
    idUser = models.ForeignKey(
        User,
        on_delete=models.CASCADE)
    
    def __str__(self):
        return self.namaTim

# models.py - Simplify the Anggota model (hapus duplicate code)
class Anggota(models.Model):
    JENIS_SAMPAH_CHOICES = [
        ('Rumah Tangga', 'Rumah Tangga'),
        ('Tempat Usaha', 'Tempat Usaha'),
    ]
    STATUS_CHOICES = [
        ('aktif', 'Aktif'),
        ('non-aktif', 'Non-Aktif'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    idAnggota = models.AutoField(primary_key=True)
    nama = models.CharField(max_length=100, null=False)
    alamat = models.TextField(null=False)
    noWA = models.CharField(max_length=12, null=False)
    
    latitude = models.FloatField(null=False)
    longitude = models.FloatField(null=False)
    
    tanggalStart = models.DateField(null=False)
    tanggalEnd = models.DateField(null=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, null=False)
    jenisSampah = models.CharField(max_length=15, choices=JENIS_SAMPAH_CHOICES, null=False)
    
    def __str__(self):
        return self.nama
    
    def save(self, *args, **kwargs):
        # Set status default jika tidak ada
        if not self.status:
            self.status = 'aktif'
        
        super().save(*args, **kwargs)

# class Anggota(models.Model):
#     JENIS_SAMPAH_CHOICES = [
#         ('Rumah Tangga', 'Rumah Tangga'),
#         ('Tempat Usaha', 'Tempat Usaha'),
#     ]
#     STATUS_CHOICES = [
#         ('aktif', 'Aktif'),
#         ('non-aktif', 'Non-Aktif'),
#     ]
    
#     user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
#     idAnggota = models.AutoField(primary_key=True)
#     nama = models.CharField(max_length=100, null=False)
#     alamat = models.TextField(null=False)
#     noWA = models.CharField(max_length=12, null=False)
    
#     latitude = models.FloatField(null=False)
#     longitude = models.FloatField(null=False)
    
#     tanggalStart = models.DateField(null=False)
#     tanggalEnd = models.DateField(null=False)
#     status = models.CharField(max_length=10, choices=STATUS_CHOICES, null=False)
#     jenisSampah = models.CharField(max_length=15, choices=JENIS_SAMPAH_CHOICES, null=False)
    
#     def __str__(self):
#         return self.nama

class Tamu(models.Model): 
    JK_CHOICES = [
        ('L', 'Laki-laki'),
        ('P', 'Perempuan'),
    ]
    
    idTamu = models.AutoField(primary_key=True)
    idUser = models.ForeignKey(
        User,
        on_delete=models.CASCADE)
    nama = models.CharField(max_length=100, null=False)
    jk = models.CharField(max_length=1, choices=JK_CHOICES)
    
    def __str__(self):
        return self.nama

class Jadwal(models.Model):
    idJadwal = models.AutoField(primary_key=True)
    tanggalJadwal = models.DateField(null=False)
    idTim = models.ForeignKey(TimPengangkut, on_delete=models.CASCADE, null=False)
    
    def __str__(self):
        return f"Jadwal {self.tanggalJadwal} - {self.idTim.namaTim}"

class Pembayaran(models.Model):
    STATUS_BAYAR_CHOICES = [
        ('pending', 'Pending'),
        ('lunas', 'Lunas'),
        ('gagal', 'Gagal'),
    ]
    
    idPembayaran = models.AutoField(primary_key=True)
    idAnggota = models.ForeignKey(Anggota, on_delete=models.CASCADE, null=False)
    tanggalBayar = models.DateField(null=False)
    jumlahBayar = models.IntegerField(null=False)
    metodeBayar = models.CharField(max_length=50, null=False)
    statusBayar = models.CharField(max_length=10, choices=STATUS_BAYAR_CHOICES, default='pending')
    buktiBayar = models.ImageField(
        upload_to='bukti_pembayaran/',  # Folder berbeda dengan laporan
        blank=True, 
        null=True,
        verbose_name='Bukti Pembayaran'
    )
    
    def __str__(self):
        return f"Pembayaran {self.idPembayaran} - {self.idAnggota.nama}"

class DetailAnggotaJadwal(models.Model):
    STATUS_PENGANGKUTAN_CHOICES = [
        ('terjadwal', 'Terjadwal'),
        ('dalam_proses', 'Dalam Proses'),
        ('selesai', 'Selesai'),
        ('dibatalkan', 'Dibatalkan'),
    ]
    
    id = models.AutoField(primary_key=True)
    idAnggota = models.ForeignKey(Anggota, on_delete=models.CASCADE, null=False)
    idJadwal = models.ForeignKey(Jadwal, on_delete=models.CASCADE, null=False)
    status_pengangkutan = models.CharField(
        max_length=15, 
        choices=STATUS_PENGANGKUTAN_CHOICES, 
        default='terjadwal'
    )
    catatan = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['idAnggota', 'idJadwal'], 
                name='unique_anggota_jadwal'
            )
        ]
    
    def __str__(self):
        return f"{self.idAnggota.nama} - {self.idJadwal}"
    
    def save(self, *args, **kwargs):
        """Override save untuk handle status berdasarkan anggota"""
        # Jika anggota tidak aktif, otomatis batalkan jadwal
        if self.idAnggota.status == 'non-aktif' and self.status_pengangkutan != 'dibatalkan':
            self.status_pengangkutan = 'dibatalkan'
            if not self.catatan:
                self.catatan = f"Status pengangkutan dibatalkan karena anggota non-aktif (ID: {self.idAnggota.idAnggota})"
        super().save(*args, **kwargs)

# class DetailAnggotaJadwal(models.Model):
#     STATUS_PENGANGKUTAN_CHOICES = [
#         ('terjadwal', 'Terjadwal'),
#         ('dalam_proses', 'Dalam Proses'),
#         ('selesai', 'Selesai'),
#         ('dibatalkan', 'Dibatalkan'),
#     ]
    
#     id = models.AutoField(primary_key=True)
#     idAnggota = models.ForeignKey(Anggota, on_delete=models.CASCADE, null=False)
#     idJadwal = models.ForeignKey(Jadwal, on_delete=models.CASCADE, null=False)
#     status_pengangkutan = models.CharField(
#         max_length=15, 
#         choices=STATUS_PENGANGKUTAN_CHOICES, 
#         default='terjadwal'
#     )
#     catatan = models.TextField(blank=True, null=True)
#     created_at = models.DateTimeField(auto_now_add=True)
    
#     class Meta:
#         constraints = [
#             models.UniqueConstraint(
#                 fields=['idAnggota', 'idJadwal'], 
#                 name='unique_anggota_jadwal'
#             )
#         ]
    
#     def __str__(self):
#         return f"{self.idAnggota.nama} - {self.idJadwal}"

class LaporanSampah(models.Model):
    idLaporan = models.AutoField(primary_key=True)
    nama = models.CharField(max_length=100, null=False)
    tanggal_lapor = models.DateField(auto_now_add=True)
    alamat = models.TextField(null=False)
    latitude = models.FloatField(null=False)
    longitude = models.FloatField(null=False)
    deskripsi = models.TextField(null=False)
    
    # Foto bukti
    foto_bukti = models.ImageField(
        upload_to='laporan_fotos/', 
        blank=True, 
        null=True,
        verbose_name='Foto Bukti'
    )
    
    # Ganti idAnggota → idUser mengacu ke model User kustom
    idUser = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="laporan_sampah"
    )

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('proses', 'Proses'),
        ('selesai', 'Selesai'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
    )

    def __str__(self):
        return f"Laporan {self.idLaporan} - {self.nama}"

    class Meta:
        db_table = 'laporan_sampah'


class PushSubscription(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='push_subscriptions'
    )
    endpoint = models.URLField(max_length=500)
    auth = models.CharField(max_length=100)
    p256dh = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        username = self.user.username if self.user else 'Anonymous'
        return f"self.id : {username} - {self.endpoint[:50]}..."
    
    def to_dict(self):
        """Convert to dictionary format for webpush"""
        return {
            'endpoint': self.endpoint,
            'keys': {
                'p256dh': self.p256dh,
                'auth': self.auth
            }
        }
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['endpoint'],
                name='unique_push_subscription_endpoint'
            )
        ]

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('payment', 'Pembayaran'),
        ('report', 'Laporan Sampah'),
        ('schedule', 'Jadwal'),
        ('user', 'Pengguna'),
        ('alert', 'Peringatan'),
        ('system', 'Sistem'),
        ('test', 'Test'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Rendah'),
        ('normal', 'Normal'),
        ('high', 'Tinggi'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='system')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    read = models.BooleanField(default=False)
    url = models.CharField(
        max_length=500, 
        blank=True, 
        null=True,
        verbose_name='URL Tujuan'
    )
    data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'read', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    def mark_as_read(self):
        self.read = True
        self.save()
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'type': self.notification_type,
            'priority': self.priority,
            'read': self.read,
            'url': self.url,
            'data': self.data,
            'created_at': self.created_at.isoformat(),
            'user_type': self.user.role,
        }


@receiver(post_save, sender=Anggota)
def update_detail_jadwal_on_status_change(sender, instance, created, **kwargs):
    """
    Signal untuk handle perubahan status anggota
    Tanpa circular import
    """
    if created:
        return  # Skip untuk instance baru
    
    try:
        # Dapatkan instance sebelumnya
        old_instance = Anggota.objects.get(pk=instance.pk)
    except Anggota.DoesNotExist:
        return
    
    # Cek perubahan status
    if old_instance.status != instance.status:
        if instance.status == 'non-aktif':
            # Non-aktifkan semua detail jadwal
            detail_jadwals = DetailAnggotaJadwal.objects.filter(idAnggota=instance)
            
            # Update status menjadi 'dibatalkan'
            detail_jadwals.update(status_pengangkutan='dibatalkan')
            
            # Update catatan untuk setiap detail
            for detail in detail_jadwals:
                detail.catatan = f"Status pengangkutan dibatalkan karena anggota non-aktif (ID: {instance.idAnggota})"
                detail.save()
                
            print(f"✅ Semua jadwal untuk anggota {instance.nama} telah dinon-aktifkan")
            
        elif instance.status == 'aktif':
            # Aktifkan kembali detail jadwal yang masih valid
            detail_jadwals = DetailAnggotaJadwal.objects.filter(
                idAnggota=instance,
                status_pengangkutan='dibatalkan'
            )
            
            # Aktifkan kembali jadwal yang masih di masa depan
            today = timezone.now().date()
            reactivated_count = 0
            
            for detail in detail_jadwals:
                if detail.idJadwal.tanggalJadwal >= today:
                    detail.status_pengangkutan = 'terjadwal'
                    detail.catatan = f"Status pengangkutan diaktifkan kembali (ID Anggota: {instance.idAnggota})"
                    detail.save()
                    reactivated_count += 1
            
            print(f"✅ {reactivated_count} jadwal untuk anggota {instance.nama} telah diaktifkan kembali")