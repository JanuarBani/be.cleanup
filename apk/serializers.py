from rest_framework import serializers
from .models import *
from django.contrib.auth.hashers import make_password

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
        nama = validated_data.pop("nama")
        jk = validated_data.pop("jk")

        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
            role="tamu"
        )

        Tamu.objects.create(
            nama=nama,
            jk=jk
        )

        return user

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, 
        required=False,
        min_length=8,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'password', 'date_joined', 'is_active']
        read_only_fields = ['id', 'date_joined', 'is_active']
        extra_kwargs = {
            'username': {'required': True},
            'email': {'required': False, 'allow_blank': True},
            'role': {'required': True}
        }
    
    def validate(self, data):
        # Jika create user baru, password wajib
        if self.instance is None and 'password' not in data:
            raise serializers.ValidationError({
                "password": "Password wajib diisi untuk user baru"
            })
        return data
    
    def create(self, validated_data):
        """Create user dengan password ter-hash"""
        password = validated_data.pop('password', None)
        
        # Buat user dulu
        user = User.objects.create(**validated_data)
        
        # Set password dengan hash
        if password:
            user.set_password(password)
            user.save()
        
        return user
    
    def update(self, instance, validated_data):
        """Update user dengan handle password"""
        password = validated_data.pop('password', None)
        
        # Update field lainnya
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Jika ada password baru, hash dan update
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance

class TimPengangkutSerializer(serializers.ModelSerializer):
    # Tambahkan field tambahan jika perlu
    jumlah_anggota = serializers.SerializerMethodField()
    
    class Meta:
        model = TimPengangkut
        fields = ['idTim', 'namaTim', 'noWhatsapp', 'jumlah_anggota']
        read_only_fields = ['idTim']
    
    def get_jumlah_anggota(self, obj):
        # Hitung jumlah anggota dari model terkait
        # Jika ada model Anggota yang berelasi dengan TimPengangkut
        try:
            # Cek apakah ada relasi ke model Anggota
            if hasattr(obj, 'anggota_set'):
                return obj.anggota_set.count()
            elif hasattr(obj, 'anggota'):
                return obj.anggota.count()
            else:
                return 0
        except:
            return 0

class AnggotaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Anggota
        fields = '__all__'

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
            'idUser': {'read_only': True}  # ← FIX PENTING
        }

    def get_foto_bukti_url(self, obj):
        if obj.foto_bukti:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.foto_bukti.url)
            return obj.foto_bukti.url
        return None