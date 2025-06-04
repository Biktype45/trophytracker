from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Extended user admin with PSN and trophy information"""
    
    # List display
    list_display = [
        'username', 'psn_id', 'get_trophy_level_display', 'total_trophy_score',
        'platinum_count', 'profile_public', 'last_trophy_sync', 'date_joined'
    ]
    
    list_filter = [
        'profile_public', 'current_trophy_level', 'allow_trophy_sync',
        'date_joined', 'last_trophy_sync', 'sync_error_count'
    ]
    
    search_fields = ['username', 'psn_id', 'email', 'first_name', 'last_name']
    
    readonly_fields = [
        'total_trophy_score', 'current_trophy_level', 'level_progress_percentage',
        'bronze_count', 'silver_count', 'gold_count', 'platinum_count',
        'last_login', 'date_joined', 'profile_updated', 'last_sync_attempt',
        'last_successful_sync', 'sync_error_count'
    ]
    
    # Fieldsets - Updated for simplified PSN model
    fieldsets = BaseUserAdmin.fieldsets + (
        ('PSN Integration', {
            'fields': (
                'psn_id', 'psn_avatar_url', 'psn_account_id',
                'allow_trophy_sync'
            )
        }),
        ('Sync Status', {
            'fields': (
                'last_trophy_sync', 'last_sync_attempt', 'last_successful_sync',
                'sync_error_count', 'last_sync_error'
            )
        }),
        ('Trophy Statistics', {
            'fields': (
                'total_trophy_score', 'current_trophy_level', 'level_progress_percentage',
                ('bronze_count', 'silver_count'), 
                ('gold_count', 'platinum_count')
            )
        }),
        ('Profile Settings', {
            'fields': ('profile_public', 'show_rare_trophies')
        }),
    )
    
    def get_trophy_level_display(self, obj):
        """Display trophy level with visual indicator"""
        level_name = obj.get_trophy_level_name()
        color = self.get_level_color(obj.current_trophy_level)
        progress_bar = self.get_progress_bar(obj.level_progress_percentage)
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">Level {}: {}</span><br/>{}<br/><small>{:.1f}% to next level</small>',
            color, obj.current_trophy_level, level_name, progress_bar, obj.level_progress_percentage
        )
    get_trophy_level_display.short_description = 'Trophy Level'
    
    def get_level_color(self, level):
        """Return color based on trophy level"""
        if level <= 5:
            return '#6c757d'  # Gray - Beginner
        elif level <= 10:
            return '#28a745'  # Green - Intermediate
        elif level <= 15:
            return '#ffc107'  # Yellow - Advanced
        else:
            return '#dc3545'  # Red - Elite
    
    def get_progress_bar(self, percentage):
        """Create a visual progress bar"""
        filled = int(percentage / 10)  # 10% per segment
        empty = 10 - filled
        bar = '█' * filled + '░' * empty
        return format_html('<span style="font-family: monospace;">{}</span>', bar)
    
    def get_psn_status(self, obj):
        """Display PSN connection status"""
        if not obj.psn_id:
            return format_html('<span style="color: #dc3545;">❌ Not Connected</span>')
        elif obj.sync_error_count >= 5:
            return format_html('<span style="color: #dc3545;">🔴 Sync Disabled (Errors: {})</span>', obj.sync_error_count)
        elif not obj.allow_trophy_sync:
            return format_html('<span style="color: #ffc107;">⏸️ Sync Disabled</span>')
        else:
            return format_html('<span style="color: #28a745;">✅ Active</span>')
    get_psn_status.short_description = 'PSN Status'
    
    def get_trophy_summary(self, obj):
        """Display trophy counts with icons"""
        return format_html(
            '🥉{} 🥈{} 🥇{} 🏆{}<br/><strong>Total: {}</strong>',
            obj.bronze_count, obj.silver_count, obj.gold_count, obj.platinum_count,
            obj.bronze_count + obj.silver_count + obj.gold_count + obj.platinum_count
        )
    get_trophy_summary.short_description = 'Trophies'
    
    # Add PSN status and trophy summary to list display
    list_display = [
        'username', 'psn_id', 'get_trophy_level_display', 'total_trophy_score',
        'get_trophy_summary', 'get_psn_status', 'last_trophy_sync', 'date_joined'
    ]
    
    actions = ['sync_trophy_data', 'recalculate_scores', 'reset_sync_errors', 'disable_sync', 'enable_sync']
    
    def sync_trophy_data(self, request, queryset):
        """Action to sync trophy data for selected users"""
        from psn_integration.services import PSNAWPService
        
        count = 0
        errors = 0
        
        for user in queryset:
            if user.psn_id and user.allow_trophy_sync and user.sync_error_count < 5:
                try:
                    # Start async sync job
                    psn_service = PSNAWPService()
                    sync_job = psn_service.sync_user_trophies(user, user.psn_id)
                    count += 1
                except Exception as e:
                    user.record_sync_attempt(success=False, error_message=str(e))
                    errors += 1
        
        if count > 0:
            self.message_user(request, f"Started trophy sync for {count} users.")
        if errors > 0:
            self.message_user(request, f"Failed to start sync for {errors} users (check error logs).", level='WARNING')
        if count == 0 and errors == 0:
            self.message_user(request, "No eligible users for sync (check PSN connection and sync settings).", level='WARNING')
    
    sync_trophy_data.short_description = "🔄 Sync trophy data from PSN"
    
    def recalculate_scores(self, request, queryset):
        """Action to recalculate trophy scores for selected users"""
        count = 0
        for user in queryset:
            user.update_all_trophy_data()
            count += 1
        
        self.message_user(request, f"♻️ Recalculated trophy data for {count} users.")
    recalculate_scores.short_description = "♻️ Recalculate trophy scores and levels"
    
    def reset_sync_errors(self, request, queryset):
        """Reset sync error counts for selected users"""
        count = 0
        for user in queryset:
            if user.sync_error_count > 0:
                user.reset_sync_errors()
                count += 1
        
        self.message_user(request, f"🔧 Reset sync errors for {count} users.")
    reset_sync_errors.short_description = "🔧 Reset sync error counts"
    
    def disable_sync(self, request, queryset):
        """Disable trophy sync for selected users"""
        count = queryset.filter(allow_trophy_sync=True).update(allow_trophy_sync=False)
        self.message_user(request, f"⏸️ Disabled trophy sync for {count} users.")
    disable_sync.short_description = "⏸️ Disable trophy sync"
    
    def enable_sync(self, request, queryset):
        """Enable trophy sync for selected users"""
        count = queryset.filter(allow_trophy_sync=False).update(allow_trophy_sync=True)
        self.message_user(request, f"▶️ Enabled trophy sync for {count} users.")
    enable_sync.short_description = "▶️ Enable trophy sync"

# =============================================================================
# ADMIN SITE CUSTOMIZATION
# =============================================================================

admin.site.site_header = "🏆 Trophy Tracker Administration"
admin.site.site_title = "Trophy Tracker Admin" 
admin.site.index_title = "Welcome to Trophy Tracker Administration"

# Add custom CSS for better admin experience
admin.site.enable_nav_sidebar = False  # Disable sidebar for cleaner look