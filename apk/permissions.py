from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated

class PublicReadPermission(BasePermission):
    """Public boleh GET / list / retrieve tanpa login."""
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True  # PUBLIC ACCESS
        return request.user.is_authenticated  # selain GET wajib login

class RolePermission(BasePermission):
    """
    Base: mempermudah membuat aturan role sesuai method.
    """

    role_read = []    # boleh GET
    role_add = []     # boleh POST
    role_edit = []    # boleh PUT/PATCH
    role_delete = []  # boleh DELETE

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        
        method = request.method

        if method in SAFE_METHODS:
            return user.role in self.role_read
        
        if method == "POST":
            return user.role in self.role_add
        
        if method in ["PUT", "PATCH"]:
            return user.role in self.role_edit
        
        if method == "DELETE":
            return user.role in self.role_delete
        
        return False
    
class PermissionTimPengangkut(RolePermission):
    role_read = ["admin", "tim_angkut"]
    role_add = ["admin"]
    role_edit = ["admin", "tim_angkut"]
    role_delete = ["admin"]

class PermissionAnggota(RolePermission):
    role_read = ["admin", "tim_angkut", "anggota"]
    role_add = ["admin", "tamu"]
    role_edit = ["admin", "anggota", "tim_angkut"]
    role_delete = ["admin"]

# permissions.py - Tambah permission khusus
class CanUpdateAnggotaStatus(BasePermission):
    """Permission untuk mengupdate status anggota"""
    
    def has_object_permission(self, request, view, obj):
        # Admin bisa update semua
        if request.user.role == 'admin':
            return True
        
        # Anggota hanya bisa update status mereka sendiri
        if request.user.role == 'anggota' and obj.user == request.user:
            # Anggota hanya bisa mengupdate status mereka ke 'aktif' jika bayar
            if 'status' in request.data:
                return request.data['status'] == 'aktif'
        
        return False

class PermissionTamu(RolePermission):
    role_read = ["admin", "tamu"]
    role_add = ["admin", "tamu"]
    role_edit = ["admin", "tamu"]
    role_delete = ["admin"]

class PermissionJadwal(RolePermission):
    role_read = ["admin", "tim_angkut", "anggota"]
    role_add = ["admin", "anggota"]
    role_edit = ["admin", "tim_angkut", "anggota"]
    role_delete = ["admin"]

class PermissionPembayaran(RolePermission):
    role_read = ["admin", "tim_angkut", "anggota"]
    role_add = ["admin", "anggota"]
    role_edit = ["admin", "tim_angkut", "anggota"]
    role_delete = ["admin"]

class PermissionDetailAnggotaJadwal(RolePermission):
    role_read = ["admin", "tim_angkut", "anggota"]
    role_add = ["admin", "anggota"]
    role_edit = ["admin", "tim_angkut", "anggota"]
    role_delete = ["admin"]

class PermissionLaporanSampah(RolePermission):
    role_read = ["admin", "tim_angkut", "anggota", "tamu"]
    role_add = ["admin", "anggota", "tamu"]
    role_edit = ["admin", "anggota", "tamu", "tim_angkut"]
    role_delete = ["admin"]
