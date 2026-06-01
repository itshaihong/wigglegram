# Wigglegram First Phase

This first phase runs with:

- 1 Raspberry Pi
- 1 ESP32-CAM, tested with AI Thinker style boards

The Raspberry Pi creates a local camera Wi-Fi network, sends commands to the ESP32-CAM, captures one JPEG, stores it locally, and creates a GIF output. Later phases can add three more cameras and a synchronized UDP trigger.

## Phase 1 behavior

1. Raspberry Pi starts a Wi-Fi access point named `WIGGLEGRAM_AP`.
2. ESP32-CAM connects to the Pi access point and starts an HTTP camera API.
3. Raspberry Pi calls `/status` to confirm the camera is online.
4. Raspberry Pi sends `/config` camera settings.
5. Raspberry Pi calls `/capture`.
6. Raspberry Pi saves:
   - `captures/latest.jpg`
   - `captures/wiggle.gif`

With one camera, the GIF is only a one-frame proof of the pipeline. The same Pi code is structured so four cameras can be added next.

## Files

- `pi/` - Raspberry Pi controller program.
- `esp32_cam/esp32_cam_phase1/` - Arduino firmware for ESP32-CAM.

## Network

For the first phase, the Pi hosts the camera network:

```text
SSID: WIGGLEGRAM_AP
Password: Wigglegram2026
Pi IP: 192.168.50.1
ESP32-CAM IP: 192.168.50.11
```

Recommended camera IP for first test:

```text
http://192.168.50.11
```

See `pi/network/README.md` for the Raspberry Pi access point setup.

## Web preview

After Pi setup, start the preview/download web app:

```bash
cd pi
./run_gallery.sh
```

Then open this from your phone or PC while connected to `WIGGLEGRAM_AP`:

```text
http://192.168.50.1:8080
```

## Next phases

- Add four camera IPs.
- Add UDP broadcast capture trigger.
- Add GIF frame order `1, 2, 3, 4, 3, 2`.
- Add idle/sleep commands and physical trigger button.
