# =============================================================================
# File: psn_integration/admin.py
# Admin interface for PSN Integration
# =============================================================================

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import PSNToken, PSNSyncLog

@admin.register(PSNToken)
class PSNTokenAdmin(admin.ModelAdmin):
    """Admin interface for PSN tokens"""
    
    list_display = [
        'user', 'psn_online_id', 'psn_account_id', 
        'is_active', 'token_status', 'last_sync_display', 
        'sync_errors', 'created_at'
    ]
    
    list_filter = [
        'is_active', 'created_at', 'last_sync'
    ]
    
    search_fields = [
        'user__username', 'psn_online_id', 'psn_account_id'
    ]
    
    readonly_fields = [
        'user', 'psn_account_id', 'psn_online_id', 
        'created_at', 'updated_at', 'token_status'
    ]
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'psn_online_id', 'psn_account_id', 'psn_avatar_url')
        }),
        ('Token Status', {
            'fields': ('is_active', 'token_status', 'expires_at', 'scope')
        }),
        ('Sync Information', {
            'fields': ('last_sync', 'sync_errors')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def token_status(self, obj):
        """Display token expiration status"""
        if obj.is_expired():
            return format_html(
                '<span style="color: red; font-weight: bold;">⚠️ Expired</span>'
            )
        else:
            time_left = obj.expires_at - timezone.now()
            hours_left = int(time_left.total_seconds() // 3600)
            return format_html(
                '<span style="color: green;">✅ Valid ({} hours left)</span>',
                hours_left
            )
    token_status.short_description = 'Token Status'
    
    def last_sync_display(self, obj):
        """Display last sync time"""
        if obj.last_sync:
            return obj.last_sync.strftime('%Y-%m-%d %H:%M')
        return "Never"
    last_sync_display.short_description = 'Last Sync'
    
    actions = ['deactivate_tokens', 'activate_tokens']
    
    def deactivate_tokens(self, request, queryset):
        """Deactivate selected tokens"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} tokens deactivated.')
    deactivate_tokens.short_description = 'Deactivate selected tokens'
    
    def activate_tokens(self, request, queryset):
        """Activate selected tokens"""
        updated = queryset.update(is_active=True, sync_errors=0)
        self.message_user(request, f'{updated} tokens activated.')
    activate_tokens.short_description = 'Activate selected tokens'

@admin.register(PSNSyncLog)
class PSNSyncLogAdmin(admin.ModelAdmin):
    """Admin interface for PSN sync logs"""
    
    list_display = [
        'user', 'sync_type', 'status_display', 'games_processed', 
        'trophies_updated', 'new_trophies_earned', 'duration_display', 
        'started_at'
    ]
    
    list_filter = [
        'sync_type', 'status', 'started_at'
    ]
    
    search_fields = [
        'user__username', 'error_message'
    ]
    
    readonly_fields = [
        'user', 'started_at', 'completed_at', 'duration_seconds',
        'duration_display'
    ]
    
    fieldsets = (
        ('Sync Information', {
            'fields': ('user', 'sync_type', 'status')
        }),
        ('Statistics', {
            'fields': (
                'games_processed', 'trophies_updated', 'new_trophies_earned'
            )
        }),
        ('Timing', {
            'fields': ('started_at', 'completed_at', 'duration_display')
        }),
        ('Results', {
            'fields': ('error_message', 'sync_data'),
            'classes': ('collapse',)
        }),
    )
    
    def status_display(self, obj):
        """Display status with color coding"""
        colors = {
            'started': 'blue',
            'success': 'green',
            'partial': 'orange',
            'failed': 'red'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def duration_display(self, obj):
        """Display sync duration"""
        return obj.get_duration_display()
    duration_display.short_description = 'Duration'
    
    # Don't allow adding/editing sync logs through admin
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False