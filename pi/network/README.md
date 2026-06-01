# Raspberry Pi Camera Access Point

This config makes the Raspberry Pi create its own Wi-Fi network for the ESP32-CAM:

```text
SSID: WIGGLEGRAM_AP
Password: Wigglegram2026
Pi IP: 192.168.50.1
ESP32-CAM phase 1 IP: 192.168.50.11
```

The ESP32-CAM no longer needs to join your home Wi-Fi. It joins the Pi's access point.

## Install AP mode on current Raspberry Pi OS

Raspberry Pi OS Bookworm and newer use NetworkManager by default, so start here:

```bash
cd pi/network
chmod +x install_ap_nm.sh
sudo ./install_ap_nm.sh
```

Reboot after installation:

```bash
sudo reboot
```

## Install AP mode on older Raspberry Pi OS

On the Raspberry Pi:

```bash
cd pi/network
chmod +x install_ap.sh
sudo ./install_ap.sh
```

Reboot after installation:

```bash
sudo reboot
```

After reboot, the Pi should broadcast:

```text
WIGGLEGRAM_AP
```

## Optional internet routing on older Raspberry Pi OS

If the Pi has Ethernet internet on `eth0` and you want devices on the camera network to also reach the internet:

```bash
sudo UPSTREAM_INTERFACE=eth0 ./install_ap.sh
```

For the camera project itself, internet routing is not required.

## Test from the Pi

After flashing the ESP32-CAM firmware and powering it near the Pi:

```bash
curl http://192.168.50.11/status
```

Then run the capture program:

```bash
cd ../
./run_once.sh
```

## Notes

`install_ap_nm.sh` is intended for current Raspberry Pi OS with NetworkManager. `install_ap.sh` is intended for older Raspberry Pi OS images using `dhcpcd`, `hostapd`, and `dnsmasq`.
