from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from games.models import Game, GameDifficultyRating
from trophies.models import Trophy, UserTrophy, UserGameProgress
from rankings.models import RankingPeriod, UserRanking, TrophyMilestone
import random
from datetime import datetime, timedelta

User = get_user_model()

class Command(BaseCommand):
    help = 'Create sample data for Trophy Tracker development and testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=10,
            help='Number of sample users to create',
        )
        parser.add_argument(
            '--games', 
            type=int,
            default=20,
            help='Number of sample games to create',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before creating new sample data',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            self.clear_data()

        self.stdout.write(self.style.SUCCESS('Creating sample data...'))
        
        # Create sample games first
        games = self.create_sample_games(options['games'])
        
        # Create sample users
        users = self.create_sample_users(options['users'])
        
        # Create trophies for games
        self.create_sample_trophies(games)
        
        # Create user progress and earned trophies
        self.create_user_progress(users, games)
        
        # Create ranking periods
        self.create_ranking_periods()
        
        # Create some milestones
        self.create_sample_milestones(users, games)

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created sample data: '
                f'{len(users)} users, {len(games)} games'
            )
        )

    def clear_data(self):
        """Clear existing data"""
        UserTrophy.objects.all().delete()
        Trophy.objects.all().delete()
        UserGameProgress.objects.all().delete()
        GameDifficultyRating.objects.all().delete()
        UserRanking.objects.all().delete()
        TrophyMilestone.objects.all().delete()
        RankingPeriod.objects.all().delete()
        Game.objects.all().delete()
        # Keep superuser, delete other users
        User.objects.filter(is_superuser=False).delete()

    def create_sample_games(self, count):
        """Create sample games with varying difficulties"""
        
        sample_games = [
            # Extremely Easy (Ratalaika games)
            {
                'title': 'My Name is Mayo',
                'platform': 'PS4,PS5',
                'difficulty_multiplier': 1.0,
                'description': 'Click the mayo jar 10,000 times.',
                'bronze': 5, 'silver': 3, 'gold': 2, 'platinum': 1
            },
            {
                'title': 'Slyde',
                'platform': 'PS4',
                'difficulty_multiplier': 1.0,
                'description': 'Simple sliding block puzzle game.',
                'bronze': 8, 'silver': 4, 'gold': 3, 'platinum': 1
            },
            
            # Easy Games
            {
                'title': 'Life is Strange',
                'platform': 'PS4',
                'difficulty_multiplier': 1.3,
                'description': 'Episodic adventure game with time manipulation.',
                'bronze': 15, 'silver': 8, 'gold': 4, 'platinum': 1
            },
            {
                'title': 'Telltale\'s The Walking Dead',
                'platform': 'PS4',
                'difficulty_multiplier': 1.4,
                'description': 'Narrative-driven zombie survival game.',
                'bronze': 20, 'silver': 10, 'gold': 5, 'platinum': 1
            },
            
            # Standard Games
            {
                'title': 'Hollow Knight',
                'platform': 'PS4',
                'difficulty_multiplier': 2.2,
                'description': 'Challenging metroidvania with precise combat.',
                'bronze': 25, 'silver': 12, 'gold': 6, 'platinum': 1
            },
            {
                'title': 'Stardew Valley',
                'platform': 'PS4,PS5',
                'difficulty_multiplier': 2.0,
                'description': 'Farming simulation with RPG elements.',
                'bronze': 30, 'silver': 15, 'gold': 8, 'platinum': 1
            },
            
            # AAA Standard
            {
                'title': 'Marvel\'s Spider-Man',
                'platform': 'PS4,PS5',
                'difficulty_multiplier': 3.0,
                'description': 'Open-world superhero action game.',
                'bronze': 35, 'silver': 18, 'gold': 10, 'platinum': 1
            },
            {
                'title': 'God of War (2018)',
                'platform': 'PS4,PS5',
                'difficulty_multiplier': 3.0,
                'description': 'Norse mythology action-adventure.',
                'bronze': 32, 'silver': 16, 'gold': 9, 'platinum': 1
            },
            {
                'title': 'Horizon Zero Dawn',
                'platform': 'PS4,PS5',
                'difficulty_multiplier': 3.0,
                'description': 'Post-apocalyptic robot hunting adventure.',
                'bronze': 40, 'silver': 20, 'gold': 12, 'platinum': 1
            },
            
            # Grind-Heavy
            {
                'title': 'Final Fantasy XV',
                'platform': 'PS4',
                'difficulty_multiplier': 4.0,
                'description': 'JRPG with extensive grinding and side content.',
                'bronze': 45, 'silver': 22, 'gold': 15, 'platinum': 1
            },
            {
                'title': 'Persona 5 Royal',
                'platform': 'PS4,PS5',
                'difficulty_multiplier': 4.0,
                'description': '100+ hour JRPG with social simulation.',
                'bronze': 50, 'silver': 25, 'gold': 18, 'platinum': 1
            },
            
            # Challenging
            {
                'title': 'Celeste',
                'platform': 'PS4',
                'difficulty_multiplier': 5.0,
                'description': 'Precision platformer with challenging mechanics.',
                'bronze': 20, 'silver': 10, 'gold': 7, 'platinum': 1
            },
            {
                'title': 'Dead Cells',
                'platform': 'PS4',
                'difficulty_multiplier': 5.0,
                'description': 'Challenging roguelike metroidvania.',
                'bronze': 28, 'silver': 14, 'gold': 8, 'platinum': 1
            },
            
            # Souls-like
            {
                'title': 'Dark Souls III',
                'platform': 'PS4',
                'difficulty_multiplier': 6.0,
                'description': 'Notoriously difficult action RPG.',
                'bronze': 30, 'silver': 15, 'gold': 10, 'platinum': 1
            },
            {
                'title': 'Bloodborne',
                'platform': 'PS4',
                'difficulty_multiplier': 6.0,
                'description': 'Gothic horror souls-like with aggressive combat.',
                'bronze': 25, 'silver': 12, 'gold': 8, 'platinum': 1
            },
            {
                'title': 'Sekiro: Shadows Die Twice',
                'platform': 'PS4',
                'difficulty_multiplier': 6.0,
                'description': 'Shinobi action game with punishing difficulty.',
                'bronze': 22, 'silver': 11, 'gold': 7, 'platinum': 1
            },
            
            # Very Difficult
            {
                'title': 'Super Meat Boy',
                'platform': 'PS4,PS5',
                'difficulty_multiplier': 8.0,
                'description': 'Brutal precision platformer.',
                'bronze': 15, 'silver': 8, 'gold': 5, 'platinum': 1
            },
            {
                'title': 'Cuphead',
                'platform': 'PS4',
                'difficulty_multiplier': 8.0,
                'description': 'Hand-drawn run-and-gun with boss rush.',
                'bronze': 18, 'silver': 9, 'gold': 6, 'platinum': 1
            },
            
            # Extremely Difficult
            {
                'title': 'Crypt of the NecroDancer',
                'platform': 'PS4',
                'difficulty_multiplier': 10.0,
                'description': 'Rhythm-based roguelike with perfect timing requirements.',
                'bronze': 12, 'silver': 6, 'gold': 4, 'platinum': 1
            },
            {
                'title': 'The Binding of Isaac: Repentance',
                'platform': 'PS4,PS5',
                'difficulty_multiplier': 10.0,
                'description': 'Extremely challenging roguelike with RNG elements.',
                'bronze': 20, 'silver': 10, 'gold': 8, 'platinum': 1
            }
        ]

        games = []
        for i, game_data in enumerate(sample_games[:count]):
            game = Game.objects.create(
                np_communication_id=f'NPWR{10000 + i:05d}_00',
                np_title_id=f'CUSA{10000 + i:05d}_00',
                title=game_data['title'],
                description=game_data['description'],
                platform=game_data['platform'],
                difficulty_multiplier=game_data['difficulty_multiplier'],
                bronze_count=game_data['bronze'],
                silver_count=game_data['silver'],
                gold_count=game_data['gold'],
                platinum_count=game_data['platinum'],
                admin_verified=True,
                players_count=random.randint(1000, 50000),
                completion_rate=random.uniform(5.0, 85.0),
                last_synced=timezone.now()
            )
            games.append(game)

        self.stdout.write(f'Created {len(games)} sample games')
        return games

    def create_sample_users(self, count):
        """Create sample users with PSN IDs"""
        
        sample_usernames = [
            'TrophyHunter2024', 'PlatinumSeeker', 'GamingLegend', 'SoulsVeteran',
            'IndieExplorer', 'RPGMaster', 'SpeedRunner99', 'CompletionistPro',
            'CasualGamer', 'HardcorePlayer', 'RetroCollector', 'AchievementUnlocker',
            'DigitalNinja', 'PixelWarrior', 'GamepadGuru', 'ConsoleCommander'
        ]
        
        users = []
        for i in range(count):
            username = f"{sample_usernames[i % len(sample_usernames)]}{i+1}"
            psn_id = f"{username.lower()}"
            
            user = User.objects.create_user(
                username=username,
                email=f"{username.lower()}@example.com",
                password='testpassword123',
                psn_id=psn_id,
                profile_public=random.choice([True, True, True, False]),  # 75% public
                allow_trophy_sync=True,
                last_trophy_sync=timezone.now() - timedelta(hours=random.randint(1, 72))
            )
            users.append(user)

        self.stdout.write(f'Created {len(users)} sample users')
        return users

    def create_sample_trophies(self, games):
        """Create trophies for each game"""
        
        trophy_templates = {
            'bronze': [
                ('First Steps', 'Complete the tutorial'),
                ('Collector', 'Find 10 collectibles'),
                ('Explorer', 'Visit 5 different areas'),
                ('Survivor', 'Survive for 10 minutes'),
                ('Fighter', 'Win 5 battles'),
                ('Helper', 'Complete a side quest'),
                ('Skilled', 'Perform a special move'),
                ('Lucky', 'Find a rare item'),
                ('Patient', 'Wait for 1 minute'),
                ('Quick', 'Complete a level in under 2 minutes')
            ],
            'silver': [
                ('Veteran', 'Complete 50% of the game'),
                ('Master Collector', 'Find 50 collectibles'),
                ('Boss Slayer', 'Defeat 10 bosses'),
                ('Completionist', 'Complete all side quests'),
                ('Speedster', 'Complete game in under 5 hours'),
                ('Perfectionist', 'Get perfect score on a level')
            ],
            'gold': [
                ('Champion', 'Complete the main story'),
                ('Legendary', 'Reach maximum level'),
                ('Flawless', 'Complete game without dying'),
                ('Ultimate Collector', 'Find all collectibles'),
                ('Master', 'Unlock all abilities')
            ],
            'platinum': [
                ('Platinum Trophy', 'Earn all other trophies')]
        }

        for game in games:
            trophy_id = 0
            
            # Create platinum trophy first
            platinum_trophy = Trophy.objects.create(
                game=game,
                trophy_id=trophy_id,
                name=f"{game.title} Platinum",
                description=f"Earn all other trophies in {game.title}",
                trophy_type='platinum',
                earn_rate=random.uniform(1.0, 15.0),
                rarity_level=random.choice([3, 4])  # Very Rare or Ultra Rare
            )
            trophy_id += 1

            # Create other trophies
            for trophy_type in ['bronze', 'silver', 'gold']:
                count = getattr(game, f'{trophy_type}_count')
                templates = trophy_templates[trophy_type]
                
                for i in range(count):
                    template = random.choice(templates)
                    name = f"{template[0]} {i+1}" if i > 0 else template[0]
                    
                    Trophy.objects.create(
                        game=game,
                        trophy_id=trophy_id,
                        name=name,
                        description=template[1],
                        trophy_type=trophy_type,
                        hidden=random.choice([False, False, False, True]),  # 25% hidden
                        earn_rate=self.get_random_earn_rate(trophy_type),
                        rarity_level=self.get_rarity_level(trophy_type),
                        has_progress_target=random.choice([False, False, True]),  # 33% have progress
                        progress_target_value=random.randint(10, 100) if random.choice([False, True]) else None
                    )
                    trophy_id += 1

        total_trophies = Trophy.objects.count()
        self.stdout.write(f'Created {total_trophies} trophies')

    def get_random_earn_rate(self, trophy_type):
        """Generate realistic earn rates based on trophy type"""
        if trophy_type == 'bronze':
            return random.uniform(40.0, 95.0)
        elif trophy_type == 'silver':
            return random.uniform(20.0, 70.0)
        elif trophy_type == 'gold':
            return random.uniform(10.0, 50.0)
        else:  # platinum
            return random.uniform(1.0, 15.0)

    def get_rarity_level(self, trophy_type):
        """Assign rarity based on trophy type and earn rate"""
        if trophy_type == 'bronze':
            return random.choice([0, 0, 1, 1, 2])  # Mostly common/uncommon
        elif trophy_type == 'silver':
            return random.choice([1, 1, 2, 2, 3])  # Uncommon to rare
        elif trophy_type == 'gold':
            return random.choice([2, 2, 3, 3, 4])  # Rare to ultra rare
        else:  # platinum
            return random.choice([3, 4, 4])  # Very rare to ultra rare

    def create_user_progress(self, users, games):
        """Create user progress and earned trophies"""
        
        for user in users:
            # Each user plays a random subset of games
            user_games = random.sample(games, random.randint(3, min(15, len(games))))
            
            for game in user_games:
                # Create progress record
                progress = UserGameProgress.objects.create(
                    user=user,
                    game=game,
                    started_date=timezone.now() - timedelta(days=random.randint(1, 365))
                )
                
                # Determine completion percentage based on game difficulty
                base_completion = random.uniform(10, 90)
                # Harder games have lower completion rates
                difficulty_factor = max(0.2, 1.0 - (game.difficulty_multiplier - 1.0) * 0.1)
                completion_rate = base_completion * difficulty_factor
                
                # Get all trophies for this game
                all_trophies = list(game.trophies.all())
                total_trophies = len(all_trophies)
                
                if total_trophies > 0:
                    # Calculate how many trophies to earn
                    trophies_to_earn = int((completion_rate / 100) * total_trophies)
                    
                    # Sort trophies by earn rate (easier trophies first)
                    all_trophies.sort(key=lambda t: t.earn_rate or 50, reverse=True)
                    
                    # Award trophies
                    for i, trophy in enumerate(all_trophies[:trophies_to_earn]):
                        earned_date = progress.started_date + timedelta(
                            days=random.randint(0, 100),
                            hours=random.randint(0, 23)
                        )
                        
                        UserTrophy.objects.create(
                            user=user,
                            trophy=trophy,
                            earned=True,
                            earned_datetime=earned_date,
                            progress_value=trophy.progress_target_value if trophy.has_progress_target else None,
                            progress_rate=100 if trophy.has_progress_target else None
                        )
                
                # Update progress statistics
                progress.update_progress()
            
            # Update user's total scores and level
            user.calculate_total_score()
            user.update_trophy_level()
            
            # Update trophy counts
            user_trophies = UserTrophy.objects.filter(user=user, earned=True)
            user.bronze_count = user_trophies.filter(trophy__trophy_type='bronze').count()
            user.silver_count = user_trophies.filter(trophy__trophy_type='silver').count()
            user.gold_count = user_trophies.filter(trophy__trophy_type='gold').count()
            user.platinum_count = user_trophies.filter(trophy__trophy_type='platinum').count()
            user.save()

        self.stdout.write('Created user progress and earned trophies')

    def create_ranking_periods(self):
        """Create ranking periods"""
        
        # All-time ranking
        RankingPeriod.objects.create(
            period_type='all_time',
            start_date=timezone.now() - timedelta(days=365),
            active=True,
            rankings_calculated=True,
            calculation_date=timezone.now()
        )
        
        # Current month
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        RankingPeriod.objects.create(
            period_type='monthly',
            start_date=month_start,
            end_date=month_start + timedelta(days=32),  # Next month
            active=True
        )
        
        # Current week
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        RankingPeriod.objects.create(
            period_type='weekly',
            start_date=week_start,
            end_date=week_start + timedelta(days=7),
            active=True
        )

        self.stdout.write('Created ranking periods')

    def create_sample_milestones(self, users, games):
        """Create sample milestones for users"""
        
        milestone_types = [
            ('first_platinum', 'First Platinum Trophy', 'Earned your very first platinum trophy!'),
            ('100_platinums', '100 Platinum Trophies', 'Reached the milestone of 100 platinum trophies!'),
            ('souls_master', 'Souls Master', 'Completed all FromSoftware games!'),
            ('level_milestone', 'Level 10 Achieved', 'Reached Trophy Level 10!'),
            ('rarity_hunter', 'Ultra Rare Hunter', 'Earned 10 ultra rare trophies!'),
        ]
        
        for user in users[:5]:  # Only create milestones for first 5 users
            # First platinum milestone
            if user.platinum_count > 0:
                TrophyMilestone.objects.create(
                    user=user,
                    milestone_type='first_platinum',
                    title='First Platinum Trophy',
                    description='Earned your very first platinum trophy!',
                    achieved=True,
                    achieved_date=timezone.now() - timedelta(days=random.randint(30, 200))
                )
            
            # Level milestone
            if user.current_trophy_level >= 5:
                TrophyMilestone.objects.create(
                    user=user,
                    milestone_type='level_milestone',
                    title=f'Level {user.current_trophy_level} Achieved',
                    description=f'Reached Trophy Level {user.current_trophy_level}!',
                    achieved=True,
                    achieved_date=timezone.now() - timedelta(days=random.randint(1, 30))
                )

        self.stdout.write('Created sample milestones')