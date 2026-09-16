#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UNIQ Smart Home - Native Zigbee Connector
Translates Zigbee 3.0 mesh devices into UNIQ Cloud sub-devices and handles RPC control.
"""

import json
import logging
import time
from typing import Dict, Any
try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None
from connectors.base_connector import BaseConnector

log = logging.getLogger("UniqZigbeeConnector")

class ZigbeeConnector(BaseConnector):
    def __init__(self, name: str, config: Dict[str, Any], gateway_callback):
        super().__init__(name, config, gateway_callback)
        self.broker_host = self.config.get("broker_host", "127.0.0.1")
        self.broker_port = int(self.config.get("broker_port", 1883))
        self.base_topic = self.config.get("base_topic", "zigbee2mqtt")
        self.known_devices = set()
        self.mqtt_client = mqtt.Client(client_id="uniq_zigbee_connector") if mqtt else None

    def start(self):
        if not self.mqtt_client:
            log.warning("MQTT library not installed, Zigbee connector running in stub mode.")
            self.is_running = True
            return
        log.info(f"Starting UNIQ Zigbee Connector (Connecting to {self.broker_host}:{self.broker_port})...")
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message
        try:
            self.mqtt_client.connect(self.broker_host, self.broker_port, 60)
            self.mqtt_client.loop_start()
            self.is_running = True
            log.info("UNIQ Zigbee Connector successfully started and listening.")
        except Exception as e:
            log.error(f"Failed to start Zigbee Connector: {e}")

    def stop(self):
        log.info("Stopping UNIQ Zigbee Connector...")
        self.is_running = False
        if self.mqtt_client:
            try:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            except Exception as e:
                log.error(f"Error stopping Zigbee connector: {e}")

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            log.info("Zigbee connector connected to local Zigbee message bus.")
            client.subscribe(f"{self.base_topic}/#")
        else:
            log.error(f"Zigbee connector connection failed with code {rc}")

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        payload_str = msg.payload.decode("utf-8")

        # Skip bridge telemetry and internal topics
        if topic.startswith(f"{self.base_topic}/bridge"):
            self._handle_bridge_event(topic, payload_str)
            return

        device_name = topic.replace(f"{self.base_topic}/", "").strip()
        if not device_name or "/" in device_name:
            return

        try:
            payload = json.loads(payload_str)
            if not isinstance(payload, dict):
                return
        except Exception:
            return

        # Auto-register device on first seen
        if device_name not in self.known_devices:
            self.known_devices.add(device_name)
            self.send_to_gateway("connect", {
                "device": f"Zigbee - {device_name}",
                "type": self._infer_device_type(payload)
            })

        # Separate telemetry (sensors, states) from static attributes (battery, linkquality)
        telemetry = {}
        attributes = {"protocol": "Zigbee 3.0", "source": "UNIQ Hub"}

        for k, v in payload.items():
            if k in ["linkquality", "battery", "voltage", "model", "manufacturer"]:
                attributes[k] = v
            else:
                telemetry[k] = v

        if telemetry:
            self.send_to_gateway("telemetry", {
                "device": f"Zigbee - {device_name}",
                "data": telemetry
            })

        if attributes:
            self.send_to_gateway("attributes", {
                "device": f"Zigbee - {device_name}",
                "data": attributes
            })

    def _handle_bridge_event(self, topic: str, payload_str: str):
        if "event" in topic:
            try:
                event_data = json.loads(payload_str)
                if event_data.get("type") == "device_joined":
                    log.info(f"New Zigbee device joined network: {event_data.get('data')}")
            except Exception:
                pass

    def _infer_device_type(self, payload: Dict) -> str:
        keys = set(payload.keys())
        if "color" in keys or "brightness" in keys or "color_temp" in keys:
            return "Smart Light"
        if "temperature" in keys or "humidity" in keys:
            return "Climate Sensor"
        if "occupancy" in keys or "presence" in keys:
            return "Motion Sensor"
        if "contact" in keys:
            return "Door/Window Sensor"
        if "power" in keys or "current" in keys or "energy" in keys:
            return "Smart Plug"
        if "state" in keys:
            return "Switch"
        return "Zigbee Device"

    def handle_rpc(self, device_name: str, method: str, params: Any) -> Any:
        """Translates Cloud RPC to Zigbee set commands."""
        # Strip "Zigbee - " prefix to get friendly name
        clean_name = device_name.replace("Zigbee - ", "").strip()
        command_topic = f"{self.base_topic}/{clean_name}/set"

        payload = {}
        if method in ["setValue", "setState", "setPower"]:
            state = "ON" if (params is True or params == 1 or str(params).upper() == "ON") else "OFF"
            payload = {"state": state}
        elif method == "setBrightness":
            payload = {"brightness": int(params)}
        elif method == "setColor":
            payload = {"color": params}
        elif method == "toggle":
            payload = {"state": "TOGGLE"}
        elif method == "setLock":
            payload = {"state": "LOCK" if params else "UNLOCK"}
        elif isinstance(params, dict):
            payload = params
        else:
            payload = {method: params}

        log.info(f"Sending Zigbee command to {command_topic}: {payload}")
        self.mqtt_client.publish(command_topic, json.dumps(payload))
        return {"status": "SUCCESS", "command": payload}
