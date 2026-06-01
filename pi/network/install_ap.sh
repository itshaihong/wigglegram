#!/usr/bin/env bash
set -euo pipefail

AP_INTERFACE="${AP_INTERFACE:-wlan0}"
UPSTREAM_INTERFACE="${UPSTREAM_INTERFACE:-}"
AP_SSID="${AP_SSID:-WIGGLEGRAM_AP}"
AP_PASSWORD="${AP_PASSWORD:-Wigglegram2026}"
AP_COUNTRY="${AP_COUNTRY:-US}"
AP_CHANNEL="${AP_CHANNEL:-6}"
AP_ADDRESS="${AP_ADDRESS:-192.168.50.1}"
DHCP_START="${DHCP_START:-192.168.50.20}"
DHCP_END="${DHCP_END:-192.168.50.80}"

if [ "$EUID" -ne 0 ]; then
  echo "Run with sudo: sudo ./install_ap.sh"
  exit 1
fi

if [ "${#AP_PASSWORD}" -lt 8 ]; then
  echo "AP_PASSWORD must be at least 8 characters for WPA2."
  exit 1
fi

echo "Installing access point packages"
apt-get update
apt-get install -y hostapd dnsmasq iptables-persistent

echo "Stopping services while writing configuration"
systemctl stop hostapd || true
systemctl stop dnsmasq || true

echo "Configuring static AP address on ${AP_INTERFACE}"
cat >/etc/dhcpcd.conf.d/wigglegram-ap.conf <<EOF_CONF
interface ${AP_INTERFACE}
static ip_address=${AP_ADDRESS}/24
nohook wpa_supplicant
EOF_CONF

echo "Writing hostapd config"
cat >/etc/hostapd/hostapd.conf <<EOF_CONF
country_code=${AP_COUNTRY}
interface=${AP_INTERFACE}
ssid=${AP_SSID}
hw_mode=g
channel=${AP_CHANNEL}
auth_algs=1
wpa=2
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
wpa_passphrase=${AP_PASSWORD}
EOF_CONF

cat >/etc/default/hostapd <<EOF_CONF
DAEMON_CONF="/etc/hostapd/hostapd.conf"
EOF_CONF

echo "Writing dnsmasq config"
cat >/etc/dnsmasq.d/wigglegram-ap.conf <<EOF_CONF
interface=${AP_INTERFACE}
bind-interfaces
dhcp-range=${DHCP_START},${DHCP_END},255.255.255.0,24h
dhcp-option=3,${AP_ADDRESS}
dhcp-option=6,${AP_ADDRESS}
EOF_CONF

if [ -n "$UPSTREAM_INTERFACE" ]; then
  echo "Enabling routing from ${AP_INTERFACE} to ${UPSTREAM_INTERFACE}"
  sed -i 's/^#*net.ipv4.ip_forward=.*/net.ipv4.ip_forward=1/' /etc/sysctl.conf
  if ! grep -q '^net.ipv4.ip_forward=1' /etc/sysctl.conf; then
    echo 'net.ipv4.ip_forward=1' >>/etc/sysctl.conf
  fi
  sysctl -w net.ipv4.ip_forward=1

  iptables -t nat -C POSTROUTING -o "${UPSTREAM_INTERFACE}" -j MASQUERADE 2>/dev/null || \
    iptables -t nat -A POSTROUTING -o "${UPSTREAM_INTERFACE}" -j MASQUERADE
  netfilter-persistent save
else
  echo "No UPSTREAM_INTERFACE set; creating camera-only AP without internet routing."
fi

echo "Enabling services"
systemctl unmask hostapd
systemctl enable hostapd
systemctl enable dnsmasq
systemctl restart dhcpcd || true
systemctl restart hostapd
systemctl restart dnsmasq

echo "Done. ESP32-CAM should join SSID '${AP_SSID}'. Pi AP address: ${AP_ADDRESS}"
