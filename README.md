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

### Option 1: One-Click Deployment (Recommended)

1. Clone the repository.
2. Run the deployment script:
   ```bash
   chmod +x scripts/deploy.sh
   ./scripts/deploy.sh
   ```
   _This script will guide you through setup. For help getting your Bot Token and Admin ID, see [docs/setup_credentials.md](docs/setup_credentials.md)._

### Option 2: Manual Deployment

If you prefer to run commands manually:

1. Copy `.env.example` to `.env` and fill in your credentials.
2. Create the data directory: `mkdir -p data`.
3. Build and proper start:
   ```bash
   docker-compose up -d --build
   ```

## Backup & Recovery

We provide automated scripts for data safety.

- **Backup**:
  ```bash
  ./scripts/backup.sh
  ```
  _Creates a `.tar.gz` archive in the `./backups` directory._

- **Restore**:
  ```bash
  ./scripts/restore.sh backups/avionyx_backup_<timestamp>.tar.gz
  ```
  _Restores the data folder from the archive._

For more details, see [docs/volumes_and_backups.md](docs/volumes_and_backups.md).

## Testing

```bash
pytest tests/ -v
```

## License

MIT
