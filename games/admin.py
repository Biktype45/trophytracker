from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Avg, Count
from .models import Game, GameDifficultyRating

class GameDifficultyRatingInline(admin.TabularInline):
    """Inline admin for difficulty ratings"""
    model = GameDifficultyRating
    extra = 0
    readonly_fields = ['user', 'difficulty_rating', 'created_at']
    can_delete = False

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    """Admin interface for games"""
    
    list_display = [
        'title', 'platform', 'get_difficulty_display', 'get_total_trophies',
        'completion_rate', 'players_count', 'admin_verified', 'last_synced'
    ]
    
    list_filter = [
        'platform', 'difficulty_multiplier', 'admin_verified', 
        'has_trophy_groups', 'created_at'
    ]
    
    search_fields = ['title', 'np_communication_id', 'np_title_id', 'description']
    
    readonly_fields = [
        'np_communication_id', 'trophy_set_version', 'completion_rate',
        'community_difficulty_rating', 'difficulty_rating_count',
        'created_at', 'updated_at', 'last_synced'
    ]
    
    fieldsets = (
        ('Game Information', {
            'fields': (
                'title', 'description', 'platform', 'icon_url'
            )
        }),
        ('PlayStation API Data', {
            'fields': (
                'np_communication_id', 'np_title_id', 'np_service_name',
                'trophy_set_version', 'has_trophy_groups'
            )
        }),
        ('Trophy Counts', {
            'fields': (
                ('bronze_count', 'silver_count'),
                ('gold_count', 'platinum_count')
            )
        }),
        ('Difficulty System', {
            'fields': (
                'difficulty_multiplier', 'admin_verified',
                'community_difficulty_rating', 'difficulty_rating_count'
            )
        }),
        ('Statistics', {
            'fields': (
                'completion_rate', 'players_count', 
                'created_at', 'updated_at', 'last_synced'
            )
        }),
    )
    
    inlines = [GameDifficultyRatingInline]
    
    def get_difficulty_display(self, obj):
        """Display difficulty with color coding"""
        category = obj.get_difficulty_category()
        color = self.get_difficulty_color(obj.difficulty_multiplier)
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}x - {}</span>',
            color, obj.difficulty_multiplier, category
        )
    get_difficulty_display.short_description = 'Difficulty'
    
    def get_difficulty_color(self, multiplier):
        """Return color based on difficulty multiplier"""
        if multiplier <= 1.5:
            return '#28a745'  # Green (Easy)
        elif multiplier <= 3.0:
            return '#ffc107'  # Yellow (Standard)
        elif multiplier <= 6.0:
            return '#fd7e14'  # Orange (Challenging)
        else:
            return '#dc3545'  # Red (Extreme)
    
    def get_total_trophies(self, obj):
        """Display total trophy count"""
        total = obj.get_total_trophy_count()
        return format_html(
            '<span title="Bronze: {} | Silver: {} | Gold: {} | Platinum: {}">{} trophies</span>',
            obj.bronze_count, obj.silver_count, obj.gold_count, obj.platinum_count, total
        )
    get_total_trophies.short_description = 'Total Trophies'
    
    actions = ['verify_difficulty', 'update_from_psn', 'calculate_max_scores']
    
    def verify_difficulty(self, request, queryset):
        """Mark games as admin verified"""
        updated = queryset.update(admin_verified=True)
        self.message_user(request, f"Verified {updated} games.")
    verify_difficulty.short_description = "Mark as admin verified"
    
    def update_from_psn(self, request, queryset):
        """Update game data from PSN API"""
        # This will be implemented in PSN API integration
        count = queryset.count()
        self.message_user(request, f"Queued {count} games for PSN update.")
    update_from_psn.short_description = "Update from PSN API"
    
    def calculate_max_scores(self, request, queryset):
        """Calculate and display max possible scores"""
        for game in queryset:
            max_score = game.calculate_max_possible_score()
            self.message_user(request, f"{game.title}: Max score = {max_score} points")
    calculate_max_scores.short_description = "Calculate max possible scores"

@admin.register(GameDifficultyRating)
class GameDifficultyRatingAdmin(admin.ModelAdmin):
    """Admin interface for community difficulty ratings"""
    
    list_display = ['game', 'user', 'difficulty_rating', 'created_at']
    list_filter = ['difficulty_rating', 'created_at', 'game__platform']
    search_fields = ['game__title', 'user__username', 'comment']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('game', 'user', 'difficulty_rating', 'comment')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )
