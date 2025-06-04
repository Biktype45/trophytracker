from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

class Game(models.Model):
    """PlayStation game with difficulty multiplier for skill-based scoring"""
    
    PLATFORM_CHOICES = [
        ('PS3', 'PlayStation 3'),
        ('PS4', 'PlayStation 4'),
        ('PS5', 'PlayStation 5'),
        ('PSV', 'PlayStation Vita'),
        ('PSP', 'PlayStation Portable'),
    ]
    
    DIFFICULTY_CATEGORIES = [
        ('extremely_easy', 'Extremely Easy (1.0-1.1x)'),
        ('easy', 'Easy (1.2-1.5x)'),
        ('standard', 'Standard (1.6-2.5x)'),
        ('aaa_standard', 'AAA Standard (3.0x)'),
        ('grind_heavy', 'Grind Heavy (4.0x)'),
        ('challenging', 'Challenging (5.0x)'),
        ('souls_like', 'Souls-like (6.0x)'),
        ('very_difficult', 'Very Difficult (8.0x)'),
        ('extremely_difficult', 'Extremely Difficult (10.0x)'),
    ]
    
    # PlayStation API identifiers
    np_communication_id = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=200)
    platform = models.CharField(max_length=5, choices=PLATFORM_CHOICES, default='PS5')
    
    # Game metadata
    icon_url = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True)
    release_date = models.DateField(null=True, blank=True)
    publisher = models.CharField(max_length=100, blank=True)
    
    # Trophy information
    has_trophy_groups = models.BooleanField(default=False)
    trophy_set_version = models.CharField(max_length=10, default='01.00')
    
    # Trophy counts
    bronze_count = models.IntegerField(default=0)
    silver_count = models.IntegerField(default=0)
    gold_count = models.IntegerField(default=0)
    platinum_count = models.IntegerField(default=0)
    
    # Difficulty and scoring
    difficulty_multiplier = models.FloatField(
        default=3.0,
        validators=[MinValueValidator(1.0), MaxValueValidator(10.0)],
        help_text="Multiplier for skill-based scoring (1.0 = easiest, 10.0 = hardest)"
    )
    difficulty_category = models.CharField(
        max_length=20,
        choices=DIFFICULTY_CATEGORIES,
        default='aaa_standard'
    )
    
    # Auto-assigned based on completion rates
    completion_rate = models.FloatField(null=True, blank=True)
    average_completion_time = models.FloatField(null=True, blank=True)
    
    # Metadata
    last_synced = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'games_game'
        ordering = ['title']
        indexes = [
            models.Index(fields=['np_communication_id']),
            models.Index(fields=['difficulty_multiplier']),
            models.Index(fields=['platform']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.platform}) - {self.difficulty_multiplier}x"
    
    def get_total_trophy_count(self):
        """Return total number of trophies in this game"""
        return self.bronze_count + self.silver_count + self.gold_count + self.platinum_count
    
    def calculate_max_possible_score(self):
        """Calculate maximum possible score for this game"""
        base_points = {
            'bronze': 1,
            'silver': 3,
            'gold': 6,
            'platinum': 15
        }
        
        total = (
            (self.bronze_count * base_points['bronze']) +
            (self.silver_count * base_points['silver']) +
            (self.gold_count * base_points['gold']) +
            (self.platinum_count * base_points['platinum'])
        )
        
        return int(total * self.difficulty_multiplier)
    
    def get_difficulty_category(self):
        """Return human-readable difficulty category"""
        multiplier = self.difficulty_multiplier
        
        if multiplier <= 1.1:
            return "Extremely Easy"
        elif multiplier <= 1.5:
            return "Easy"
        elif multiplier <= 2.5:
            return "Standard"
        elif multiplier <= 3.0:
            return "AAA Standard"
        elif multiplier <= 4.0:
            return "Grind Heavy"
        elif multiplier <= 5.0:
            return "Challenging"
        elif multiplier <= 6.0:
            return "Souls-like"
        elif multiplier <= 8.0:
            return "Very Difficult"
        else:
            return "Extremely Difficult"
    
    def update_difficulty_from_completion_rate(self):
        """Auto-update difficulty based on completion rate"""
        if self.completion_rate is not None:
            if self.completion_rate >= 70:
                self.difficulty_multiplier = 1.2
            elif self.completion_rate >= 50:
                self.difficulty_multiplier = 1.5
            elif self.completion_rate >= 35:
                self.difficulty_multiplier = 2.0
            elif self.completion_rate >= 25:
                self.difficulty_multiplier = 3.0
            elif self.completion_rate >= 15:
                self.difficulty_multiplier = 4.0
            elif self.completion_rate >= 10:
                self.difficulty_multiplier = 5.0
            elif self.completion_rate >= 5:
                self.difficulty_multiplier = 6.0
            elif self.completion_rate >= 2:
                self.difficulty_multiplier = 8.0
            else:
                self.difficulty_multiplier = 10.0
            
            self.save()