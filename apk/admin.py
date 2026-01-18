# admin.py - OPSI 1: Hapus jenis_sampah
from django.contrib import admin
from django.utils.html import format_html
from .models import User, Pembayaran, Anggota, Jadwal, DetailAnggotaJadwal, TimPengangkut, LaporanSampah, Tamu, PushSubscription, Notification
from .utils.notifications import NotificationService

# Register basic models without custom admin
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'is_active')
    list_filter = ('role', 'is_active')
    search_fields = ('username', 'email')

@admin.register(Anggota)
class AnggotaAdmin(admin.ModelAdmin):
    list_display = ('nama', 'user', 'alamat', 'noWA')
    search_fields = ('nama', 'alamat')

@admin.register(Jadwal)
class JadwalAdmin(admin.ModelAdmin):
    list_display = ('idJadwal', 'tanggalJadwal', 'idTim')
    list_filter = ('tanggalJadwal',)
    search_fields = ('idTim__namaTim',)

@admin.register(TimPengangkut)
class TimPengangkutAdmin(admin.ModelAdmin):
    list_display = ('namaTim', 'noWhatsapp')
    search_fields = ('namaTim',)

@admin.register(LaporanSampah)
class LaporanSampahAdmin(admin.ModelAdmin):
    list_display = ('nama', 'tanggal_lapor', 'status', 'idUser')  # Hapus jenis_sampah dan volume
    list_filter = ('status',)  # Hapus 'jenis_sampah' dari list_filter
    search_fields = ('nama', 'alamat')

@admin.register(Tamu)
class TamuAdmin(admin.ModelAdmin):
    list_display = ('nama', 'jk', 'idUser')
    search_fields = ('nama',)

# PushSubscription Admin
@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'endpoint_short', 'created_at')
    search_fields = ('user__username', 'endpoint')
    list_filter = ('created_at', 'user__role')
    
    def endpoint_short(self, obj):
        return obj.endpoint[:50] + '...' if len(obj.endpoint) > 50 else obj.endpoint
    endpoint_short.short_description = 'Endpoint'

# Pembayaran Admin dengan notification
@admin.register(Pembayaran)
class PembayaranAdmin(admin.ModelAdmin):
    list_display = ('idAnggota', 'jumlahBayar', 'statusBayar', 'tanggalBayar', 'bukti_bayar_preview')
    list_filter = ('statusBayar', 'tanggalBayar')
    search_fields = ('idAnggota__nama', 'idPembayaran')
    
    def bukti_bayar_preview(self, obj):
        if obj.buktiBayar:
            return format_html('<img src="{}" width="50" height="50" />', obj.buktiBayar.url)
        return "No Image"
    bukti_bayar_preview.short_description = 'Bukti Bayar'
    
    actions = ['send_status_notification']
    
    def send_status_notification(self, request, queryset):
        """Admin action to send payment status notification"""
        for pembayaran in queryset:
            NotificationService.send_payment_status_update(pembayaran)
        self.message_user(request, f"Notifications sent for {queryset.count()} payments")
    send_status_notification.short_description = "Send status notification to anggota"

# DetailAnggotaJadwal Admin dengan notification
@admin.register(DetailAnggotaJadwal)
class DetailAnggotaJadwalAdmin(admin.ModelAdmin):
    list_display = ('idAnggota', 'idJadwal', 'status_pengangkutan', 'created_at')
    list_filter = ('status_pengangkutan', 'idJadwal__tanggalJadwal')
    search_fields = ('idAnggota__nama', 'idJadwal__idJadwal')
    
    actions = ['send_status_notification']
    
    def send_status_notification(self, request, queryset):
        """Admin action to send pickup status notification"""
        for detail in queryset:
            NotificationService.send_pickup_status_update(detail)
        self.message_user(request, f"Notifications sent for {queryset.count()} pickups")
    send_status_notification.short_description = "Send status notification to anggota"

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title_short', 'notification_type', 'priority', 'read_status', 'created_at')
    list_filter = ('notification_type', 'priority', 'read', 'created_at')
    search_fields = ('title', 'message', 'user__username')
    list_per_page = 20
    
    def title_short(self, obj):
        return obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
    title_short.short_description = 'Title'
    
    def read_status(self, obj):
        if obj.read:
            return format_html('<span class="badge bg-success">✓ Read</span>')
        else:
            return format_html('<span class="badge bg-warning">● Unread</span>')
    read_status.short_description = 'Status'
    
    actions = ['mark_as_read', 'mark_as_unread', 'send_test_notification']
    
    def mark_as_read(self, request, queryset):
        updated = queryset.update(read=True)
        self.message_user(request, f"{updated} notifications marked as read")
    mark_as_read.short_description = "Mark selected as read"
    
    def mark_as_unread(self, request, queryset):
        updated = queryset.update(read=False)
        self.message_user(request, f"{updated} notifications marked as unread")
    mark_as_unread.short_description = "Mark selected as unread"
    
    def send_test_notification(self, request, queryset):
        """Send test push notifications"""
        from .utils.notifications import NotificationService
        
        for notification in queryset:
            # Kirim push notification ke user
            NotificationService.send_notification_to_user(
                user=notification.user,
                title=f"[Test Admin] {notification.title}",
                body=f"Admin test: {notification.message}",
                notification_type='test',
                url='/admin/',
                data={'admin_test': True, 'original_id': notification.id}
            )
        
        self.message_user(request, f"Test push notifications sent for {queryset.count()} notifications")
    send_test_notification.short_description = "Send test push notifications"