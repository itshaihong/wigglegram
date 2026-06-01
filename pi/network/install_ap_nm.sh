#!/usr/bin/env bash
set -euo pipefail

AP_INTERFACE="${AP_INTERFACE:-wlan0}"
AP_CONNECTION="${AP_CONNECTION:-wigglegram-ap}"
AP_SSID="${AP_SSID:-WIGGLEGRAM_AP}"
AP_PASSWORD="${AP_PASSWORD:-Wigglegram2026}"
AP_COUNTRY="${AP_COUNTRY:-US}"
AP_ADDRESS="${AP_ADDRESS:-192.168.50.1/24}"
AP_CHANNEL="${AP_CHANNEL:-6}"
CONNECT_TIMEOUT_SECONDS="${CONNECT_TIMEOUT_SECONDS:-30}"

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

echo "Preparing ${AP_INTERFACE}"
rfkill unblock wifi || true
nmcli radio wifi on
nmcli device disconnect "${AP_INTERFACE}" >/dev/null 2>&1 || true

nmcli connection add \
  type wifi \
  ifname "${AP_INTERFACE}" \
  con-name "${AP_CONNECTION}" \
  autoconnect yes \
  ssid "${AP_SSID}"

nmcli connection modify "${AP_CONNECTION}" \
  802-11-wireless.mode ap \
  802-11-wireless.band bg \
  802-11-wireless.channel "${AP_CHANNEL}" \
  ipv4.method shared \
  ipv4.addresses "${AP_ADDRESS}" \
  ipv6.method ignore \
  wifi-sec.key-mgmt wpa-psk \
  wifi-sec.proto rsn \
  wifi-sec.pairwise ccmp \
  wifi-sec.group ccmp \
  wifi-sec.psk "${AP_PASSWORD}" \
  connection.autoconnect yes

nmcli connection modify "${AP_CONNECTION}" 802-11-wireless-security.pmf 1 >/dev/null 2>&1 || true

echo "Starting AP connection, timeout ${CONNECT_TIMEOUT_SECONDS}s"
if ! timeout "${CONNECT_TIMEOUT_SECONDS}" nmcli connection up "${AP_CONNECTION}"; then
  echo
  echo "Failed or timed out while starting the AP."
  echo "Useful diagnostics:"
  nmcli device status || true
  nmcli connection show || true
  echo
  echo "Try rebooting, then run:"
  echo "  sudo nmcli connection up ${AP_CONNECTION}"
  echo
  echo "If wlan0 is unmanaged, run:"
  echo "  sudo nmcli device set ${AP_INTERFACE} managed yes"
  exit 1
fi

nmcli device status

echo "Done. Pi AP is ${AP_SSID} at ${AP_ADDRESS}. ESP32-CAM should use 192.168.50.11."
