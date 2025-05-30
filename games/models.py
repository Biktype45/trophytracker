from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class Game(models.Model):
    """PlayStation game with difficulty rating and metadata"""
    
    # PlayStation API identifiers
    np_communication_id = models.CharField(max_length=50, unique=True)
    np_title_id = models.CharField(max_length=50, blank=True, null=True)
    np_service_name = models.CharField(max_length=20, default='trophy2')
    
    # Game Information
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    icon_url = models.URLField(blank=True, null=True)
    platform = models.CharField(max_length=50)  # PS5, PS4, PS3, etc.
    
    # Trophy Information
    has_trophy_groups = models.BooleanField(default=False)
    trophy_set_version = models.CharField(max_length=20, default='01.00')
    
    # Trophy Counts
    bronze_count = models.IntegerField(default=0)
    silver_count = models.IntegerField(default=0) 
    gold_count = models.IntegerField(default=0)
    platinum_count = models.IntegerField(default=0, validators=[MaxValueValidator(1)])
    
    # Difficulty System (Core Feature)
    DIFFICULTY_CHOICES = [
        (1.0, 'Extremely Easy (1.0x)'),
        (1.1, 'Extremely Easy (1.1x)'),
        (1.2, 'Easy (1.2x)'),
        (1.3, 'Easy (1.3x)'),
        (1.4, 'Easy (1.4x)'),
        (1.5, 'Easy (1.5x)'),
        (1.6, 'Standard (1.6x)'),
        (1.7, 'Standard (1.7x)'),
        (1.8, 'Standard (1.8x)'),
        (1.9, 'Standard (1.9x)'),
        (2.0, 'Standard (2.0x)'),
        (2.1, 'Standard (2.1x)'),
        (2.2, 'Standard (2.2x)'),
        (2.3, 'Standard (2.3x)'),
        (2.4, 'Standard (2.4x)'),
        (2.5, 'Standard (2.5x)'),
        (3.0, 'AAA Standard (3.0x)'),
        (4.0, 'Grind-Heavy (4.0x)'),
        (5.0, 'Challenging (5.0x)'),
        (6.0, 'Souls-like (6.0x)'),
        (8.0, 'Very Difficult (8.0x)'),
        (10.0, 'Extremely Difficult (10.0x)'),
    ]
    
    difficulty_multiplier = models.FloatField(
        choices=DIFFICULTY_CHOICES,
        default=3.0,
        help_text="Multiplier applied to all trophies in this game"
    )
    
    # Difficulty Rating Metadata
    difficulty_rating_count = models.IntegerField(default=0)
    community_difficulty_rating = models.FloatField(null=True, blank=True)
    admin_verified = models.BooleanField(default=False)
    
    # Statistics
    completion_rate = models.FloatField(null=True, blank=True)  # From PSN API
    players_count = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_synced = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.title} ({self.platform}) - {self.difficulty_multiplier}x"
    
    def get_difficulty_category(self):
        """Return difficulty category name"""
        if self.difficulty_multiplier <= 1.1:
            return "Extremely Easy"
        elif self.difficulty_multiplier <= 1.5:
            return "Easy"
        elif self.difficulty_multiplier <= 2.5:
            return "Standard"
        elif self.difficulty_multiplier == 3.0:
            return "AAA Standard"
        elif self.difficulty_multiplier == 4.0:
            return "Grind-Heavy"
        elif self.difficulty_multiplier == 5.0:
            return "Challenging"
        elif self.difficulty_multiplier == 6.0:
            return "Souls-like"
        elif self.difficulty_multiplier == 8.0:
            return "Very Difficult"
        elif self.difficulty_multiplier == 10.0:
            return "Extremely Difficult"
        else:
            return "Standard"
    
    def get_total_trophy_count(self):
        """Return total number of trophies"""
        return self.bronze_count + self.silver_count + self.gold_count + self.platinum_count
    
    def calculate_max_possible_score(self):
        """Calculate maximum possible score for completing all trophies"""
        bronze_points = self.bronze_count * 1 * self.difficulty_multiplier
        silver_points = self.silver_count * 3 * self.difficulty_multiplier  
        gold_points = self.gold_count * 6 * self.difficulty_multiplier
        platinum_points = self.platinum_count * 15 * self.difficulty_multiplier
        
        return int(bronze_points + silver_points + gold_points + platinum_points)
    
    class Meta:
        db_table = 'games_game'
        ordering = ['-updated_at']

class GameDifficultyRating(models.Model):
    """Community-driven difficulty ratings for games"""
    
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='difficulty_ratings')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    
    difficulty_rating = models.FloatField(
        validators=[MinValueValidator(1.0), MaxValueValidator(10.0)],
        help_text="Difficulty rating from 1.0 (extremely easy) to 10.0 (extremely difficult)"
    )
    
    # Optional feedback
    comment = models.TextField(blank=True, help_text="Optional explanation of rating")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'games_difficultyrating'
        unique_together = ['game', 'user']
        
    def __str__(self):
        return f"{self.user.username}: {self.game.title} - {self.difficulty_rating}/10"
