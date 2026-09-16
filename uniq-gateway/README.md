# UNIQ Smart Home Gateway Suite

The **UNIQ Gateway** is the core edge software running inside the **UNIQ Smart Hub** hardware. It connects local mesh smart devices (Zigbee 3.0, Matter over Thread / Wi-Fi) to the **UNIQ Cloud** (ThingsBoard Gateway Protocol) and enforces commercial protocol licensing.

---

## 1. Architecture Overview

```
                     +---------------------------------------+
                     |         UNIQ Cloud Platform           |
                     |     (ThingsBoard 4.3.1.4 Custom)      |
                     +-------------------+-------------------+
                                         ^
                                         | MQTT Gateway API
                                         | (v1/gateway/*)
                                         v
                     +-------------------+-------------------+
                     |       UNIQ Smart Hub (Gateway)        |
                     |                                       |
                     |  +---------------------------------+  |
                     |  |     License Manager Engine      |  |
                     |  |  (Tier 1: Lite | Tier 2: Pro)   |  |
                     |  +----------------+----------------+  |
                     |                   |                   |
                     |     +-------------+-------------+     |
                     |     |                           |     |
                     |     v                           v     |
                     | +-------+                   +-------+ |
                     | |Zigbee |                   |Matter | |
                     | |3.0    |                   |Thread | |
                     +----+----+-------------------+---+---+ +
                          |                            |
                          v                            v
               [ Zigbee Lights / ]            [ Matter Sockets / ]
               [ Climate Sensors ]            [ Smart Door Locks ]
```

---

## 2. Protocol Licensing Engine

The UNIQ Hub features remote hardware licensing managed directly from UNIQ Cloud device attributes:

- **Tier 1 (UNIQ Hub Lite)**:
  - Supports: `WiFi`, `Matter`
- **Tier 2 (UNIQ Hub Pro)**:
  - Supports: `WiFi`, `Matter`, `Zigbee`, `BLE`
- **Tier 3 (UNIQ Hub Ultra)**:
  - Supports: `WiFi`, `Matter`, `Zigbee`, `BLE`, `Thread Border Router`

### Remote License Upgrade:
You can unlock Zigbee or Matter remotely for any customer hub by updating the device's server/shared attributes on UNIQ Cloud:
```json
{
  "licensedProtocols": ["matter", "zigbee", "ble"]
}
```
The gateway daemon listens for attribute updates and dynamically hot-loads the newly licensed connector without needing a hardware reboot.

---

## 3. Deployment on Physical Hub

### Prerequisites:
- Linux OS (Ubuntu Core, Debian, or Armbian on Raspberry Pi CM4 / Rockchip RK3566 / Orange Pi Zero).
- Python 3.9+
- Zigbee 3.0 USB/UART Coordinator (CC2652P, EFR32MG21, or Sonoff ZBDongle-P).

### Quick Install:
```bash
# 1. Clone or copy files to /opt/uniq-gateway
sudo mkdir -p /opt/uniq-gateway
sudo cp -r . /opt/uniq-gateway/

# 2. Setup Python Virtual Environment
cd /opt/uniq-gateway
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configure Hub credentials in config/gateway.yaml
nano config/gateway.yaml
# Set cloud.host and cloud.access_token

# 4. Install & Enable Systemd Service
sudo cp systemd/uniq-gateway.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable uniq-gateway
sudo systemctl start uniq-gateway
```

### Viewing Logs:
```bash
journalctl -u uniq-gateway -f
```

---

## 4. Sub-Device Data Mapping & Control

- **Zigbee Devices**: Automatically discovered via Zigbee2MQTT local broker and registered as `Zigbee - {friendly_name}` on UNIQ Cloud.
- **Matter Devices**: Commissioned via QR code or pairing code and registered as `Matter - Node {id}`.
- **RPC Remote Control**: Instant bidirectional control from UNIQ mobile & web apps (`setState`, `setBrightness`, `setColorTemp`, `setLock`).
