# Raspberry Pi Controller

## Install

On the Raspberry Pi:

```bash
cd pi
chmod +x setup_pi.sh run_once.sh
./setup_pi.sh
```

The default `config.json` points to `http://192.168.50.11`, which matches the phase 1 ESP32-CAM firmware.

## Configure the Pi camera network

Before running the capture program, configure the Raspberry Pi as the camera access point:

```bash
cd network
chmod +x install_ap_nm.sh
sudo ./install_ap_nm.sh
sudo reboot
```

After reboot, flash/power the ESP32-CAM. It should connect to the Pi network:

```text
SSID: WIGGLEGRAM_AP
Password: Wigglegram2026
ESP32-CAM IP: 192.168.50.11
```

## Run

```bash
cd ~/wigglegram/pi
./run_once.sh
```

Expected output files:

```text
captures/latest.jpg
captures/wiggle.gif
```

## Notes

The first phase uses normal HTTP requests. This is simple and reliable for one camera. The synchronized multi-camera phase should keep HTTP for setup and image transfer, then add UDP broadcast for capture triggering.
