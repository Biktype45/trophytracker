from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid

class User(AbstractUser):
    """Extended User model with PSN integration and trophy tracking"""
    
    # PSN Integration
    psn_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    psn_avatar_url = models.URLField(blank=True, null=True)
    psn_account_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    psn_access_token = models.TextField(blank=True, null=True)  # Encrypted in production
    psn_refresh_token = models.TextField(blank=True, null=True)  # Encrypted in production
    psn_token_expires = models.DateTimeField(null=True, blank=True)
    
    # Trophy Stats (calculated fields)
    total_trophy_score = models.IntegerField(default=0)
    current_trophy_level = models.IntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(20)])
    level_progress_percentage = models.FloatField(default=0.0)
    
    # Trophy Counts
    bronze_count = models.IntegerField(default=0)
    silver_count = models.IntegerField(default=0)
    gold_count = models.IntegerField(default=0)
    platinum_count = models.IntegerField(default=0)
    
    # Profile Settings
    profile_public = models.BooleanField(default=True)
    show_rare_trophies = models.BooleanField(default=True)
    allow_trophy_sync = models.BooleanField(default=True)
    
    # Timestamps
    last_trophy_sync = models.DateTimeField(null=True, blank=True)
    profile_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.username} ({self.psn_id or 'No PSN ID'})"
    
    def get_trophy_level_name(self):
        """Return the trophy level name based on current level"""
        level_names = {
            1: "PS Noob",
            2: "Button Masher", 
            3: "Trophy Hunter",
            4: "Achievement Seeker",
            5: "Digital Collector",
            6: "Gaming Enthusiast",
            7: "Skill Apprentice",
            8: "Trophy Veteran",
            9: "Gaming Gladiator",
            10: "Platinum Pursuer",
            11: "Elite Gamer",
            12: "Trophy Titan",
            13: "Achievement Ace",
            14: "Legendary Hunter",
            15: "Gaming Virtuoso",
            16: "Trophy Overlord",
            17: "Digital Deity",
            18: "PlayStation Paragon",
            19: "Trophy Transcendent",
            20: "Maybe I Was The PlayStation All Along"
        }
        return level_names.get(self.current_trophy_level, "Unknown Level")
    
    def calculate_total_score(self):
        """Calculate total trophy score from all user trophies"""
        from trophies.models import UserTrophy
        total = 0
        user_trophies = UserTrophy.objects.filter(user=self, earned=True).select_related('trophy__game')
        
        for user_trophy in user_trophies:
            trophy = user_trophy.trophy
            game = trophy.game
            base_points = trophy.get_base_points()
            multiplier = game.difficulty_multiplier
            total += int(base_points * multiplier)
        
        self.total_trophy_score = total
        self.save(update_fields=['total_trophy_score'])
        return total
    
    def update_trophy_level(self):
        """Update user's trophy level based on total score"""
        # Level thresholds from the project plan
        level_thresholds = [
            (0, 1), (100, 2), (350, 3), (850, 4), (1850, 5),
            (3850, 6), (7850, 7), (15350, 8), (27850, 9), (47850, 10),
            (80350, 11), (130350, 12), (205350, 13), (315350, 14), (475350, 15),
            (700350, 16), (1010350, 17), (1430350, 18), (1980350, 19), (2730350, 20)
        ]
        
        new_level = 1
        next_threshold = 100
        current_threshold = 0
        
        # Find the appropriate level based on score
        for threshold, level in level_thresholds:
            if self.total_trophy_score >= threshold:
                new_level = level
                current_threshold = threshold
                
                # Find next threshold
                next_idx = level_thresholds.index((threshold, level)) + 1
                if next_idx < len(level_thresholds):
                    next_threshold = level_thresholds[next_idx][0]
                else:
                    next_threshold = threshold  # Max level reached
            else:
                break
        
        # Calculate progress percentage to next level
        if new_level < 20 and next_threshold > current_threshold:
            progress = ((self.total_trophy_score - current_threshold) / 
                       (next_threshold - current_threshold)) * 100
            self.level_progress_percentage = min(progress, 100.0)
        else:
            self.level_progress_percentage = 100.0
        
        self.current_trophy_level = new_level
        self.save(update_fields=['current_trophy_level', 'level_progress_percentage'])
    
    class Meta:
        db_table = 'users_user'