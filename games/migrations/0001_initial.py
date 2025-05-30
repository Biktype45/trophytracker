# Generated by Django 5.2.1 on 2025-05-30 16:15

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Game',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('np_communication_id', models.CharField(max_length=50, unique=True)),
                ('np_title_id', models.CharField(blank=True, max_length=50, null=True)),
                ('np_service_name', models.CharField(default='trophy2', max_length=20)),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('icon_url', models.URLField(blank=True, null=True)),
                ('platform', models.CharField(max_length=50)),
                ('has_trophy_groups', models.BooleanField(default=False)),
                ('trophy_set_version', models.CharField(default='01.00', max_length=20)),
                ('bronze_count', models.IntegerField(default=0)),
                ('silver_count', models.IntegerField(default=0)),
                ('gold_count', models.IntegerField(default=0)),
                ('platinum_count', models.IntegerField(default=0, validators=[django.core.validators.MaxValueValidator(1)])),
                ('difficulty_multiplier', models.FloatField(choices=[(1.0, 'Extremely Easy (1.0x)'), (1.1, 'Extremely Easy (1.1x)'), (1.2, 'Easy (1.2x)'), (1.3, 'Easy (1.3x)'), (1.4, 'Easy (1.4x)'), (1.5, 'Easy (1.5x)'), (1.6, 'Standard (1.6x)'), (1.7, 'Standard (1.7x)'), (1.8, 'Standard (1.8x)'), (1.9, 'Standard (1.9x)'), (2.0, 'Standard (2.0x)'), (2.1, 'Standard (2.1x)'), (2.2, 'Standard (2.2x)'), (2.3, 'Standard (2.3x)'), (2.4, 'Standard (2.4x)'), (2.5, 'Standard (2.5x)'), (3.0, 'AAA Standard (3.0x)'), (4.0, 'Grind-Heavy (4.0x)'), (5.0, 'Challenging (5.0x)'), (6.0, 'Souls-like (6.0x)'), (8.0, 'Very Difficult (8.0x)'), (10.0, 'Extremely Difficult (10.0x)')], default=3.0, help_text='Multiplier applied to all trophies in this game')),
                ('difficulty_rating_count', models.IntegerField(default=0)),
                ('community_difficulty_rating', models.FloatField(blank=True, null=True)),
                ('admin_verified', models.BooleanField(default=False)),
                ('completion_rate', models.FloatField(blank=True, null=True)),
                ('players_count', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('last_synced', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'games_game',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='GameDifficultyRating',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('difficulty_rating', models.FloatField(help_text='Difficulty rating from 1.0 (extremely easy) to 10.0 (extremely difficult)', validators=[django.core.validators.MinValueValidator(1.0), django.core.validators.MaxValueValidator(10.0)])),
                ('comment', models.TextField(blank=True, help_text='Optional explanation of rating')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('game', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='difficulty_ratings', to='games.game')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'games_difficultyrating',
                'unique_together': {('game', 'user')},
            },
        ),
    ]
