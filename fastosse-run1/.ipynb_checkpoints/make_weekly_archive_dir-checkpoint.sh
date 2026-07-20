#!/bin/bash

# --- CONFIGURATION ---
SOURCE_DIR="/glade/derecho/scratch/iranjan/archive/EEP_MITgcm185Lvgrid_Whitt2026hgrid/ocn/hist"
DEST_DIR="/glade/derecho/scratch/iranjan/archive/weekly_eep/ocn/hist"
# 20 hours converted to minutes (20 * 60 = 1200)
TIME_MINUTES=1200 

# --- SAFETY CHECKS ---
# Ensure source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "Error: Source directory $SOURCE_DIR does not exist."
    exit 1
fi

# Create destination directory if it doesn't exist
if [ ! -d "$DEST_DIR" ]; then
    echo "Creating destination directory: $DEST_DIR"
    mkdir -p "$DEST_DIR"
fi

# --- EXECUTION ---
echo "Creating soft links in $DEST_DIR for files added to $SOURCE_DIR in the last 20 hours..."

# Convert source path to absolute path to prevent broken links
ABS_SOURCE_DIR=$(cd "$SOURCE_DIR" && pwd)

find "$ABS_SOURCE_DIR" -maxdepth 1 -type f -mmin -$TIME_MINUTES -exec ln -s -t "$DEST_DIR" {} +

echo "Done!"
