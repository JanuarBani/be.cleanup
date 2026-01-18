from rest_framework import serializers
from .models import *
from django.contrib.auth.hashers import make_password
from django.db import transaction

class RegisterTamuSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=False)
    nama = serializers.CharField()
    jk = serializers.ChoiceField(choices=[("L", "L"), ("P", "P")])
    
    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username sudah digunakan.")
        return value
    
    def create(self, validated_data):
        from django.db import transaction
        
        with transaction.atomic():
            # 1. Buat User
            user = User.objects.create_user(
                username=validated_data['username'],
                password=validated_data['password'],
                email=validated_data.get('email', ''),
                role='tamu'
            )
            
            # 2. Buat Tamu dengan user tersebut
            tamu = Tamu.objects.create(
                nama=validated_data['nama'],
                jk=validated_data['jk'],
                idUser=user  # Hubungkan ke user baru
            )
            
            return {
                'user': user,
                'tamu': tamu
            }
        
class RegisterAnggotaSerializer(serializers.Serializer):
    # === USER ===
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=False)

    # === ANGGOTA ===
    nama = serializers.CharField()
    alamat = serializers.CharField()
    noWA = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    tanggalStart = serializers.DateField()
    tanggalEnd = serializers.DateField()
    status = serializers.ChoiceField(choices=['aktif', 'non-aktif'])
    jenisSampah = serializers.ChoiceField(
        choices=['Rumah Tangga', 'Tempat Usaha']
    )

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username sudah digunakan")
        return value

    def create(self, validated_data):
        with transaction.atomic():
            # 1️⃣ Buat USER
            user = User.objects.create_user(
                username=validated_data['username'],
                password=validated_data['password'],
                email=validated_data.get('email', ''),
                role='anggota'
            )

            # 2️⃣ Buat ANGGOTA
            anggota = Anggota.objects.create(
                user=user,
                nama=validated_data['nama'],
                alamat=validated_data['alamat'],
                noWA=validated_data['noWA'],
                latitude=validated_data['latitude'],
                longitude=validated_data['longitude'],
                tanggalStart=validated_data['tanggalStart'],
                tanggalEnd=validated_data['tanggalEnd'],
                status=validated_data['status'],
                jenisSampah=validated_data['jenisSampah'],
            )

            return {
                "user": user,
                "anggota": anggota
            }

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=False,
        min_length=8,
        style={'input_type': 'password'}
    )

    def validate_username(self, value):
        qs = User.objects.filter(username=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Username sudah digunakan.")
        return value

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'role',
            'password', 'date_joined', 'is_active'
        ]
        read_only_fields = ['id', 'date_joined', 'is_active']
        extra_kwargs = {
            'username': {'required': True},
            'email': {'required': False, 'allow_blank': True},
            'role': {'required': True}
        }

    def validate(self, data):
        # CREATE → password wajib
        if self.instance is None and not data.get('password'):
            raise serializers.ValidationError({
                "password": "Password wajib diisi untuk user baru"
            })
        return data

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()
        return instance

# serializers.py
class TimPengangkutSerializer(serializers.ModelSerializer):
    """
    Serializer sederhana untuk TimPengangkut.
    Untuk CREATE: kirim {'namaTim': '...', 'noWhatsapp': '...', 'idUser': id}
    Untuk READ: akan tampil {'idTim': ..., 'namaTim': ..., 'noWhatsapp': ..., 'idUser': id}
    """
    class Meta:
        model = TimPengangkut
        fields = ['idTim', 'namaTim', 'noWhatsapp', 'idUser']
        read_only_fields = ['idTim']

class AnggotaSerializer(serializers.ModelSerializer):
    status_jadwal_info = serializers.SerializerMethodField(read_only=True)
    user_info = serializers.SerializerMethodField(read_only=True)  # Tambah field user info
    
    class Meta:
        model = Anggota
        fields = '__all__'
    
    def get_user_info(self, obj):
        """Get user information for anggota"""
        if obj.user:
            return {
                'id': obj.user.id,
                'username': obj.user.username,
                'email': obj.user.email
            }
        return None

    def get_status_jadwal_info(self, obj):
        """Info status jadwal untuk anggota"""
        detail_jadwals = DetailAnggotaJadwal.objects.filter(idAnggota=obj)
        
        total = detail_jadwals.count()
        terjadwal = detail_jadwals.filter(status_pengangkutan='terjadwal').count()
        dibatalkan = detail_jadwals.filter(status_pengangkutan='dibatalkan').count()
        selesai = detail_jadwals.filter(status_pengangkutan='selesai').count()
        
        return {
            'total_jadwal': total,
            'terjadwal': terjadwal,
            'dibatalkan': dibatalkan,
            'selesai': selesai,
            'percentage_terjadwal': f"{(terjadwal/total*100 if total > 0 else 0):.1f}%"
        }
    
    def validate(self, data):
        """Validasi data anggota"""
        # Validasi tanggal
        if 'tanggalStart' in data and 'tanggalEnd' in data:
            if data['tanggalStart'] > data['tanggalEnd']:
                raise serializers.ValidationError({
                    'tanggalEnd': 'Tanggal berakhir harus setelah tanggal mulai'
                })
        
        # Jika status diubah menjadi non-aktif, catat
        if self.instance and 'status' in data:
            if self.instance.status == 'aktif' and data['status'] == 'non-aktif':
                # Status akan diubah ke non-aktif, jadwal akan otomatis dibatalkan oleh signal
                pass
        
        return data

class UpgradeAnggotaSerializer(serializers.Serializer):
    nama = serializers.CharField()
    alamat = serializers.CharField()
    noWA = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    tanggalStart = serializers.DateField()
    tanggalEnd = serializers.DateField()
    status = serializers.CharField()
    jenisSampah = serializers.CharField()

    def create(self, validated_data):
        user = self.context["request"].user

        anggota = Anggota.objects.create(
            user=user,
            **validated_data
        )

        user.role = "anggota"
        user.save()

        return anggota


class TamuSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tamu
        fields = '__all__'

class JadwalSerializer(serializers.ModelSerializer):
    nama_tim = serializers.CharField(source='idTim.namaTim', read_only=True)
    
    class Meta:
        model = Jadwal
        fields = '__all__'

class PembayaranSerializer(serializers.ModelSerializer):
    # Tampilkan nama anggota dari relasi idAnggota
    nama_anggota = serializers.CharField(source='idAnggota.nama', read_only=True)
    
    # URL untuk bukti bayar (jika menggunakan ImageField)
    bukti_bayar_url = serializers.SerializerMethodField()

    class Meta:
        model = Pembayaran
        fields = [
            'idPembayaran',
            'idAnggota',
            'nama_anggota',
            'tanggalBayar',
            'jumlahBayar',
            'metodeBayar',
            'statusBayar',
            'buktiBayar',        # Field asli untuk upload
            'bukti_bayar_url',   # URL untuk display
        ]
        extra_kwargs = {
            'idAnggota': {'required': True},
            'buktiBayar': {'required': False, 'allow_null': True}
        }

    def get_bukti_bayar_url(self, obj):
        if obj.buktiBayar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.buktiBayar.url)
            return obj.buktiBayar.url
        return None
    
    def validate_jumlahBayar(self, value):
        if value <= 0:
            raise serializers.ValidationError("Jumlah bayar harus lebih dari 0")
        return value
    
    def validate_tanggalBayar(self, value):
        from django.utils import timezone
        if value > timezone.now().date():
            raise serializers.ValidationError("Tanggal bayar tidak boleh di masa depan")
        return value


class DetailAnggotaJadwalSerializer(serializers.ModelSerializer):
    nama_anggota = serializers.CharField(source='idAnggota.nama', read_only=True)
    tanggal_jadwal = serializers.DateField(source='idJadwal.tanggalJadwal', read_only=True)
    nama_tim = serializers.CharField(source='idJadwal.idTim.namaTim', read_only=True)
    
    class Meta:
        model = DetailAnggotaJadwal
        fields = '__all__'

class LaporanSampahSerializer(serializers.ModelSerializer):
    nama_user = serializers.CharField(source='idUser.username', read_only=True)
    foto_bukti_url = serializers.SerializerMethodField()

    class Meta:
        model = LaporanSampah
        fields = [
            'idLaporan',
            'nama',
            'tanggal_lapor',
            'alamat',
            'latitude',
            'longitude',
            'deskripsi',
            'foto_bukti',
            'foto_bukti_url',
            'idUser',
            'status',
            'nama_user'
        ]
        extra_kwargs = {
            # HAPUS ini: 'idUser': {'read_only': True} ← HAPUS!
            'idLaporan': {'read_only': True},
            'tanggal_lapor': {'read_only': True},  # Tanggal tidak bisa diubah
        }

    def get_foto_bukti_url(self, obj):
        if obj.foto_bukti:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.foto_bukti.url)
            return obj.foto_bukti.url
        return None
    
    # TAMBAHKAN VALIDASI UNTUK LATITUDE/LONGITUDE
    def validate_latitude(self, value):
        """Validasi latitude"""
        try:
            lat = float(value)
            if not (-90 <= lat <= 90):
                raise serializers.ValidationError("Latitude harus antara -90 dan 90")
            return str(lat)  # Simpan sebagai string untuk DecimalField
        except (ValueError, TypeError):
            raise serializers.ValidationError("Latitude harus berupa angka")
    
    def validate_longitude(self, value):
        """Validasi longitude"""
        try:
            lng = float(value)
            if not (-180 <= lng <= 180):
                raise serializers.ValidationError("Longitude harus antara -180 dan 180")
            return str(lng)  # Simpan sebagai string untuk DecimalField
        except (ValueError, TypeError):
            raise serializers.ValidationError("Longitude harus berupa angka")
    
    def validate(self, data):
        """Validasi tambahan"""
        # Pastikan idUser tidak diubah oleh user biasa
        request = self.context.get('request')
        if request and request.method in ['PUT', 'PATCH']:
            if 'idUser' in data and data['idUser'] != self.instance.idUser:
                # Hanya admin yang bisa mengubah idUser
                if not request.user.is_staff:
                    raise serializers.ValidationError({
                        'idUser': 'Tidak diizinkan mengubah pemilik laporan'
                    })
        return data
    
    def update(self, instance, validated_data):
        """Override update untuk handle idUser dengan benar"""
        # Jika idUser ada di validated_data, update
        # Jika tidak, pertahankan yang lama
        if 'idUser' in validated_data:
            instance.idUser = validated_data.pop('idUser')
        
        return super().update(instance, validated_data)
    
class PushSubscriptionSerializer(serializers.ModelSerializer):

    user_username = serializers.CharField(
        source='user.username',
        read_only=True
    )

    class Meta:
        model = PushSubscription
        fields = ['id', 'endpoint', 'auth', 'p256dh', 'user_username', 'user']
        read_only_fields = ['user']

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None

        subscription, created = PushSubscription.objects.update_or_create(
            endpoint=validated_data['endpoint'],
            defaults={
                'auth': validated_data['auth'],
                'p256dh': validated_data['p256dh'],
                'user': user
            }
        )
        return subscription

class NotificationPayloadSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    body = serializers.CharField(max_length=500)
    icon = serializers.CharField(max_length=200, required=False)
    url = serializers.CharField(max_length=200, required=False)
    type = serializers.CharField(max_length=50, required=False)
    data = serializers.DictField(required=False)

class NotificationSerializer(serializers.ModelSerializer):
    user_type = serializers.CharField(source='user.role', read_only=True)
    
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'notification_type', 'priority', 
                 'read', 'data', 'created_at', 'updated_at', 'user_type']
        read_only_fields = ['created_at', 'updated_at']
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Format tanggal lebih baik
        representation['created_at'] = instance.created_at.isoformat()
        representation['updated_at'] = instance.updated_at.isoformat()
        return representation
