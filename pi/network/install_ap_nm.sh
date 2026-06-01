#!/usr/bin/env bash
set -euo pipefail

AP_INTERFACE="${AP_INTERFACE:-wlan0}"
AP_CONNECTION="${AP_CONNECTION:-wigglegram-ap}"
AP_SSID="${AP_SSID:-WIGGLEGRAM_AP}"
AP_PASSWORD="${AP_PASSWORD:-Wigglegram2026}"
AP_COUNTRY="${AP_COUNTRY:-US}"
AP_ADDRESS="${AP_ADDRESS:-192.168.50.1/24}"

if [ "$EUID" -ne 0 ]; then
  echo "Run with sudo: sudo ./install_ap_nm.sh"
  exit 1
fi

if ! command -v nmcli >/dev/null 2>&1; then
  echo "nmcli not found. Use install_ap.sh for older dhcpcd/hostapd images."
  exit 1
fi

if [ "${#AP_PASSWORD}" -lt 8 ]; then
  echo "AP_PASSWORD must be at least 8 characters for WPA2."
  exit 1
fi

if command -v raspi-config >/dev/null 2>&1; then
  raspi-config nonint do_wifi_country "${AP_COUNTRY}" || true
fi

echo "Creating NetworkManager access point '${AP_SSID}' on ${AP_INTERFACE}"
nmcli connection delete "${AP_CONNECTION}" >/dev/null 2>&1 || true

nmcli connection add \
  type wifi \
  ifname "${AP_INTERFACE}" \
  con-name "${AP_CONNECTION}" \
  autoconnect yes \
  ssid "${AP_SSID}"

nmcli connection modify "${AP_CONNECTION}" \
  802-11-wireless.mode ap \
  802-11-wireless.band bg \
  ipv4.method shared \
  ipv4.addresses "${AP_ADDRESS}" \
  ipv6.method ignore \
  wifi-sec.key-mgmt wpa-psk \
  wifi-sec.psk "${AP_PASSWORD}"

nmcli connection up "${AP_CONNECTION}"

echo "Done. Pi AP is ${AP_SSID} at ${AP_ADDRESS}. ESP32-CAM should use 192.168.50.11."
