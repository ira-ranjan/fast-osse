#!/bin/bash

# --- CONFIGURATION ---
INPUT_DIR="/glade/derecho/scratch/iranjan/archive/weekly_eep/ocn/hist"
OUTPUT_DIR="/glade/derecho/scratch/iranjan/weekly_eep_osse/"
STATIC_FILE="/glade/derecho/scratch/iranjan/archive/EEP_MITgcm185Lvgrid_Whitt2026hgrid/ocn/hist/EEP_MITgcm185Lvgrid_Whitt2026hgrid.mom6.h.static.nc"
OCEAN_GEOM_FILE="/glade/derecho/scratch/iranjan/archive/EEP_MITgcm185Lvgrid_Whitt2026hgrid/ocn/hist/EEP_MITgcm185Lvgrid_Whitt2026hgrid.mom6.h.ocean_geometry.nc"
PMO_EXEC="/glade/work/iranjan/DART/models/MOM6/work/perfect_model_obs"
INPUT_NML="/glade/work/iranjan/fast-osse/input.nml"
# ---------------------

if [ ! -d "$INPUT_DIR" ]; then
    echo "ERROR: Input directory does not exist: $INPUT_DIR"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

for f in "$INPUT_DIR"/*; do
    # Ensure it is a file and not a directory
    if [ -f "$f" ]; then
        
        # Extract just the filename (e.g., "data.nc")
        fname="${f##*/}"
        
        # Get folder name without extension (e.g., "data")
        folder_name="${fname%.*}"
        
        # Define the path for the new specific subdirectory
        sub_dir="$OUTPUT_DIR/$folder_name"
        
        echo "Processing: $fname -> Creating: $sub_dir"
        
        # 1. Create the unique subdirectory inside the destination folder
        mkdir -p "$sub_dir"
        
        # 2. Move the original file from source into its new subdirectory
        ln -sf "$f" "$sub_dir/mom6.r.nc"
        
        # 3. Copy the three extra files into that same subdirectory
        ln -sf "$PMO_EXEC"  "$sub_dir/perfect_model_obs"
        ln -sf "$INPUT_NML" "$sub_dir/input.nml"
        ln -sf "$OCEAN_GEOM_FILE" "$sub_dir/ocean_geometry.nc"
        ln -sf "$STATIC_FILE" "$sub_dir/mom6.static.nc"
    fi
done
