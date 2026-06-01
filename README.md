# Wigglegram First Phase

This first phase runs with:

- 1 Raspberry Pi
- 1 ESP32-CAM, tested with AI Thinker style boards

The Raspberry Pi sends commands to the ESP32-CAM over Wi-Fi, captures one JPEG, stores it locally, and creates a GIF output. Later phases can add three more cameras and a synchronized UDP trigger.

## Phase 1 behavior

1. ESP32-CAM connects to Wi-Fi and starts an HTTP camera API.
2. Raspberry Pi calls `/status` to confirm the camera is online.
3. Raspberry Pi sends `/config` camera settings.
4. Raspberry Pi calls `/capture`.
5. Raspberry Pi saves:
   - `captures/latest.jpg`
   - `captures/wiggle.gif`

With one camera, the GIF is only a one-frame proof of the pipeline. The same Pi code is structured so four cameras can be added next.

## Files

- `pi/` - Raspberry Pi controller program.
- `esp32_cam/esp32_cam_phase1/` - Arduino firmware for ESP32-CAM.

## Network

For the first phase, both devices can be on any same Wi-Fi network.

Recommended camera IP for first test:

```text
http://192.168.50.11
```

You can either set a DHCP reservation on your router / Pi access point, or edit the ESP32 firmware to use a static IP.

## Next phases

- Add Raspberry Pi access point setup.
- Add four camera IPs.
- Add UDP broadcast capture trigger.
- Add GIF frame order `1, 2, 3, 4, 3, 2`.
- Add idle/sleep commands and physical trigger button.
