# Generated by Django 5.2.1 on 2025-05-30 16:15

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('games', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Trophy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('trophy_id', models.IntegerField()),
                ('trophy_group_id', models.CharField(default='default', max_length=20)),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('trophy_type', models.CharField(choices=[('bronze', 'Bronze'), ('silver', 'Silver'), ('gold', 'Gold'), ('platinum', 'Platinum')], max_length=10)),
                ('icon_url', models.URLField(blank=True, null=True)),
                ('hidden', models.BooleanField(default=False)),
                ('has_progress_target', models.BooleanField(default=False)),
                ('progress_target_value', models.IntegerField(blank=True, null=True)),
                ('earn_rate', models.FloatField(blank=True, null=True)),
                ('rarity_level', models.IntegerField(choices=[(0, 'Common'), (1, 'Uncommon'), (2, 'Rare'), (3, 'Very Rare'), (4, 'Ultra Rare')], default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('game', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='trophies', to='games.game')),
            ],
            options={
                'db_table': 'trophies_trophy',
                'ordering': ['trophy_id'],
                'unique_together': {('game', 'trophy_id')},
            },
        ),
        migrations.CreateModel(
            name='UserGameProgress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('progress_percentage', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('bronze_earned', models.IntegerField(default=0)),
                ('silver_earned', models.IntegerField(default=0)),
                ('gold_earned', models.IntegerField(default=0)),
                ('platinum_earned', models.IntegerField(default=0)),
                ('total_score_earned', models.IntegerField(default=0)),
                ('max_possible_score', models.IntegerField(default=0)),
                ('completed', models.BooleanField(default=False)),
                ('hidden', models.BooleanField(default=False)),
                ('started_date', models.DateTimeField(auto_now_add=True)),
                ('last_trophy_date', models.DateTimeField(blank=True, null=True)),
                ('completion_date', models.DateTimeField(blank=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('game', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_progress', to='games.game')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='game_progress', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'trophies_usergameprogress',
                'ordering': ['-last_updated'],
                'unique_together': {('user', 'game')},
            },
        ),
        migrations.CreateModel(
            name='UserTrophy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('earned', models.BooleanField(default=False)),
                ('earned_datetime', models.DateTimeField(blank=True, null=True)),
                ('progress_value', models.IntegerField(blank=True, null=True)),
                ('progress_rate', models.IntegerField(blank=True, null=True)),
                ('progress_datetime', models.DateTimeField(blank=True, null=True)),
                ('synced_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('trophy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_trophies', to='trophies.trophy')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_trophies', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'trophies_usertrophy',
                'ordering': ['-earned_datetime'],
                'unique_together': {('user', 'trophy')},
            },
        ),
    ]
