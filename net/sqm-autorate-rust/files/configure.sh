#!/bin/sh
#   configure.sh: configures /etc/config/sqm-autorate-rust
#
#   Copyright (C) 2022-2024
#       Charles Corrigan mailto:chas-iot@runegate.org (github @chas-iot)
#       Mark Baker mailto:mark@vpost.net (github @Fail-Safe)
#
#   This Source Code Form is subject to the terms of the Mozilla Public
#   License, v. 2.0. If a copy of the MPL was not distributed with this
#   file, You can obtain one at https://mozilla.org/MPL/2.0/.

# shellcheck disable=SC3045

SERVICE_NAME="sqm-autorate-rust"
CONFIG_FILE="/etc/config/${SERVICE_NAME}"
CONFIGURE_SCRIPT="/usr/lib/${SERVICE_NAME}/configure.sh"

print_rerun() {
    echo "

================================================================================

To re-run this configuration at any time, type the following command at the
router shell prompt: '${CONFIGURE_SCRIPT}'

"
}

handle_ctlc() {
    echo "

SIGINT..."
    print_rerun
    trap "-" 2
    # shellcheck disable=SC2242
    exit -1 2>/dev/null
}
trap "handle_ctlc" 2

echo "
>> Starting the 'sqm-autorate-rust' configuration script.

"

if [ ! -w "${CONFIG_FILE}" ]; then
    echo "${CONFIG_FILE} not found or not writable - exiting with no change
"
    # shellcheck disable=SC2242
    exit -1 2>/dev/null
fi

read -r -p "You may interrupt this script and re-run later. To re-run, at the router shell
prompt, type '${CONFIGURE_SCRIPT}'

Press return, or type y or yes if you want guided assistance to set up a ready
   to run configuration file for 'sqm-autorate-rust' [Y/n]: " do_config
do_config=$(echo "${do_config}" | awk '{ print tolower($0) }')
if [ -z "${do_config}" ] || [ "${do_config}" = "y" ] || [ "${do_config}" = "yes" ]; then
    # shellcheck disable=SC1091
    . /lib/functions/network.sh
    network_flush_cache
    network_find_wan WAN_IF
    WAN_DEVICE=$(uci -q get network."${WAN_IF}".device)

    # Read existing settings
    SETTINGS_UPLOAD_DEVICE=$(uci -q get "${SERVICE_NAME}.@network[0].upload_interface")
    SETTINGS_DOWNLOAD_DEVICE=$(uci -q get "${SERVICE_NAME}.@network[0].download_interface")
    SETTINGS_UPLOAD_SPEED=$(uci -q get "${SERVICE_NAME}.@network[0].upload_base_kbits")
    SETTINGS_DOWNLOAD_SPEED=$(uci -q get "${SERVICE_NAME}.@network[0].download_base_kbits")
    SETTINGS_LOG_LEVEL=$(uci -q get "${SERVICE_NAME}.@output[0].log_level")
    SETTINGS_USE_SYSLOG=$(uci -q get "${SERVICE_NAME}.@output[0].use_syslog")
    SETTINGS_OBS_ENABLED=$(uci -q get "${SERVICE_NAME}.@observability[0].enabled")
    SETTINGS_OBS_PROTOCOL=$(uci -q get "${SERVICE_NAME}.@observability[0].protocol")
    SETTINGS_OBS_HOST=$(uci -q get "${SERVICE_NAME}.@observability[0].host")
    SETTINGS_OBS_PORT=$(uci -q get "${SERVICE_NAME}.@observability[0].port")
    SETTINGS_MEASUREMENT_TYPE=$(uci -q get "${SERVICE_NAME}.@advanced_settings[0].measurement_type")
    SETTINGS_NUM_REFLECTORS=$(uci -q get "${SERVICE_NAME}.@advanced_settings[0].num_reflectors")
    SETTINGS_DRY_RUN=$(uci -q get "${SERVICE_NAME}.@advanced_settings[0].dry_run")

    INPUT=Y
    while [ $INPUT = "Y" ]; do

        # =====================================================================
        # NETWORK INTERFACES
        # =====================================================================
        echo "
This script does not reliably handle advanced or complex configurations of CAKE
You may be required to manually find and type the network device names

Here's the list of network devices known to CAKE:
$(tc qdisc | grep -i cake | grep -o ' dev [[:alnum:]]* ' | cut -d ' ' -f 3)"

        if [ -n "${SETTINGS_UPLOAD_DEVICE}" ]; then
            UPLOAD_DEVICE=$(tc qdisc | grep -i cake | grep -o -- " dev ${SETTINGS_UPLOAD_DEVICE} " | cut -d ' ' -f 3)
        fi
        if [ -z "${UPLOAD_DEVICE}" ]; then
            UPLOAD_DEVICE=$(tc qdisc | grep -i cake | grep -o -- " dev ${WAN_DEVICE} " | cut -d ' ' -f 3)
        fi

        if [ -n "${UPLOAD_DEVICE}" ]; then
            read -r -p "
press return to accept detected network upload device [${UPLOAD_DEVICE}]: " ACCEPT
            ACCEPT=$(echo "${ACCEPT}" | awk '{ print tolower($0) }')
            if [ -z "${ACCEPT}" ]; then
                GOOD=Y
            fi
        else
            echo "unable to automatically detect the network upload device"
            GOOD=N
        fi
        while [ "$GOOD" = "N" ]; do
            read -r -p "
These are the network devices known to CAKE
$(tc qdisc | grep -i cake | grep -o ' dev [[:alnum:]]* ' | cut -d ' ' -f 3)

Please type in the upload network device name: " UPLOAD_DEVICE
            x=$(tc qdisc | grep -i cake | grep -o -- " dev ${UPLOAD_DEVICE} " | cut -d ' ' -f 3)
            if [ -n "${x}" ]; then
                GOOD=Y
            fi
        done

        if [ -n "${SETTINGS_DOWNLOAD_DEVICE}" ]; then
            DOWNLOAD_DEVICE=$(tc qdisc | grep -i cake | grep -o -- " dev ${SETTINGS_DOWNLOAD_DEVICE} " | cut -d ' ' -f 3)
        fi
        if [ -z "${DOWNLOAD_DEVICE}" ]; then
            DOWNLOAD_DEVICE=$(tc qdisc | grep -i cake | grep -o -- " dev ifb4${UPLOAD_DEVICE} " | cut -d ' ' -f 3)
        fi
        if [ -z "${DOWNLOAD_DEVICE}" ]; then
            DOWNLOAD_DEVICE=$(tc qdisc | grep -i cake | grep -o -- " dev veth.* " | cut -d ' ' -f 3)
        fi

        if [ -n "${DOWNLOAD_DEVICE}" ]; then
            read -r -p "
press return to accept detected network download device [${DOWNLOAD_DEVICE}]: " ACCEPT
            ACCEPT=$(echo "${ACCEPT}" | awk '{ print tolower($0) }')
            if [ -z "${ACCEPT}" ]; then
                GOOD=Y
            fi
        else
            echo "unable to automatically detect the network download device"
            GOOD=N
        fi
        while [ "$GOOD" = "N" ]; do
            read -r -p "
These are the network devices known to CAKE
$(tc qdisc | grep -i cake | grep -o ' dev [[:alnum:]]* ' | cut -d ' ' -f 3)

Please type in the download network device name: " DOWNLOAD_DEVICE
            x=$(tc qdisc | grep -i cake | grep -o -- " dev ${DOWNLOAD_DEVICE} " | cut -d ' ' -f 3)
            if [ -n "${x}" ]; then
                GOOD=Y
            fi
        done

        # =====================================================================
        # SPEEDS
        # =====================================================================
        echo "
Please type in the maximum speed that you reasonably expect from your network
on a good day. This should be a little lower than the speed advertised by your
ISP, unless you have specific knowledge otherwise. The speed is measured in
kbits per second, where 1 mbit = 1000 kbits, and 1 gbit = 1000000 kbits.
The speed should be input with just digits and no punctuation
"
        BAD=Y
        # shellcheck disable=SC3010
        if [ -n "${SETTINGS_UPLOAD_SPEED}" ] && [[ $SETTINGS_UPLOAD_SPEED =~ ^[0-9]+$ ]]; then
            DEFAULT=" [${SETTINGS_UPLOAD_SPEED}]"
        else
            DEFAULT=""
        fi
        while [ $BAD = "Y" ]; do
            read -r -p "upload speed${DEFAULT}: " UPLOAD_SPEED
            # shellcheck disable=SC3010
            if [ -n "${SETTINGS_UPLOAD_SPEED}" ] && [ -z "${UPLOAD_SPEED}" ]; then
                UPLOAD_SPEED=$SETTINGS_UPLOAD_SPEED
                BAD=N
            elif [[ $UPLOAD_SPEED =~ ^[0-9]+$ ]]; then
                BAD=N
            else
                echo "
please input digits only"
            fi
        done

        BAD=Y
        while [ $BAD = "Y" ]; do
            # shellcheck disable=SC3010
            if [ -n "${SETTINGS_DOWNLOAD_SPEED}" ] && [[ $SETTINGS_DOWNLOAD_SPEED =~ ^[0-9]+$ ]]; then
                DEFAULT=" [${SETTINGS_DOWNLOAD_SPEED}]"
            else
                DEFAULT=""
            fi
            read -r -p "download speed${DEFAULT}: " DOWNLOAD_SPEED
            # shellcheck disable=SC3010
            if [ -n "${SETTINGS_DOWNLOAD_SPEED}" ] && [ -z "${DOWNLOAD_SPEED}" ]; then
                DOWNLOAD_SPEED=$SETTINGS_DOWNLOAD_SPEED
                BAD=N
            elif [[ $DOWNLOAD_SPEED =~ ^[0-9]+$ ]]; then
                BAD=N
            else
                echo "
please input digits only"
            fi
        done

        echo "
The minimum tolerable speed is calculated from the speeds input above.
You may override the recommendation with care. The minimum must be lower than
the original speed. The input may be recalculated slightly, and in that case,
will be re-displayed for confirmation
"
        if [ "$UPLOAD_SPEED" -le 3000 ]; then
            UPLOAD_PERCENT=75
            UPLOAD_MINIMUM=$((UPLOAD_SPEED * 3 / 4))
            UPLOAD_HARD_MINIMUM=$UPLOAD_MINIMUM
        elif [ "$UPLOAD_SPEED" -le 11250 ]; then
            UPLOAD_PERCENT=$((2250 * 100 / UPLOAD_SPEED))
            UPLOAD_MINIMUM=$((UPLOAD_SPEED * UPLOAD_PERCENT / 100))
            t=$((UPLOAD_MINIMUM * 100 / UPLOAD_PERCENT))
            while [ $t -lt "$UPLOAD_SPEED" ] || [ $UPLOAD_MINIMUM -lt 2250 ]; do
                UPLOAD_PERCENT=$((UPLOAD_PERCENT + 1))
                UPLOAD_MINIMUM=$((UPLOAD_SPEED * UPLOAD_PERCENT / 100))
                t=$((UPLOAD_MINIMUM * 100 / UPLOAD_PERCENT))
            done
            UPLOAD_HARD_MINIMUM=$UPLOAD_MINIMUM
        else
            UPLOAD_MINIMUM=$((UPLOAD_SPEED / 5))
            UPLOAD_PERCENT=20
            UPLOAD_HARD_MINIMUM=$((UPLOAD_SPEED / 10))
        fi

        BAD=Y
        while [ $BAD = "Y" ]; do
            read -r -p "upload minimum speed [${UPLOAD_MINIMUM}]: " OVERRIDE_UPLOAD
            # shellcheck disable=SC3010
            if [ -z "${OVERRIDE_UPLOAD}" ]; then
                BAD=N
            elif [[ $OVERRIDE_UPLOAD =~ ^[0-9]+$ ]]; then
                if [ "$OVERRIDE_UPLOAD" -lt "$UPLOAD_SPEED" ]; then
                    if [ "$OVERRIDE_UPLOAD" -ne $UPLOAD_MINIMUM ]; then
                        UPLOAD_PERCENT=$((OVERRIDE_UPLOAD * 100 / UPLOAD_SPEED))
                        UPLOAD_MINIMUM=$((UPLOAD_SPEED * UPLOAD_PERCENT / 100))
                        if [ $UPLOAD_PERCENT -lt 10 ]; then
                            UPLOAD_PERCENT=10
                        elif [ $UPLOAD_PERCENT -gt 75 ]; then
                            UPLOAD_PERCENT=75
                        elif [ $UPLOAD_MINIMUM -lt $UPLOAD_HARD_MINIMUM ]; then
                            UPLOAD_MINIMUM=$UPLOAD_HARD_MINIMUM
                            UPLOAD_PERCENT=$((UPLOAD_MINIMUM * 100 / UPLOAD_SPEED))
                        else
                            UPLOAD_MINIMUM=$((UPLOAD_SPEED * UPLOAD_PERCENT / 100))
                            t=$((UPLOAD_MINIMUM * 100 / UPLOAD_PERCENT))
                            if [ $t -lt "$UPLOAD_SPEED" ]; then
                                UPLOAD_PERCENT=$((UPLOAD_PERCENT + 1))
                            fi
                        fi
                        UPLOAD_MINIMUM=$((UPLOAD_SPEED * UPLOAD_PERCENT / 100))
                        echo "
please confirm recalculated value"
                    else
                        BAD=N
                    fi
                else
                    echo "
please input digits only and ensure that the minimum is less than the original"
                fi
            fi
        done

        if [ "$DOWNLOAD_SPEED" -le 3000 ]; then
            DOWNLOAD_PERCENT=75
            DOWNLOAD_MINIMUM=$((DOWNLOAD_SPEED * 3 / 4))
            DOWNLOAD_HARD_MINIMUM=$DOWNLOAD_MINIMUM
        elif [ "$DOWNLOAD_SPEED" -le 11250 ]; then
            DOWNLOAD_PERCENT=$((2250 * 100 / DOWNLOAD_SPEED))
            DOWNLOAD_MINIMUM=$((DOWNLOAD_SPEED * DOWNLOAD_PERCENT / 100))
            t=$((DOWNLOAD_MINIMUM * 100 / DOWNLOAD_PERCENT))
            while [ $t -lt "$DOWNLOAD_SPEED" ] || [ $DOWNLOAD_MINIMUM -lt 2250 ]; do
                DOWNLOAD_PERCENT=$((DOWNLOAD_PERCENT + 1))
                DOWNLOAD_MINIMUM=$((DOWNLOAD_SPEED * DOWNLOAD_PERCENT / 100))
                t=$((DOWNLOAD_MINIMUM * 100 / DOWNLOAD_PERCENT))
            done
            DOWNLOAD_HARD_MINIMUM=$DOWNLOAD_MINIMUM
        else
            DOWNLOAD_MINIMUM=$((DOWNLOAD_SPEED / 5))
            DOWNLOAD_PERCENT=20
            DOWNLOAD_HARD_MINIMUM=$((DOWNLOAD_SPEED / 10))
        fi

        BAD=Y
        while [ $BAD = "Y" ]; do
            read -r -p "download minimum speed [${DOWNLOAD_MINIMUM}]: " OVERRIDE_DOWNLOAD
            # shellcheck disable=SC3010
            if [ -z "${OVERRIDE_DOWNLOAD}" ]; then
                BAD=N
            elif [[ $OVERRIDE_DOWNLOAD =~ ^[0-9]+$ ]]; then
                if [ "$OVERRIDE_DOWNLOAD" -lt "$DOWNLOAD_SPEED" ]; then
                    if [ "$OVERRIDE_DOWNLOAD" -ne $DOWNLOAD_MINIMUM ]; then
                        DOWNLOAD_PERCENT=$((OVERRIDE_DOWNLOAD * 100 / DOWNLOAD_SPEED))
                        DOWNLOAD_MINIMUM=$((DOWNLOAD_SPEED * DOWNLOAD_PERCENT / 100))
                        if [ $DOWNLOAD_PERCENT -lt 10 ]; then
                            DOWNLOAD_PERCENT=10
                        elif [ $DOWNLOAD_PERCENT -gt 70 ]; then
                            DOWNLOAD_PERCENT=75
                        elif [ $DOWNLOAD_MINIMUM -lt $DOWNLOAD_HARD_MINIMUM ]; then
                            DOWNLOAD_MINIMUM=$DOWNLOAD_HARD_MINIMUM
                            DOWNLOAD_PERCENT=$((DOWNLOAD_MINIMUM * 100 / DOWNLOAD_SPEED))
                        else
                            DOWNLOAD_MINIMUM=$((DOWNLOAD_SPEED * DOWNLOAD_PERCENT / 100))
                            t=$((DOWNLOAD_MINIMUM * 100 / DOWNLOAD_PERCENT))
                            if [ $t -lt "$DOWNLOAD_SPEED" ]; then
                                DOWNLOAD_PERCENT=$((DOWNLOAD_PERCENT + 1))
                            fi
                        fi
                        DOWNLOAD_MINIMUM=$((DOWNLOAD_SPEED * DOWNLOAD_PERCENT / 100))
                        echo "
please confirm recalculated value"
                    else
                        BAD=N
                    fi
                else
                    echo "
please input digits only and ensure that the minimum is less than the original"
                fi
            fi
        done

        # =====================================================================
        # OUTPUT / LOGGING
        # =====================================================================
        GOOD=N
        while [ $GOOD = "N" ]; do
            read -r -p "
sqm-autorate-rust logging uses storage on the router
Choose one of the following log levels
- FATAL     - minimal
- ERROR     - minimal
- WARN      - minimal, recommended
- INFO      - typically a very few Kb per day showing settings changes, however
                could be more depending on the network activity
- DEBUG     - for error finding, developers; use for short periods only
- TRACE     - for developers; use for short periods only

Type in one of the log levels, or press return to accept [${SETTINGS_LOG_LEVEL:-WARN}]: " LOG_LEVEL
            LOG_LEVEL=$(echo "${LOG_LEVEL}" | awk '{ print toupper($0) }')
            if [ -z "${LOG_LEVEL}" ]; then
                LOG_LEVEL="${SETTINGS_LOG_LEVEL:-WARN}"
                GOOD=Y
            elif [ "${LOG_LEVEL}" = "FATAL" ] ||
                [ "${LOG_LEVEL}" = "ERROR" ] ||
                [ "${LOG_LEVEL}" = "WARN" ] ||
                [ "${LOG_LEVEL}" = "INFO" ] ||
                [ "${LOG_LEVEL}" = "DEBUG" ] ||
                [ "${LOG_LEVEL}" = "TRACE" ]; then
                GOOD=Y
            fi
        done

        read -r -p "
sqm-autorate-rust can output log entries to your system log (syslog).

Type y or yes to choose to output log entries to syslog [y/N]: " SYS_LOG
        SYS_LOG=$(echo "${SYS_LOG}" | awk '{ print tolower($0) }')
        if [ "${SYS_LOG}" = "y" ] || [ "${SYS_LOG}" = "yes" ]; then
            USE_SYSLOG='1'
        else
            USE_SYSLOG='0'
        fi

        read -r -p "
sqm-autorate-rust can output statistics that may be analysed with Julia scripts
( https://github.com/sqm-autorate/sqm-autorate/tree/main#graphical-analysis ),
spreadsheets, or other statistical software.
The statistics use about 12 Mb of storage per day on the router.

Type y or yes to choose to output the statistics [y/N]: " STATS
        STATS=$(echo "${STATS}" | awk '{ print tolower($0) }')
        if [ "${STATS}" = "y" ] || [ "${STATS}" = "yes" ]; then
            SUPPRESS_STATISTICS='false'
        else
            SUPPRESS_STATISTICS='true'
        fi

        # =====================================================================
        # MEASUREMENT TYPE
        # =====================================================================
        GOOD=N
        while [ $GOOD = "N" ]; do
            read -r -p "
Choose the measurement method sqm-autorate-rust will use to estimate one-way delay:
- icmp-timestamps  - uses ICMP timestamp requests; most accurate, recommended
- icmp             - uses ICMP echo (ping); splits RTT 50/50, less accurate

Type in one of the above, or press return to accept [${SETTINGS_MEASUREMENT_TYPE:-icmp-timestamps}]: " MEASUREMENT_TYPE
            MEASUREMENT_TYPE=$(echo "${MEASUREMENT_TYPE}" | awk '{ print tolower($0) }')
            if [ -z "${MEASUREMENT_TYPE}" ]; then
                MEASUREMENT_TYPE="${SETTINGS_MEASUREMENT_TYPE:-icmp-timestamps}"
                GOOD=Y
            elif [ "${MEASUREMENT_TYPE}" = "icmp-timestamps" ] ||
                [ "${MEASUREMENT_TYPE}" = "icmp" ]; then
                GOOD=Y
            else
                echo "
please enter 'icmp-timestamps' or 'icmp'"
            fi
        done

        # =====================================================================
        # NUM REFLECTORS
        # =====================================================================
        BAD=Y
        while [ $BAD = "Y" ]; do
            read -r -p "
Number of reflectors to use for latency measurement (3-20, default ${SETTINGS_NUM_REFLECTORS:-5}): " NUM_REFLECTORS
            # shellcheck disable=SC3010
            if [ -z "${NUM_REFLECTORS}" ]; then
                NUM_REFLECTORS="${SETTINGS_NUM_REFLECTORS:-5}"
                BAD=N
            elif [[ $NUM_REFLECTORS =~ ^[0-9]+$ ]] && [ "$NUM_REFLECTORS" -ge 3 ] && [ "$NUM_REFLECTORS" -le 20 ]; then
                BAD=N
            else
                echo "
please input a number between 3 and 20"
            fi
        done

        # =====================================================================
        # DRY RUN
        # =====================================================================
        read -r -p "
Dry-run / monitoring mode: sqm-autorate-rust will measure latency and calculate
rate adjustments but will NOT actually change qdisc rates. Useful for
observing behaviour before committing.

Type y or yes to enable dry-run mode [y/N]: " DRY_RUN_INPUT
        DRY_RUN_INPUT=$(echo "${DRY_RUN_INPUT}" | awk '{ print tolower($0) }')
        if [ "${DRY_RUN_INPUT}" = "y" ] || [ "${DRY_RUN_INPUT}" = "yes" ]; then
            DRY_RUN='true'
        else
            DRY_RUN='false'
        fi

        # =====================================================================
        # OBSERVABILITY
        # =====================================================================
        read -r -p "
sqm-autorate-rust can export metrics in InfluxDB line protocol to a remote
collector (e.g. Telegraf, InfluxDB, Grafana Agent). This is optional.

Type y or yes to configure observability [y/N]: " OBS_INPUT
        OBS_INPUT=$(echo "${OBS_INPUT}" | awk '{ print tolower($0) }')
        if [ "${OBS_INPUT}" = "y" ] || [ "${OBS_INPUT}" = "yes" ]; then
            OBS_ENABLED='true'

            GOOD=N
            while [ $GOOD = "N" ]; do
                read -r -p "
Observability transport protocol:
- udp  - lower overhead, packets may be lost (recommended for LAN collectors)
- tcp  - reliable delivery, adds reconnect logic

Type 'udp' or 'tcp', or press return to accept [${SETTINGS_OBS_PROTOCOL:-udp}]: " OBS_PROTOCOL
                OBS_PROTOCOL=$(echo "${OBS_PROTOCOL}" | awk '{ print tolower($0) }')
                if [ -z "${OBS_PROTOCOL}" ]; then
                    OBS_PROTOCOL="${SETTINGS_OBS_PROTOCOL:-udp}"
                    GOOD=Y
                elif [ "${OBS_PROTOCOL}" = "udp" ] || [ "${OBS_PROTOCOL}" = "tcp" ]; then
                    GOOD=Y
                else
                    echo "
please enter 'udp' or 'tcp'"
                fi
            done

            BAD=Y
            while [ $BAD = "Y" ]; do
                read -r -p "
Collector hostname or IP address [${SETTINGS_OBS_HOST:-}]: " OBS_HOST
                if [ -z "${OBS_HOST}" ] && [ -n "${SETTINGS_OBS_HOST}" ]; then
                    OBS_HOST="${SETTINGS_OBS_HOST}"
                    BAD=N
                elif [ -n "${OBS_HOST}" ]; then
                    BAD=N
                else
                    echo "
a hostname or IP address is required"
                fi
            done

            BAD=Y
            while [ $BAD = "Y" ]; do
                read -r -p "
Collector port [${SETTINGS_OBS_PORT:-8089}]: " OBS_PORT
                # shellcheck disable=SC3010
                if [ -z "${OBS_PORT}" ]; then
                    OBS_PORT="${SETTINGS_OBS_PORT:-8089}"
                    BAD=N
                elif [[ $OBS_PORT =~ ^[0-9]+$ ]] && [ "$OBS_PORT" -ge 1 ] && [ "$OBS_PORT" -le 65535 ]; then
                    BAD=N
                else
                    echo "
please input a valid port number (1-65535)"
                fi
            done

            echo "
Which metrics should be exported? (press return to accept defaults)
"
            read -r -p "Export rate metrics (dl/ul kbps, load) - recommended [Y/n]: " OBS_RATES
            OBS_RATES=$(echo "${OBS_RATES}" | awk '{ print tolower($0) }')
            if [ -z "${OBS_RATES}" ] || [ "${OBS_RATES}" = "y" ] || [ "${OBS_RATES}" = "yes" ]; then
                OBS_EXPORT_RATES='true'
            else
                OBS_EXPORT_RATES='false'
            fi

            read -r -p "Export per-reflector ping metrics (RTT, OWD) [y/N]: " OBS_PINGS
            OBS_PINGS=$(echo "${OBS_PINGS}" | awk '{ print tolower($0) }')
            if [ "${OBS_PINGS}" = "y" ] || [ "${OBS_PINGS}" = "yes" ]; then
                OBS_EXPORT_PINGS='true'
            else
                OBS_EXPORT_PINGS='false'
            fi

            read -r -p "Export per-reflector baseline EWMA metrics [y/N]: " OBS_BASELINE
            OBS_BASELINE=$(echo "${OBS_BASELINE}" | awk '{ print tolower($0) }')
            if [ "${OBS_BASELINE}" = "y" ] || [ "${OBS_BASELINE}" = "yes" ]; then
                OBS_EXPORT_BASELINE='true'
            else
                OBS_EXPORT_BASELINE='false'
            fi

            read -r -p "Export lifecycle events (start, stop, reselection) - recommended [Y/n]: " OBS_EVENTS
            OBS_EVENTS=$(echo "${OBS_EVENTS}" | awk '{ print tolower($0) }')
            if [ -z "${OBS_EVENTS}" ] || [ "${OBS_EVENTS}" = "y" ] || [ "${OBS_EVENTS}" = "yes" ]; then
                OBS_EXPORT_EVENTS='true'
            else
                OBS_EXPORT_EVENTS='false'
            fi

        else
            OBS_ENABLED='false'
            OBS_PROTOCOL="${SETTINGS_OBS_PROTOCOL:-udp}"
            OBS_HOST="${SETTINGS_OBS_HOST:-}"
            OBS_PORT="${SETTINGS_OBS_PORT:-8089}"
            OBS_EXPORT_RATES='true'
            OBS_EXPORT_PINGS='false'
            OBS_EXPORT_BASELINE='false'
            OBS_EXPORT_EVENTS='true'
        fi

        # =====================================================================
        # SERVICE START
        # =====================================================================
        if [ ! -x "/etc/init.d/${SERVICE_NAME}" ]; then
            echo "
/etc/init.d/${SERVICE_NAME} - not found or not executable, skipping (auto)start"
        else
            read -r -p "
Do you want to automatically start 'sqm-autorate-rust' at reboot [Y/n]: " STARTAUTO
            STARTAUTO=$(echo "${STARTAUTO}" | awk '{ print tolower($0) }')
            if [ -z "${STARTAUTO}" ] || [ "${STARTAUTO}" = "y" ] || [ "${STARTAUTO}" = "yes" ]; then
                START_AUTO=Yes
            else
                START_AUTO=No
            fi

            read -r -p "
Do you want to start 'sqm-autorate-rust' now [Y/n]: " STARTNOW
            STARTNOW=$(echo "${STARTNOW}" | awk '{ print tolower($0) }')
            if [ -z "${STARTNOW}" ] || [ "${STARTNOW}" = "y" ] || [ "${STARTNOW}" = "yes" ]; then
                START_NOW=Yes
            else
                START_NOW=No
            fi
        fi

        # =====================================================================
        # CONFIRMATION SUMMARY
        # =====================================================================
        read -r -p "

================================================================================

Settings:

      UPLOAD DEVICE: ${UPLOAD_DEVICE}
    DOWNLOAD DEVICE: ${DOWNLOAD_DEVICE}

       UPLOAD SPEED: ${UPLOAD_SPEED}
     UPLOAD PERCENT: ${UPLOAD_PERCENT}
     UPLOAD MINIMUM: ${UPLOAD_MINIMUM}

     DOWNLOAD SPEED: ${DOWNLOAD_SPEED}
   DOWNLOAD PERCENT: ${DOWNLOAD_PERCENT}
   DOWNLOAD MINIMUM: ${DOWNLOAD_MINIMUM}

          LOG LEVEL: ${LOG_LEVEL}
         USE SYSLOG: $(if [ "${USE_SYSLOG}" = "1" ]; then echo 'Yes'; else echo 'No'; fi)
SUPPRESS STATISTICS: ${SUPPRESS_STATISTICS}

   MEASUREMENT TYPE: ${MEASUREMENT_TYPE}
     NUM REFLECTORS: ${NUM_REFLECTORS}
           DRY RUN: ${DRY_RUN}

OBSERVABILITY ENABLED: ${OBS_ENABLED}
$(if [ "${OBS_ENABLED}" = "true" ]; then
echo "     OBS PROTOCOL: ${OBS_PROTOCOL}
         OBS HOST: ${OBS_HOST}
         OBS PORT: ${OBS_PORT}
     EXPORT RATES: ${OBS_EXPORT_RATES}
     EXPORT PINGS: ${OBS_EXPORT_PINGS}
  EXPORT BASELINE: ${OBS_EXPORT_BASELINE}
    EXPORT EVENTS: ${OBS_EXPORT_EVENTS}"
fi)

Start automatically: ${START_AUTO}
          Start now: ${START_NOW}

Type y or yes to confirm the above input and continue;
  <ctrl-c> to interrupt and exit;  or
  anything else to start over [y/N]: " RESPONSE
        RESPONSE=$(echo "${RESPONSE}" | awk '{ print tolower($0) }')
        if [ "${RESPONSE}" = "y" ] || [ "${RESPONSE}" = "yes" ]; then
            INPUT=N
        else
            INPUT=Y
            echo "
restarting input
            "
        fi
    done

    if [ "$UPLOAD_SPEED" -le 3000 ] || [ "$DOWNLOAD_SPEED" -le 3000 ]; then
        echo "
================================================================================

Please visit https://forum.openwrt.org/t/cake-w-adaptive-bandwidth/108848
and ask about further measures that may help in improving experience on a
relatively low bandwidth link.

This suggestion is provided because either your upload or download has a
maximum speed of 3 Mbits per second or lower.

At speeds below 3Mbps, low latency applications may not work well, even with
good queue management. The cause of this is that individual packets take longer
and longer to send, causing disruptions even with perfect queueing.

Note that the above forum requires registration before posting."
    fi

    # =========================================================================
    # WRITE CONFIG
    # =========================================================================
    uci set "${SERVICE_NAME}.@network[0].upload_interface=${UPLOAD_DEVICE}"
    uci set "${SERVICE_NAME}.@network[0].download_interface=${DOWNLOAD_DEVICE}"
    uci set "${SERVICE_NAME}.@network[0].upload_base_kbits=${UPLOAD_SPEED}"
    uci set "${SERVICE_NAME}.@network[0].download_base_kbits=${DOWNLOAD_SPEED}"
    uci set "${SERVICE_NAME}.@network[0].upload_min_percent=${UPLOAD_PERCENT}"
    uci set "${SERVICE_NAME}.@network[0].download_min_percent=${DOWNLOAD_PERCENT}"

    uci set "${SERVICE_NAME}.@output[0].log_level=${LOG_LEVEL}"
    uci set "${SERVICE_NAME}.@output[0].use_syslog=${USE_SYSLOG}"
    uci set "${SERVICE_NAME}.@output[0].suppress_statistics=${SUPPRESS_STATISTICS}"

    uci set "${SERVICE_NAME}.@advanced_settings[0].measurement_type=${MEASUREMENT_TYPE}"
    uci set "${SERVICE_NAME}.@advanced_settings[0].num_reflectors=${NUM_REFLECTORS}"
    uci set "${SERVICE_NAME}.@advanced_settings[0].dry_run=${DRY_RUN}"

    uci set "${SERVICE_NAME}.@observability[0].enabled=${OBS_ENABLED}"
    uci set "${SERVICE_NAME}.@observability[0].protocol=${OBS_PROTOCOL}"
    uci set "${SERVICE_NAME}.@observability[0].port=${OBS_PORT}"
    uci set "${SERVICE_NAME}.@observability[0].export_rate_metrics=${OBS_EXPORT_RATES}"
    uci set "${SERVICE_NAME}.@observability[0].export_ping_metrics=${OBS_EXPORT_PINGS}"
    uci set "${SERVICE_NAME}.@observability[0].export_baseline_metrics=${OBS_EXPORT_BASELINE}"
    uci set "${SERVICE_NAME}.@observability[0].export_events=${OBS_EXPORT_EVENTS}"

    if [ -n "${OBS_HOST}" ]; then
        uci set "${SERVICE_NAME}.@observability[0].host=${OBS_HOST}"
    fi

    uci commit "${SERVICE_NAME}"

    if [ -x "/etc/init.d/${SERVICE_NAME}" ]; then
        if [ "${START_AUTO}" = "Yes" ]; then
            echo "
Enabling 'sqm-autorate-rust' service"
            "/etc/init.d/${SERVICE_NAME}" enable
        fi
        if [ "${START_NOW}" = "Yes" ]; then
            echo "
Starting 'sqm-autorate-rust' service"
            if "/etc/init.d/${SERVICE_NAME}" running; then
                "/etc/init.d/${SERVICE_NAME}" stop
                sleep 3
            fi
            "/etc/init.d/${SERVICE_NAME}" start
        fi
    fi

fi

print_rerun
trap "-" 2
