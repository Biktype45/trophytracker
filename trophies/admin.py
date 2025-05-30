from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Trophy, UserTrophy, UserGameProgress

class UserTrophyInline(admin.TabularInline):
    """Inline admin for user trophies"""
    model = UserTrophy
    extra = 0
    readonly_fields = ['calculate_points_display', 'synced_at']
    fields = ['user', 'earned', 'earned_datetime', 'progress_value', 'calculate_points_display']
    
    def calculate_points_display(self, obj):
        """Display points for this trophy"""
        if obj.id:
            points = obj.calculate_points_earned()
            return f"{points} points"
        return "0 points"
    calculate_points_display.short_description = 'Points'

@admin.register(Trophy)
class TrophyAdmin(admin.ModelAdmin):
    """Admin interface for trophies"""
    
    list_display = [
        'name', 'game', 'get_trophy_type_display', 'get_score_display',
        'earn_rate', 'get_rarity_display', 'hidden'
    ]
    
    list_filter = [
        'trophy_type', 'rarity_level', 'hidden', 'has_progress_target',
        'game__platform', 'game__difficulty_multiplier'
    ]
    
    search_fields = ['name', 'description', 'game__title']
    
    readonly_fields = [
        'trophy_id', 'get_score_display', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Trophy Information', {
            'fields': (
                'game', 'name', 'description', 'trophy_type', 'icon_url'
            )
        }),
        ('PlayStation API Data', {
            'fields': (
                'trophy_id', 'trophy_group_id', 'hidden'
            )
        }),
        ('Progress Tracking', {
            'fields': (
                'has_progress_target', 'progress_target_value'
            )
        }),
        ('Rarity Information', {
            'fields': (
                'earn_rate', 'rarity_level'
            )
        }),
        ('Calculated Values', {
            'fields': (
                'get_score_display', 'created_at', 'updated_at'
            )
        }),
    )
    
    inlines = [UserTrophyInline]
    
    def get_trophy_type_display(self, obj):
        """Display trophy type with icon"""
        icons = {
            'bronze': '🥉',
            'silver': '🥈', 
            'gold': '🥇',
            'platinum': '🏆'
        }
        icon = icons.get(obj.trophy_type, '🏆')
        return format_html('{} {}', icon, obj.get_trophy_type_display())
    get_trophy_type_display.short_description = 'Type'
    
    def get_score_display(self, obj):
        """Display calculated score"""
        base_points = obj.get_base_points()
        total_score = obj.calculate_score()
        multiplier = obj.game.difficulty_multiplier
        
        return format_html(
            '<span title="Base: {} × Multiplier: {:.1f}">{} points</span>',
            base_points, multiplier, total_score
        )
    get_score_display.short_description = 'Score'
    
    def get_rarity_display(self, obj):
        """Display rarity with color"""
        colors = {
            0: '#28a745',  # Common - Green
            1: '#17a2b8',  # Uncommon - Blue  
            2: '#ffc107',  # Rare - Yellow
            3: '#fd7e14',  # Very Rare - Orange
            4: '#dc3545'   # Ultra Rare - Red
        }
        color = colors.get(obj.rarity_level, '#6c757d')
        rarity_name = obj.get_rarity_name()
        
        if obj.earn_rate:
            return format_html(
                '<span style="color: {}; font-weight: bold;">{} ({:.1f}%)</span>',
                color, rarity_name, obj.earn_rate
            )
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, rarity_name
        )
    get_rarity_display.short_description = 'Rarity'

@admin.register(UserTrophy)
class UserTrophyAdmin(admin.ModelAdmin):
    """Admin interface for user trophy relationships"""
    
    list_display = [
        'user', 'get_trophy_info', 'earned', 'earned_datetime', 
        'get_points_display', 'progress_rate'
    ]
    
    list_filter = [
        'earned', 'trophy__trophy_type', 'trophy__game__platform',
        'earned_datetime', 'synced_at'
    ]
    
    search_fields = [
        'user__username', 'user__psn_id', 'trophy__name', 'trophy__game__title'
    ]
    
    readonly_fields = ['get_points_display', 'synced_at', 'created_at']
    
    def get_trophy_info(self, obj):
        """Display trophy and game information"""
        trophy_icons = {'bronze': '🥉', 'silver': '🥈', 'gold': '🥇', 'platinum': '🏆'}
        icon = trophy_icons.get(obj.trophy.trophy_type, '🏆')
        
        return format_html(
            '{} {} - <small>{}</small>',
            icon, obj.trophy.name, obj.trophy.game.title
        )
    get_trophy_info.short_description = 'Trophy'
    
    def get_points_display(self, obj):
        """Display points earned"""
        points = obj.calculate_points_earned()
        if points > 0:
            return format_html('<span style="color: #28a745; font-weight: bold;">{} pts</span>', points)
        return format_html('<span style="color: #6c757d;">0 pts</span>')
    get_points_display.short_description = 'Points'

@admin.register(UserGameProgress)
class UserGameProgressAdmin(admin.ModelAdmin):
    """Admin interface for user game progress"""
    
    list_display = [
        'user', 'game', 'get_progress_display', 'get_trophies_display',
        'total_score_earned', 'completed', 'last_trophy_date'
    ]
    
    list_filter = [
        'completed', 'hidden', 'game__platform', 'game__difficulty_multiplier',
        'progress_percentage', 'last_updated'
    ]
    
    search_fields = ['user__username', 'game__title']
    
    readonly_fields = [
        'total_score_earned', 'max_possible_score', 'started_date',
        'completion_date', 'last_updated'
    ]
    
    fieldsets = (
        ('User & Game', {
            'fields': ('user', 'game', 'hidden')
        }),
        ('Progress', {
            'fields': (
                'progress_percentage', 'completed',
                ('bronze_earned', 'silver_earned'),
                ('gold_earned', 'platinum_earned')
            )
        }),
        ('Scoring', {
            'fields': (
                'total_score_earned', 'max_possible_score'
            )
        }),
        ('Timestamps', {
            'fields': (
                'started_date', 'last_trophy_date', 
                'completion_date', 'last_updated'
            )
        }),
    )
    
    def get_progress_display(self, obj):
        """Display progress with visual bar"""
        percentage = obj.progress_percentage
        color = '#28a745' if obj.completed else '#007bff'
        
        return format_html(
            '<div style="width: 100px; background: #e9ecef; border-radius: 3px;">'
            '<div style="width: {}%; background: {}; height: 20px; border-radius: 3px; '
            'display: flex; align-items: center; justify-content: center; color: white; font-size: 12px;">'
            '{}%</div></div>',
            percentage, color, percentage
        )
    get_progress_display.short_description = 'Progress'
    
    def get_trophies_display(self, obj):
        """Display trophy counts"""
        return format_html(
            '🥉{} 🥈{} 🥇{} 🏆{}',
            obj.bronze_earned, obj.silver_earned, obj.gold_earned, obj.platinum_earned
        )
    get_trophies_display.short_description = 'Trophies'
    
    actions = ['update_progress', 'recalculate_scores']
    
    def update_progress(self, request, queryset):
        """Recalculate progress for selected records"""
        count = 0
        for progress in queryset:
            progress.update_progress()
            count += 1
        
        self.message_user(request, f"Updated progress for {count} records.")
    update_progress.short_description = "Recalculate progress statistics"
