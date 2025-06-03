from django.core.management.base import BaseCommand
from django.db import connection

class UpdatePSNModelsCommand(BaseCommand):
    help = 'Update PSN models for PSNAWP compatibility'
    
    def handle(self, *args, **options):
        self.stdout.write("🔧 Updating PSN models for PSNAWP...")
        
        with connection.cursor() as cursor:
            # Add new fields to PSNToken if they don't exist
            try:
                cursor.execute("""
                    ALTER TABLE psn_integration_token 
                    ADD COLUMN IF NOT EXISTS npsso_token TEXT;
                """)
                self.stdout.write("✅ Added npsso_token field")
            except:
                self.stdout.write("⚠️  npsso_token field already exists")
            
            try:
                cursor.execute("""
                    ALTER TABLE psn_integration_token 
                    ADD COLUMN IF NOT EXISTS psnawp_version VARCHAR(20);
                """)
                self.stdout.write("✅ Added psnawp_version field")
            except:
                self.stdout.write("⚠️  psnawp_version field already exists")
            
            try:
                cursor.execute("""
                    ALTER TABLE psn_integration_token 
                    ADD COLUMN IF NOT EXISTS last_error TEXT;
                """)
                self.stdout.write("✅ Added last_error field")
            except:
                self.stdout.write("⚠️  last_error field already exists")
        
        self.stdout.write(self.style.SUCCESS("🎉 PSN models updated for PSNAWP!"))