#!/bin/bash

# Avionyx Backup Script

BACKUP_DIR="./backups"
DATA_DIR="./data"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/avionyx_backup_$TIMESTAMP.tar.gz"

mkdir -p "$BACKUP_DIR"

if [ ! -d "$DATA_DIR" ]; then
    echo "❌ Data directory '$DATA_DIR' not found. Is the bot deployed?"
    exit 1
fi

echo "📦 Creating backup of '$DATA_DIR'..."

# Create tarball
tar -czf "$BACKUP_FILE" "$DATA_DIR"

if [ $? -eq 0 ]; then
    echo "✅ Backup created successfully: $BACKUP_FILE"
    
    # Optional: Rotate backups (keep last 5)
    echo "🧹 Cleaning up old backups (keeping last 5)..."
    ls -tp "$BACKUP_DIR"/avionyx_backup_*.tar.gz | grep -v '/$' | tail -n +6 | xargs -I {} rm -- "{}"
else
    echo "❌ Backup failed."
    exit 1
fi
