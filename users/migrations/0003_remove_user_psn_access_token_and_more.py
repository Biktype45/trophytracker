# Generated by Django 5.2.1 on 2025-06-04 12:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_user_last_successful_sync_user_last_sync_attempt_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='psn_access_token',
        ),
        migrations.RemoveField(
            model_name='user',
            name='psn_profile_public',
        ),
        migrations.RemoveField(
            model_name='user',
            name='psn_refresh_token',
        ),
        migrations.RemoveField(
            model_name='user',
            name='psn_token_expires',
        ),
        migrations.RemoveField(
            model_name='user',
            name='sync_enabled',
        ),
        migrations.AlterField(
            model_name='user',
            name='psn_account_id',
            field=models.CharField(blank=True, max_length=100, null=True, unique=True),
        ),
    ]
