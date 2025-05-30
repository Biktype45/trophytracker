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
        'date_joined', 'last_trophy_sync'
    ]
    
    search_fields = ['username', 'psn_id', 'email', 'first_name', 'last_name']
    
    readonly_fields = [
        'total_trophy_score', 'current_trophy_level', 'level_progress_percentage',
        'bronze_count', 'silver_count', 'gold_count', 'platinum_count',
        'last_login', 'date_joined', 'profile_updated'
    ]
    
    # Fieldsets
    fieldsets = BaseUserAdmin.fieldsets + (
        ('PSN Integration', {
            'fields': (
                'psn_id', 'psn_avatar_url', 'psn_account_id',
                'last_trophy_sync', 'allow_trophy_sync'
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
        return format_html(
            '<span style="color: {}; font-weight: bold;">Level {}: {}</span>',
            color, obj.current_trophy_level, level_name
        )
    get_trophy_level_display.short_description = 'Trophy Level'
    
    def get_level_color(self, level):
        """Return color based on trophy level"""
        if level <= 5:
            return '#6c757d'  # Gray
        elif level <= 10:
            return '#28a745'  # Green
        elif level <= 15:
            return '#ffc107'  # Yellow
        else:
            return '#dc3545'  # Red
    
    actions = ['sync_trophy_data', 'recalculate_scores']
    
    def sync_trophy_data(self, request, queryset):
        """Action to sync trophy data for selected users"""
        count = 0
        for user in queryset:
            if user.psn_id and user.allow_trophy_sync:
                # This will be implemented in the PSN API integration
                count += 1
        
        self.message_user(request, f"Queued {count} users for trophy sync.")
    sync_trophy_data.short_description = "Sync trophy data from PSN"
    
    def recalculate_scores(self, request, queryset):
        """Action to recalculate trophy scores for selected users"""
        count = 0
        for user in queryset:
            user.calculate_total_score()
            user.update_trophy_level()
            count += 1
        
        self.message_user(request, f"Recalculated scores for {count} users.")
    recalculate_scores.short_description = "Recalculate trophy scores and levels"

# =============================================================================
# ADMIN SITE CUSTOMIZATION
# =============================================================================

admin.site.site_header = "Trophy Tracker Administration"
admin.site.site_title = "Trophy Tracker Admin" 
admin.site.index_title = "Welcome to Trophy Tracker Administration"

# Add custom CSS for better admin experience
admin.site.enable_nav_sidebar = False  # Disable sidebar for cleaner look
