from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

class Trophy(models.Model):
    """Individual trophy within a game"""
    
    TROPHY_TYPES = [
        ('bronze', 'Bronze'),
        ('silver', 'Silver'), 
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
    ]
    
    # PlayStation API identifiers
    game = models.ForeignKey('games.Game', on_delete=models.CASCADE, related_name='trophies')
    trophy_id = models.IntegerField()  # From PSN API
    trophy_group_id = models.CharField(max_length=20, default='default')
    
    # Trophy Information
    name = models.CharField(max_length=200)
    description = models.TextField()
    trophy_type = models.CharField(max_length=10, choices=TROPHY_TYPES)
    icon_url = models.URLField(blank=True, null=True)
    
    # Trophy Properties
    hidden = models.BooleanField(default=False)
    
    # Progress Tracking (PS5 feature)
    has_progress_target = models.BooleanField(default=False)
    progress_target_value = models.IntegerField(null=True, blank=True)
    
    # Rarity Information
    earn_rate = models.FloatField(null=True, blank=True)  # Percentage who earned it
    rarity_level = models.IntegerField(
        choices=[(0, 'Common'), (1, 'Uncommon'), (2, 'Rare'), (3, 'Very Rare'), (4, 'Ultra Rare')],
        default=0
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.trophy_type}) - {self.game.title}"
    
    def get_base_points(self):
        """Return base points for trophy type"""
        base_points = {
            'bronze': 1,
            'silver': 3, 
            'gold': 6,
            'platinum': 15
        }
        return base_points.get(self.trophy_type, 1)
    
    def calculate_score(self):
        """Calculate final score including game multiplier"""
        base_points = self.get_base_points()
        return int(base_points * self.game.difficulty_multiplier)
    
    def get_rarity_name(self):
        """Return rarity level name"""
        rarity_names = {
            0: 'Common',
            1: 'Uncommon', 
            2: 'Rare',
            3: 'Very Rare',
            4: 'Ultra Rare'
        }
        return rarity_names.get(self.rarity_level, 'Common')
    
    class Meta:
        db_table = 'trophies_trophy'
        unique_together = ['game', 'trophy_id']
        ordering = ['trophy_id']

class UserTrophy(models.Model):
    """Junction table tracking which trophies users have earned"""
    
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='user_trophies')
    trophy = models.ForeignKey(Trophy, on_delete=models.CASCADE, related_name='user_trophies')
    
    # Earning Status
    earned = models.BooleanField(default=False)
    earned_datetime = models.DateTimeField(null=True, blank=True)
    
    # Progress Tracking (PS5 feature)
    progress_value = models.IntegerField(null=True, blank=True)
    progress_rate = models.IntegerField(null=True, blank=True)  # Percentage
    progress_datetime = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    synced_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        earned_status = "✓" if self.earned else "✗"
        return f"{self.user.username}: {self.trophy.name} {earned_status}"
    
    def calculate_points_earned(self):
        """Calculate points earned for this trophy"""
        if self.earned:
            return self.trophy.calculate_score()
        return 0
    
    class Meta:
        db_table = 'trophies_usertrophy'
        unique_together = ['user', 'trophy']
        ordering = ['-earned_datetime']

class UserGameProgress(models.Model):
    """Track user's progress in each game"""
    
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='game_progress')
    game = models.ForeignKey('games.Game', on_delete=models.CASCADE, related_name='user_progress')
    
    # Progress Statistics
    progress_percentage = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    # Trophy Counts Earned
    bronze_earned = models.IntegerField(default=0)
    silver_earned = models.IntegerField(default=0)
    gold_earned = models.IntegerField(default=0)
    platinum_earned = models.IntegerField(default=0)
    
    # Score Information
    total_score_earned = models.IntegerField(default=0)
    max_possible_score = models.IntegerField(default=0)
    
    # Status
    completed = models.BooleanField(default=False)  # 100% completion
    hidden = models.BooleanField(default=False)  # User can hide games
    
    # Timestamps
    started_date = models.DateTimeField(auto_now_add=True)
    last_trophy_date = models.DateTimeField(null=True, blank=True)
    completion_date = models.DateTimeField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}: {self.game.title} ({self.progress_percentage}%)"
    
    def update_progress(self):
        """Recalculate progress statistics from user trophies"""
        user_trophies = UserTrophy.objects.filter(
            user=self.user, 
            trophy__game=self.game,
            earned=True
        )
        
        # Count earned trophies by type
        self.bronze_earned = user_trophies.filter(trophy__trophy_type='bronze').count()
        self.silver_earned = user_trophies.filter(trophy__trophy_type='silver').count()
        self.gold_earned = user_trophies.filter(trophy__trophy_type='gold').count()
        self.platinum_earned = user_trophies.filter(trophy__trophy_type='platinum').count()
        
        # Calculate progress percentage
        total_earned = self.bronze_earned + self.silver_earned + self.gold_earned + self.platinum_earned
        total_available = self.game.get_total_trophy_count()
        
        if total_available > 0:
            self.progress_percentage = int((total_earned / total_available) * 100)
        else:
            self.progress_percentage = 0
        
        # Calculate scores
        self.total_score_earned = sum(ut.calculate_points_earned() for ut in user_trophies)
        self.max_possible_score = self.game.calculate_max_possible_score()
        
        # Check completion
        self.completed = (self.progress_percentage == 100)
        if self.completed and not self.completion_date:
            self.completion_date = timezone.now()
        
        # Update last trophy date
        last_trophy = user_trophies.filter(earned_datetime__isnull=False).order_by('-earned_datetime').first()
        if last_trophy:
            self.last_trophy_date = last_trophy.earned_datetime
        
        self.save()
    
    class Meta:
        db_table = 'trophies_usergameprogress'
        unique_together = ['user', 'game']
        ordering = ['-last_updated']