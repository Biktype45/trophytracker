from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from trophies.models import Trophy
from games.models import Game

class RankingPeriod(models.Model):
    """Define ranking periods (monthly, weekly, all-time)"""
    
    PERIOD_TYPES = [
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'), 
        ('all_time', 'All Time'),
    ]
    
    period_type = models.CharField(max_length=20, choices=PERIOD_TYPES)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)  # Null for all-time
    
    # Status
    active = models.BooleanField(default=True)
    rankings_calculated = models.BooleanField(default=False)
    calculation_date = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        if self.period_type == 'all_time':
            return "All Time Rankings"
        return f"{self.get_period_type_display()}: {self.start_date.strftime('%Y-%m-%d')}"
    
    class Meta:
        db_table = 'rankings_rankingperiod'
        ordering = ['-start_date']

class UserRanking(models.Model):
    """Store calculated rankings for users"""
    
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='rankings')
    ranking_period = models.ForeignKey(RankingPeriod, on_delete=models.CASCADE, related_name='user_rankings')
    
    # Ranking Information
    global_rank = models.IntegerField()
    total_score = models.IntegerField()
    
    # Category-specific rankings (optional)
    souls_like_rank = models.IntegerField(null=True, blank=True)
    souls_like_score = models.IntegerField(default=0)
    
    indie_rank = models.IntegerField(null=True, blank=True) 
    indie_score = models.IntegerField(default=0)
    
    aaa_rank = models.IntegerField(null=True, blank=True)
    aaa_score = models.IntegerField(default=0)
    
    # Trophy Statistics for the period
    trophies_earned_period = models.IntegerField(default=0)
    platinum_earned_period = models.IntegerField(default=0)
    
    # Timestamps
    calculated_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username}: Rank #{self.global_rank} ({self.ranking_period})"
    
    class Meta:
        db_table = 'rankings_userranking'
        unique_together = ['user', 'ranking_period']
        ordering = ['global_rank']

class TrophyMilestone(models.Model):
    """Track special achievements and milestones"""
    
    MILESTONE_TYPES = [
        ('first_platinum', 'First Platinum'),
        ('100_platinums', '100 Platinums'),
        ('souls_master', 'Souls-like Master'),
        ('speed_demon', 'Speed Completion'),
        ('rarity_hunter', 'Ultra Rare Hunter'),
        ('level_milestone', 'Level Milestone'),
        ('custom', 'Custom Achievement'),
    ]
    
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='milestones')
    milestone_type = models.CharField(max_length=20, choices=MILESTONE_TYPES)
    
    # Milestone Details
    title = models.CharField(max_length=100)
    description = models.TextField()
    icon_class = models.CharField(max_length=50, default='fas fa-trophy')  # FontAwesome class
    
    # Associated Data
    related_game = models.ForeignKey('games.Game', on_delete=models.SET_NULL, null=True, blank=True)
    related_trophy = models.ForeignKey(Trophy, on_delete=models.SET_NULL, null=True, blank=True)
    score_threshold = models.IntegerField(null=True, blank=True)
    
    # Status
    achieved = models.BooleanField(default=False)
    achieved_date = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        status = "✓" if self.achieved else "○"
        return f"{self.user.username}: {self.title} {status}"
    
    class Meta:
        db_table = 'rankings_trophymilestone'
        ordering = ['-achieved_date', '-created_at']
