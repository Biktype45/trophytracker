# =============================================================================
# games/admin.py
# =============================================================================
from django.contrib import admin
from django.utils.html import format_html
from .models import Game

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'platform', 'get_difficulty_display', 'get_trophy_count_display',
        'completion_rate', 'last_synced'
    ]
    
    list_filter = [
        'platform', 'difficulty_category', 'difficulty_multiplier',
        'has_trophy_groups', 'created_at'
    ]
    
    search_fields = ['title', 'np_communication_id', 'publisher']
    
    readonly_fields = [
        'np_communication_id', 'last_synced', 'created_at', 'updated_at',
        'get_max_score_display'
    ]
    
    fieldsets = (
        ('Game Information', {
            'fields': (
                'np_communication_id', 'title', 'platform', 'publisher',
                'description', 'icon_url', 'release_date'
            )
        }),
        ('Trophy Information', {
            'fields': (
                'has_trophy_groups', 'trophy_set_version',
                ('bronze_count', 'silver_count'),
                ('gold_count', 'platinum_count')
            )
        }),
        ('Difficulty & Scoring', {
            'fields': (
                'difficulty_multiplier', 'difficulty_category',
                'completion_rate', 'average_completion_time',
                'get_max_score_display'
            )
        }),
        ('Metadata', {
            'fields': ('last_synced', 'created_at', 'updated_at')
        }),
    )
    
    def get_difficulty_display(self, obj):
        """Display difficulty with color coding"""
        colors = {
            'extremely_easy': '#28a745',
            'easy': '#17a2b8',
            'standard': '#ffc107',
            'aaa_standard': '#007bff',
            'grind_heavy': '#6f42c1',
            'challenging': '#fd7e14',
            'souls_like': '#dc3545',
            'very_difficult': '#e83e8c',
            'extremely_difficult': '#6c757d'
        }
        
        color = colors.get(obj.difficulty_category, '#007bff')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}x</span>',
            color, obj.difficulty_multiplier
        )
    get_difficulty_display.short_description = 'Difficulty'
    
    def get_trophy_count_display(self, obj):
        """Display trophy counts with icons"""
        return format_html(
            '🥉{} 🥈{} 🥇{} 🏆{}',
            obj.bronze_count, obj.silver_count, obj.gold_count, obj.platinum_count
        )
    get_trophy_count_display.short_description = 'Trophies'
    
    def get_max_score_display(self, obj):
        """Display maximum possible score for this game"""
        max_score = obj.calculate_max_possible_score()
        return f"{max_score:,} points"
    get_max_score_display.short_description = 'Max Score'