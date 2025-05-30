from django.core.management.base import BaseCommand
from django.db import models
from django.utils import timezone
from games.models import Game
from users.models import User
from rankings.models import RankingPeriod, UserRanking

class CalculateRankingsCommand(BaseCommand):
    help = 'Calculate user rankings for all active periods'

    def handle(self, *args, **options):
        periods = RankingPeriod.objects.filter(active=True)
        
        for period in periods:
            self.calculate_period_rankings(period)
            period.rankings_calculated = True
            period.calculation_date = timezone.now()
            period.save()

        self.stdout.write(
            self.style.SUCCESS(f'Calculated rankings for {periods.count()} periods')
        )

    def calculate_period_rankings(self, period):
        """Calculate rankings for a specific period"""
        # Clear existing rankings for this period
        UserRanking.objects.filter(ranking_period=period).delete()
        
        # Get all users with trophy data
        users = User.objects.filter(total_trophy_score__gt=0).order_by('-total_trophy_score')
        
        for rank, user in enumerate(users, 1):
            UserRanking.objects.create(
                user=user,
                ranking_period=period,
                global_rank=rank,
                total_score=user.total_trophy_score,
                trophies_earned_period=user.bronze_count + user.silver_count + user.gold_count + user.platinum_count,
                platinum_earned_period=user.platinum_count
            )