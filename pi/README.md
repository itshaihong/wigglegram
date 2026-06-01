# Raspberry Pi Controller

## Install

On the Raspberry Pi:

```bash
cd pi
chmod +x setup_pi.sh run_once.sh
./setup_pi.sh
```

Edit `config.json` so `base_url` matches the ESP32-CAM IP address.

## Run

```bash
./run_once.sh
```

Expected output files:

```text
captures/latest.jpg
captures/wiggle.gif
```

## Notes

The first phase uses normal HTTP requests. This is simple and reliable for one camera. The synchronized multi-camera phase should keep HTTP for setup and image transfer, then add UDP broadcast for capture triggering.
