# Avionyx Data Management: Volumes & Backups

## Hardware Failure & Recovery Strategy

This system is designed to be easily recoverable in case of hardware failure or server migration. All critical data is stored in a single directory: `./data` in your project root.

### The `./data` Directory

When you run `docker-compose up`, the `data/` folder on your host machine is "bind-mounted" into the container at `/app/data`. This means:
1. The database file `avionyx.db` lives directly on your server's disk in the `data/` folder.
2. If you delete the Docker container, your data persists.
3. If you move the `data/` folder to a new server, your data moves with it.

### Backup Procedure

We have provided a script to automate backups.

1. Run `./scripts/backup.sh`
2. This creates a compressed archive in `backups/avionyx_backup_YYYYMMDD_HHMMSS.tar.gz`.
3. **Recommendation**: Copy these `.tar.gz` files to an external location (cloud storage, another server, or your local machine) periodically.

### Restoration Procedure

To restore from a backup (e.g., after moving to a new server):

1. **Stop the bot**: `docker-compose stop` (handled automatically by the script, but good to know).
2. **Run Restore**: `./scripts/restore.sh backups/avionyx_backup_YYYYMMDD_HHMMSS.tar.gz`
3. **Confirm**: The script will ask for confirmation before overwriting the current `data/` folder.
4. **Restart**: The script will restart the bot automatically.

### Migration to Odoo (Future Proofing)

If you decide to scale beyond 1000 birds and move to Odoo:
1. Use the **Export Data (CSV)** feature in the Reports menu of the bot.
2. This generates a CSV file containing all daily entries (Sales, Feed, Production, Mortality).
3. This CSV format is generic and can be easily imported into Odoo or any other ERP system.
