#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
==============================================================================
UNIQ Smart Home Gateway Daemon
Main entrypoint for UNIQ Hub devices. Handles Cloud MQTT Gateway API,
Connector lifecycle management, Protocol Licensing, and bidirectional RPC.
==============================================================================
"""

import sys
import os
import json
import time
import logging
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from typing import Dict, Any
try:
    import paho.mqtt.client as mqtt
    HAS_MQTT = True
except ImportError:
    HAS_MQTT = False
    mqtt = None

from license_manager import LicenseManager, HubTier
from connectors.zigbee_connector import ZigbeeConnector
from connectors.matter_connector import MatterConnector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger("UniqGateway")

CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
GATEWAY_CONFIG_PATH = os.path.join(CONFIG_DIR, "gateway.json" if not HAS_YAML and os.path.exists(os.path.join(CONFIG_DIR, "gateway.json")) else "gateway.yaml")

class UniqGateway:
    def __init__(self, config_path: str = None):
        if config_path is None:
            if not HAS_YAML and os.path.exists(os.path.join(CONFIG_DIR, "gateway.json")):
                config_path = os.path.join(CONFIG_DIR, "gateway.json")
            else:
                config_path = os.path.join(CONFIG_DIR, "gateway.yaml")
        self.config_path = config_path
        self.config = self._load_config()
        
        hub_cfg = self.config.get("hub", {})
        self.hub_serial = hub_cfg.get("serial", "UNIQ-HUB-PRO-001")
        self.hub_tier = hub_cfg.get("tier", HubTier.PRO)

        cloud_cfg = self.config.get("cloud", {})
        self.cloud_host = cloud_cfg.get("host", "127.0.0.1")
        self.cloud_port = int(cloud_cfg.get("port", 1883))
        self.access_token = cloud_cfg.get("access_token", "YOUR_GATEWAY_TOKEN")

        # 1. Initialize Protocol License Manager
        self.license_manager = LicenseManager(self.hub_serial, self.hub_tier)
        self.license_manager.on_license_changed(self._on_license_changed)

        # 2. Connectors pool
        self.connectors: Dict[str, Any] = {}
        self.mqtt_client = mqtt.Client(client_id=f"uniq_gw_{self.hub_serial}") if HAS_MQTT else None
        self.is_running = False

    def _load_config(self) -> Dict:
        # If the requested path doesn't exist, try alternating .yaml / .json
        if not os.path.exists(self.config_path):
            alt_path = self.config_path.replace(".yaml", ".json") if self.config_path.endswith(".yaml") else self.config_path.replace(".json", ".yaml")
            if os.path.exists(alt_path):
                self.config_path = alt_path

        if not os.path.exists(self.config_path):
            log.warning(f"Config file not found at {self.config_path}, using defaults.")
            return {}

        with open(self.config_path, "r", encoding="utf-8") as f:
            if self.config_path.endswith((".yaml", ".yml")):
                if HAS_YAML:
                    return yaml.safe_load(f)
                else:
                    log.warning("PyYAML not installed, attempting JSON fallback.")
                    json_path = self.config_path.replace(".yaml", ".json").replace(".yml", ".json")
                    if os.path.exists(json_path):
                        with open(json_path, "r", encoding="utf-8") as jf:
                            return json.load(jf)
                    return {}
            return json.load(f)


    def start(self):
        log.info("=======================================================")
        log.info(f" Starting UNIQ Smart Home Gateway - Serial: {self.hub_serial}")
        log.info(f" Hardware Tier: {self.license_manager.tier}")
        log.info(f" Licensed Protocols: {self.license_manager.get_licensed_protocols()}")
        log.info("=======================================================")

        self.is_running = True

        # Setup Cloud MQTT client
        self.mqtt_client.username_pw_set(self.access_token)
        self.mqtt_client.on_connect = self._on_cloud_connect
        self.mqtt_client.on_message = self._on_cloud_message

        try:
            log.info(f"Connecting to UNIQ Cloud at {self.cloud_host}:{self.cloud_port}...")
            self.mqtt_client.connect(self.cloud_host, self.cloud_port, 60)
            self.mqtt_client.loop_start()
        except Exception as e:
            log.error(f"Failed to connect to UNIQ Cloud: {e}")

        # Start authorized protocol connectors
        self._init_connectors()

        # Keep running
        try:
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        log.info("Shutting down UNIQ Gateway...")
        self.is_running = False
        for name, connector in list(self.connectors.items()):
            try:
                connector.stop()
            except Exception as e:
                log.error(f"Error stopping connector {name}: {e}")
        self.connectors.clear()
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        log.info("UNIQ Gateway stopped cleanly.")

    def _init_connectors(self):
        """Initializes and starts connectors if licensed."""
        connectors_cfg = self.config.get("connectors", {})

        # A. Zigbee Connector
        if self.license_manager.is_protocol_licensed("zigbee"):
            zigbee_cfg = connectors_cfg.get("zigbee", {})
            zb_connector = ZigbeeConnector("zigbee", zigbee_cfg, self.on_connector_data)
            zb_connector.start()
            self.connectors["zigbee"] = zb_connector
        else:
            log.info("Zigbee connector disabled by license.")

        # B. Matter Connector
        if self.license_manager.is_protocol_licensed("matter"):
            matter_cfg = connectors_cfg.get("matter", {})
            mat_connector = MatterConnector("matter", matter_cfg, self.on_connector_data)
            mat_connector.start()
            self.connectors["matter"] = mat_connector
        else:
            log.info("Matter connector disabled by license.")

    def _on_license_changed(self, active_protocols):
        """Dynamic license hot-reload: start newly unlocked connectors or stop revoked ones."""
        log.info(f"License change detected. Active: {active_protocols}")

        # Check Zigbee
        if "zigbee" in active_protocols and "zigbee" not in self.connectors:
            log.info("Activating newly licensed Zigbee connector...")
            zigbee_cfg = self.config.get("connectors", {}).get("zigbee", {})
            zb_connector = ZigbeeConnector("zigbee", zigbee_cfg, self.on_connector_data)
            zb_connector.start()
            self.connectors["zigbee"] = zb_connector
        elif "zigbee" not in active_protocols and "zigbee" in self.connectors:
            log.info("Deactivating revoked Zigbee connector...")
            self.connectors["zigbee"].stop()
            del self.connectors["zigbee"]

        # Check Matter
        if "matter" in active_protocols and "matter" not in self.connectors:
            log.info("Activating newly licensed Matter connector...")
            matter_cfg = self.config.get("connectors", {}).get("matter", {})
            mat_connector = MatterConnector("matter", matter_cfg, self.on_connector_data)
            mat_connector.start()
            self.connectors["matter"] = mat_connector
        elif "matter" not in active_protocols and "matter" in self.connectors:
            log.info("Deactivating revoked Matter connector...")
            self.connectors["matter"].stop()
            del self.connectors["matter"]

    def _on_cloud_connect(self, client, userdata, flags, rc):
        if rc == 0:
            log.info("Connected to UNIQ Cloud successfully!")
            # Subscribe to RPC and attributes
            client.subscribe("v1/gateway/rpc")
            client.subscribe("v1/devices/me/attributes")
            client.subscribe("v1/devices/me/attributes/response/+")

            # Publish Hub identification attributes to Cloud
            hub_attributes = {
                "serialNumber": self.hub_serial,
                "tier": self.license_manager.tier,
                "licensedProtocols": self.license_manager.get_licensed_protocols(),
                "firmwareVersion": "2.4.0-uniq",
                "brand": "UNIQ Smart Home",
                "online": True
            }
            client.publish("v1/devices/me/attributes", json.dumps(hub_attributes))
            log.info(f"Published Hub telemetry and license attributes: {hub_attributes}")

            # Re-announce all known sub-devices to Cloud!
            for c_name, connector in list(self.connectors.items()):
                if hasattr(connector, "mapper") and connector.mapper:
                    for key, dev in connector.mapper._registry.items():
                        d_name = dev.get("device_name")
                        d_type = dev.get("device_type", "Matter Device")
                        if d_name:
                            client.publish("v1/gateway/connect", json.dumps({"device": d_name, "type": d_type}))
                            log.info(f"Announced sub-device to Cloud on connect: [{d_name}] ({d_type})")

        else:
            log.error(f"Cloud connection failed with code: {rc}")

    def _on_cloud_message(self, client, userdata, msg):
        topic = msg.topic
        payload_str = msg.payload.decode("utf-8")

        # 1. Attribute updates (License management / Remote config)
        if topic == "v1/devices/me/attributes":
            try:
                attrs = json.loads(payload_str)
                log.info(f"Received Cloud attribute update: {attrs}")
                self.license_manager.update_license_from_cloud(attrs)
            except Exception as e:
                log.error(f"Error processing attribute update: {e}")

        # 2. Remote Procedure Calls (Controlling smart home devices)
        elif topic == "v1/gateway/rpc":
            try:
                rpc_req = json.loads(payload_str)
                self._handle_cloud_rpc(rpc_req)
            except Exception as e:
                log.error(f"Error handling Cloud RPC: {e}")

    def _handle_cloud_rpc(self, rpc_req: Dict):
        """
        Processes incoming RPC from Thingsboard Cloud.
        Format: {
          "device": "Zigbee - Living Room Light",
          "data": { "id": 123, "method": "setState", "params": true }
        }
        """
        device_name = rpc_req.get("device", "")
        data = rpc_req.get("data", {})
        request_id = data.get("id")
        method = data.get("method")
        params = data.get("params")

        log.info(f"Cloud RPC -> Device: [{device_name}], Method: [{method}], Params: [{params}]")

        target_connector = None
        if device_name.startswith("Zigbee") and "zigbee" in self.connectors:
            target_connector = self.connectors["zigbee"]
        elif device_name.startswith("Matter") and "matter" in self.connectors:
            target_connector = self.connectors["matter"]

        if target_connector:
            try:
                result = target_connector.handle_rpc(device_name, method, params)
                # Reply back to Thingsboard RPC
                response_payload = {
                    "device": device_name,
                    "id": request_id,
                    "data": {"success": True, "result": result}
                }
                self.mqtt_client.publish("v1/gateway/rpc", json.dumps(response_payload))
            except Exception as e:
                log.error(f"RPC execution error on connector: {e}")
        else:
            log.warning(f"No active licensed connector found for device: {device_name}")

    def on_connector_data(self, connector_name: str, message_type: str, data: Dict[str, Any]):
        """
        Callback invoked by connectors to forward sub-device data to UNIQ Cloud.
        """
        if not self.is_running:
            return

        device = data.get("device")
        if not device:
            return

        if message_type == "connect":
            # Inform Cloud of newly connected device
            payload = {"device": device}
            self.mqtt_client.publish("v1/gateway/connect", json.dumps(payload))
            log.info(f"Published sub-device connected: {device}")

        elif message_type == "disconnect":
            payload = {"device": device}
            self.mqtt_client.publish("v1/gateway/disconnect", json.dumps(payload))
            log.info(f"Published sub-device disconnected: {device}")

        elif message_type == "telemetry":
            # Telemetry format: { "DeviceName": [ { "values": { ... } } ] }
            telemetry_data = data.get("data", {})
            payload = {
                device: [
                    {
                        "ts": int(round(time.time() * 1000)),
                        "values": telemetry_data
                    }
                ]
            }
            self.mqtt_client.publish("v1/gateway/telemetry", json.dumps(payload))

        elif message_type == "attributes":
            # Attributes format: { "DeviceName": { "attr1": "val1" } }
            attributes_data = data.get("data", {})
            payload = {
                device: attributes_data
            }
            self.mqtt_client.publish("v1/gateway/attributes", json.dumps(payload))

if __name__ == "__main__":
    gateway = UniqGateway()
    gateway.start()
