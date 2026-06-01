# ESP32-CAM Firmware

This first firmware exposes a small HTTP API:

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
4. Set:

```cpp
const char *WIFI_SSID = "YOUR_WIFI_SSID";
const char *WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
```

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
