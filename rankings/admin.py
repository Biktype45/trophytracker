from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import RankingPeriod, UserRanking, TrophyMilestone

@admin.register(RankingPeriod)
class RankingPeriodAdmin(admin.ModelAdmin):
    """Admin interface for ranking periods"""
    
    list_display = [
        'get_period_display', 'period_type', 'active', 
        'rankings_calculated', 'calculation_date'
    ]
    
    list_filter = ['period_type', 'active', 'rankings_calculated']
    
    readonly_fields = ['calculation_date']
    
    def get_period_display(self, obj):
        """Display period with status"""
        status_color = '#28a745' if obj.active else '#6c757d'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            status_color, str(obj)
        )
    get_period_display.short_description = 'Period'
    
    actions = ['calculate_rankings', 'deactivate_periods']
    
    def calculate_rankings(self, request, queryset):
        """Calculate rankings for selected periods"""
        count = 0
        for period in queryset:
            # This will be implemented in ranking calculation logic
            period.rankings_calculated = True
            period.calculation_date = timezone.now()
            period.save()
            count += 1
        
        self.message_user(request, f"Calculated rankings for {count} periods.")
    calculate_rankings.short_description = "Calculate rankings"
    
    def deactivate_periods(self, request, queryset):
        """Deactivate selected periods"""
        updated = queryset.update(active=False)
        self.message_user(request, f"Deactivated {updated} periods.")
    deactivate_periods.short_description = "Deactivate periods"

@admin.register(UserRanking)
class UserRankingAdmin(admin.ModelAdmin):
    """Admin interface for user rankings"""
    
    list_display = [
        'get_rank_display', 'user', 'ranking_period', 'total_score',
        'trophies_earned_period', 'platinum_earned_period'
    ]
    
    list_filter = [
        'ranking_period__period_type', 'ranking_period__active',
        'calculated_at'
    ]
    
    search_fields = ['user__username', 'user__psn_id']
    
    readonly_fields = ['calculated_at']
    
    ordering = ['ranking_period', 'global_rank']
    
    def get_rank_display(self, obj):
        """Display rank with medal icons"""
        rank = obj.global_rank
        if rank == 1:
            return format_html('🥇 #{} ', rank)
        elif rank == 2:
            return format_html('🥈 #{} ', rank)
        elif rank == 3:
            return format_html('🥉 #{} ', rank)
        elif rank <= 10:
            return format_html('🏆 #{} ', rank)
        else:
            return format_html('#{} ', rank)
    get_rank_display.short_description = 'Rank'

@admin.register(TrophyMilestone)
class TrophyMilestoneAdmin(admin.ModelAdmin):
    """Admin interface for trophy milestones"""
    
    list_display = [
        'user', 'get_milestone_display', 'achieved', 'achieved_date', 'related_game'
    ]
    
    list_filter = [
        'milestone_type', 'achieved', 'achieved_date', 'created_at'
    ]
    
    search_fields = ['user__username', 'title', 'description']
    
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Milestone Information', {
            'fields': (
                'user', 'milestone_type', 'title', 'description', 'icon_class'
            )
        }),
        ('Related Data', {
            'fields': (
                'related_game', 'related_trophy', 'score_threshold'
            )
        }),
        ('Achievement Status', {
            'fields': (
                'achieved', 'achieved_date', 'created_at'
            )
        }),
    )
    
    def get_milestone_display(self, obj):
        """Display milestone with icon and status"""
        status_icon = '✅' if obj.achieved else '⏳'
        return format_html(
            '{} <i class="{}"></i> {}',
            status_icon, obj.icon_class, obj.title
        )
    get_milestone_display.short_description = 'Milestone'
    
    actions = ['mark_achieved', 'create_custom_milestones']
    
    def mark_achieved(self, request, queryset):
        """Mark selected milestones as achieved"""
        updated = queryset.filter(achieved=False).update(
            achieved=True, 
            achieved_date=timezone.now()
        )
        self.message_user(request, f"Marked {updated} milestones as achieved.")
    mark_achieved.short_description = "Mark as achieved"
