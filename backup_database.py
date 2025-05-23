import os
import shutil
import schedule
import time
from datetime import datetime

# Path to the database file
db_path = os.path.join('instance', 'bib.db')
# Path to the backup directory
backup_dir = os.path.join('instance', 'backups')

# Ensure the backup directory exists
os.makedirs(backup_dir, exist_ok=True)

def backup_database():
    """Creates a backup of the database."""
    if os.path.exists(db_path):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'bib_backup_{timestamp}.db')
        shutil.copy2(db_path, backup_file)
        print(f"Backup created: {backup_file}")
    else:
        print("Database file not found. Backup skipped.")

# Schedule the backup every hour
schedule.every(1).hours.do(backup_database)

if __name__ == "__main__":
    print("Starting database backup scheduler...")
    while True:
        schedule.run_pending()
        time.sleep(1)
