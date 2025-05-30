from django.core.management.base import BaseCommand
from django.db import models
from django.utils import timezone
from games.models import Game

class UpdateDifficultyRatingsCommand(BaseCommand):
    help = 'Update game difficulty ratings based on community feedback'

    def handle(self, *args, **options):
        games_updated = 0
        
        for game in Game.objects.all():
            ratings = game.difficulty_ratings.all()
            if ratings.exists():
                avg_rating = ratings.aggregate(avg=models.Avg('difficulty_rating'))['avg']
                game.community_difficulty_rating = avg_rating
                game.difficulty_rating_count = ratings.count()
                game.save()
                games_updated += 1

        self.stdout.write(
            self.style.SUCCESS(f'Updated difficulty ratings for {games_updated} games')
        )
