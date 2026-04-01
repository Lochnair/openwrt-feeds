#!/bin/sh

# SPDX-License-Identifier: GPL-2.0-only
#
# Copyright (C) 2023 Nils Andreas Svee
# Copyright (C) 2026 Fabio Rieker


URL="https://raw.githubusercontent.com/Lochnair/sqm-autorate-rust/master/reflectors-icmp.csv"
RAM_FILE="/tmp/reflectors-icmp.csv"
TMP_FILE="/tmp/reflectors-icmp.csv.new"


# The reflectors file is so tiny,
# that checking if it got updated basically causes the same trafick than just downloading it.
# Ergo, I decided pulling it once a day is sustainabel enought. 

# Configuration
MAX_RETRIES=3
RETRY_DELAY=30  # Seconds
MIN_SIZE=2048   # 2KB minimum
STALE_IN_DAYS=3

update_success=0
attempt=1

# 1. Atomic Download Loop
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
    
    CURRENT_TIME=$(date +%s)
    FILE_TIME=$(date -r "$RAM_FILE" +%s)
    
    # Calculate difference in seconds, then convert to integer days
    AGE_SEC=$((CURRENT_TIME - FILE_TIME))
    AGE_DAYS=$((AGE_SEC / 86400))

    # Use -ge (greater than or equal to) because 3.1 days becomes 3 days
    if [ "$AGE_DAYS" -ge "$STALE_IN_DAYS" ]; then
        logger -t sqm-autorate "WARNING: Reflectors are STALE, update failed. Active list is $AGE_DAYS days old (Threshold: $STALE_DAYS)!"
    else
        logger -t sqm-autorate "INFO: Reflector update failed. Continuing with existing list."
    fi
fi