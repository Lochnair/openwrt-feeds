#!/bin/sh

# SPDX-License-Identifier: GPL-2.0-only
#
# Copyright (C) 2023 Nils Andreas Svee
# Copyright (C) 2026 Fabio Rieker


URL="https://raw.githubusercontent.com/Lochnair/sqm-autorate-rust/master/reflectors-icmp.csv"
RUN_DIR="/var/run/sqm-autorate"
RAM_FILE="$RUN_DIR/reflectors-icmp.csv"
# Generating temporary files in the same directory as their target guarantees that
# standard \`mv\` commands perform a purely atomic kernel rename() operation.
# This ensures zero window where the Rust binary could read a partially written file.
TMP_FILE="$RUN_DIR/reflectors-icmp.csv.new"


# The reflectors file is so tiny,
# that checking if it got updated basically causes the same traffic than just downloading it.
# Ergo, I decided pulling it once a day is sustainable enough. 

# Configuration
MAX_RETRIES=3
RETRY_DELAY=30  # Seconds
MIN_SIZE=2048   # 2KB minimum
STALE_IN_DAYS=3

update_success=0
attempt=1

# 1. Atomic Download Loop
mkdir -p "$RUN_DIR"

while [ $attempt -le $MAX_RETRIES ]; do
    if wget -q -O "$TMP_FILE" "$URL"; then
        FILE_SIZE=$(wc -c < "$TMP_FILE")
        
        if [ "$FILE_SIZE" -gt "$MIN_SIZE" ]; then
            mv "$TMP_FILE" "$RAM_FILE"
            logger -t sqm-autorate "INFO: Reflectors updated successfully ($FILE_SIZE bytes ... will now restart sqm-autorate)."
            /etc/init.d/sqm-autorate restart
            update_success=1
            break
        fi
    fi
    
    # Silently increment and wait. No log spam.
    attempt=$((attempt + 1))
    [ $attempt -le $MAX_RETRIES ] && sleep $RETRY_DELAY
done

# 2. Total Failure Handling (Stale Check)
if [ "$update_success" -ne 1 ]; then
    rm -f "$TMP_FILE"
    
    if [ ! -f "$RAM_FILE" ]; then
        logger -t sqm-autorate "WARNING: Update failed & RAM copy of reflectors entirely missing! Restarting service to attemt self-heal."
        /etc/init.d/sqm-autorate restart
        exit 1
    fi
    
    CURRENT_TIME=$(date +%s)
    FILE_TIME=$(date -r "$RAM_FILE" +%s)
    AGE_DAYS=$(( (CURRENT_TIME - FILE_TIME) / 86400 ))

    # Use -ge (greater than or equal to) because 3.1 days becomes 3 days
    if [ "$AGE_DAYS" -ge "$STALE_IN_DAYS" ]; then
        logger -t sqm-autorate "WARNING: Reflectors are STALE, update failed. Active list is $AGE_DAYS days old (Threshold: $STALE_DAYS)!"
    else
        logger -t sqm-autorate "INFO: Update failed. Continuing with existing $AGE_DAYS days old list."
    fi
fi