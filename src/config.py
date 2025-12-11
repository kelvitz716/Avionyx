import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    
    # Parse comma-separated list of admin IDs
    admin_ids_str = os.getenv("ADMIN_IDS", "")
    ADMIN_IDS = [int(id.strip()) for id in admin_ids_str.split(",") if id.strip().isdigit()]

    if not TELEGRAM_TOKEN:
        raise ValueError("No TELEGRAM_TOKEN provided in .env file.")

# Global instance
cfg = Config()
