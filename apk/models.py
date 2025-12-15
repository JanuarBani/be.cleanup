from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator

class User(AbstractUser):
    ROLE_CHOICES = (
        ("anggota", "Anggota"),
        ("tim_angkut", "Tim Angkut"),
        ("tamu", "Tamu"),
        ("admin", "Admin"),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="tamu")

    def __str__(self):
        return f"{self.id}, {self.username} ({self.role})"

class TimPengangkut(models.Model):
    idTim = models.AutoField(primary_key=True)
    namaTim = models.CharField(max_length=100, null=False)
    noWhatsapp = models.CharField(max_length=12, null=False)  # Changed to CharField
    
    def __str__(self):
        return self.namaTim

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

class Tamu(models.Model): 
    JK_CHOICES = [
        ('L', 'Laki-laki'),
        ('P', 'Perempuan'),
    ]
    
    idTamu = models.AutoField(primary_key=True)
    idUser = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        default=1)
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

class LaporanSampah(models.Model):
    idLaporan = models.AutoField(primary_key=True)
    nama = models.CharField(max_length=100, null=False)
    tanggal_lapor = models.DateField(null=False)
    alamat = models.TextField(null=False)
    latitude = models.DecimalField(max_digits=17, decimal_places=14, null=False)
    longitude = models.DecimalField(max_digits=18, decimal_places=14, null=False)
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
        default=1,
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
