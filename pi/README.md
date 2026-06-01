# Raspberry Pi Controller

## Install

On the Raspberry Pi:

```bash
cd pi
chmod +x setup_pi.sh run_once.sh run_gallery.sh
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

## Web preview and download

Start the web gallery on the Pi:

```bash
cd ~/wigglegram/pi
chmod +x run_gallery.sh
./run_gallery.sh
```

From a phone or PC connected to `WIGGLEGRAM_AP`, open:

```text
http://192.168.50.1:8080
```

The page can preview `latest.jpg` and `wiggle.gif`, download files, refresh the gallery, and trigger a new capture.

It also includes camera controls based on the ESP32-CAM CameraWebServer demo:

```text
resolution, JPEG quality, brightness, contrast, saturation, sharpness,
white balance, exposure, gain, mirror/flip, lens correction, and colorbar
```

Press `Apply to All` to send the same settings to every camera listed in `config.json`.

## Notes

This phase uses normal HTTP requests for settings and image transfer. The synchronized multi-camera phase should add UDP broadcast for capture triggering.
