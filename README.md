# Avionyx - Poultry Farm Management Bot

A Telegram bot for managing poultry farm operations including egg collection, feed tracking, flock management, and reporting.

## Features

- 🥚 **Egg Collection** - Track daily egg production with breakage logging
- 🍽️ **Feed Management** - Record feed usage with cost calculations
- 🐥 **Flock Tracking** - Monitor flock additions, removals, and mortality
- 💰 **Sales Recording** - Track egg sales and income
- 📊 **Reports** - Daily, weekly, and monthly summaries
- 🔔 **Alerts** - Low stock and production anomaly detection
- 📜 **Audit Logs** - Track all user actions

## Quick Start

### Option 1: Docker (Recommended)

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in your Telegram bot token:
   ```bash
   cp .env.example .env
   nano .env  # Add your TELEGRAM_TOKEN and ADMIN_IDS
   ```

3. Start with Docker Compose:
   ```bash
   docker-compose up -d
   ```

4. View logs:
   ```bash
   docker-compose logs -f
   ```

### Option 2: Manual Setup

1. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment:
   ```bash
   cp .env.example .env
   nano .env  # Add your credentials
   ```

4. Run migrations (if needed):
   ```bash
   alembic upgrade head
   ```

5. Start the bot:
   ```bash
   python src/bot.py
   ```

## Configuration

| Variable | Description |
|----------|-------------|
| `TELEGRAM_TOKEN` | Bot token from @BotFather |
| `ADMIN_IDS` | Comma-separated Telegram user IDs with access |

## Database

The bot uses SQLite by default. The database file is `avionyx.db` in the project root (or `/app/data/avionyx.db` in Docker).

### Migrations

```bash
# Apply migrations
alembic upgrade head

# Create new migration after model changes
alembic revision --autogenerate -m "Description"

# Rollback last migration
alembic downgrade -1
```

## Testing

```bash
pytest tests/ -v
```

## License

MIT
