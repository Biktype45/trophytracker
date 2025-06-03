from django.core.management.base import BaseCommand
from psn_integration.models import PSNToken
from django.utils import timezone

class Command(BaseCommand):
    help = 'Refresh PSN authentication token for dedicated account'
    
    def handle(self, *args, **options):
        self.stdout.write("Manual PSN token refresh required.")
        self.stdout.write("Follow these steps:")
        self.stdout.write("1. Visit https://store.playstation.com and login with dedicated account")
        self.stdout.write("2. Visit https://ca.account.sony.com/api/v1/ssocookie")
        self.stdout.write("3. Copy the npsso token and run:")
        self.stdout.write("   python manage.py shell")
        self.stdout.write("   from psn_integration.services import PSNTokenManager")
        self.stdout.write("   PSNTokenManager().refresh_token('YOUR_NPSSO_TOKEN')")