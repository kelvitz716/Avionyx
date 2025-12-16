#!/bin/bash

# Avionyx Restore Script

BACKUP_DIR="./backups"
DATA_DIR="./data"

if [ -z "$1" ]; then
    echo "📜 Available Backups:"
    if [ -d "$BACKUP_DIR" ]; then
        ls -lh "$BACKUP_DIR"/*.tar.gz 2>/dev/null
        if [ $? -ne 0 ]; then
            echo "   (No backups found)"
        fi
    else
        echo "   (No backup directory found)"
    fi
    echo ""
    echo "Usage: ./scripts/restore.sh <path_to_backup_file>"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Error: Backup file '$BACKUP_FILE' does not exist."
    exit 1
fi

echo "⚠️  WARNING: This will OVERWRITE current data in '$DATA_DIR'."
read -p "❓ Are you sure you want to proceed? (y/n): " confirm
if [[ "$confirm" != "y" ]]; then
    echo "🚫 Restore cancelled."
    exit 0
fi

echo "🛑 Stopping containers to ensure data integrity..."
docker-compose stop

echo "♻️  Restoring data..."
# Keep strict hierarchy? The backup script does `tar -czf ... ./data`. 
# So unpacking it in current dir should overwrite ./data if we are in project root.

# If we are running this from project root, and backup was made of ./data, 
# extracting it here will restore ./data.
tar -xzf "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "✅ Restore complete."
    echo "🚀 Restarting containers..."
    docker-compose up -d
    echo "✅ Done."
else
    echo "❌ Restore failed."
fi
