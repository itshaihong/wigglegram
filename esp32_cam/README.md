# ESP32-CAM Firmware

This first firmware connects to the Raspberry Pi access point and exposes a small HTTP API:

```text
GET  /status
POST /config
GET  /capture
POST /sleep
```

## Arduino IDE setup

1. Install the ESP32 board package in Arduino IDE.
2. Install the `ArduinoJson` library.
3. Open `esp32_cam_phase1/esp32_cam_phase1.ino`.
4. The default Wi-Fi settings match the Pi AP setup:

```cpp
const char *WIFI_SSID = "WIGGLEGRAM_AP";
const char *WIFI_PASSWORD = "Wigglegram2026";
```

Set this before flashing each camera:

```cpp
#define CAMERA_INDEX 1
```

Use:

```text
Camera 1: CAMERA_INDEX 1 -> 192.168.50.11
Camera 2: CAMERA_INDEX 2 -> 192.168.50.12
Camera 3: CAMERA_INDEX 3 -> 192.168.50.13
Camera 4: CAMERA_INDEX 4 -> 192.168.50.14
```

The web app broadcasts settings to all cameras configured in `pi/config.json`.

5. Select board: `AI Thinker ESP32-CAM`.
6. Upload with GPIO0 connected to GND.
7. Remove GPIO0 from GND and reset the board.
8. Open Serial Monitor at `115200` baud and note the IP address.

## API examples

Check status:

```bash
curl http://CAMERA_IP/status
```

Configure:

```bash
curl -X POST http://CAMERA_IP/config \
  -H "Content-Type: application/json" \
  -d '{"framesize":"SVGA","quality":12,"aec":true,"agc":true}'
```

Capture:

```bash
curl http://CAMERA_IP/capture --output latest.jpg
```

Sleep test:

```bash
curl -X POST http://CAMERA_IP/sleep
```

`/sleep` currently uses a short light sleep test. Deep sleep will be added later because it needs a wake source; a deeply sleeping ESP32-CAM cannot listen for Wi-Fi commands.
