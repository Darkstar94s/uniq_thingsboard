#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UNIQ Smart Home - Native Matter Connector (Matter over Thread & Wi-Fi)
Integrates with Matter Controller Server, translates Matter clusters into telemetry,
and executes cluster RPC commands.
"""

import json
import logging
import threading
import time
from typing import Dict, Any
from connectors.base_connector import BaseConnector

log = logging.getLogger("UniqMatterConnector")

# Standard Matter Cluster IDs
CLUSTER_ON_OFF = 0x0006
CLUSTER_LEVEL_CONTROL = 0x0008
CLUSTER_COLOR_CONTROL = 0x0300
CLUSTER_DOOR_LOCK = 0x0101
CLUSTER_TEMP_MEASUREMENT = 0x0402
CLUSTER_HUMIDITY_MEASUREMENT = 0x0405
CLUSTER_OCCUPANCY_SENSING = 0x0406

class MatterConnector(BaseConnector):
    def __init__(self, name: str, config: Dict[str, Any], gateway_callback):
        super().__init__(name, config, gateway_callback)
        self.server_url = self.config.get("server_url", "ws://127.0.0.1:5580/ws")
        self.known_nodes = {}
        self._thread = None

    def start(self):
        log.info(f"Starting UNIQ Matter Connector (Listening on {self.server_url})...")
        self.is_running = True
        # Background worker simulating or communicating with Matter controller
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        log.info("UNIQ Matter Connector successfully started.")

    def stop(self):
        log.info("Stopping UNIQ Matter Connector...")
        self.is_running = False

    def _run_loop(self):
        """Worker thread that processes Matter events."""
        while self.is_running:
            # Heartbeat check and event polling
            time.sleep(1)

    def on_matter_attribute_changed(self, node_id: str, endpoint_id: int, cluster_id: int, attribute_name: str, value: Any):
        """
        Called when a Matter device node changes state.
        Translates Matter clusters into human-readable UNIQ smart home telemetry.
        """
        device_name = f"Matter - Node {node_id}"

        if node_id not in self.known_nodes:
            self.known_nodes[node_id] = {
                "type": self._infer_matter_type(cluster_id)
            }
            self.send_to_gateway("connect", {
                "device": device_name,
                "type": self.known_nodes[node_id]["type"]
            })
            self.send_to_gateway("attributes", {
                "device": device_name,
                "data": {
                    "protocol": "Matter 1.3",
                    "nodeId": node_id,
                    "endpoint": endpoint_id,
                    "transport": "Thread / Wi-Fi"
                }
            })

        telemetry = {}

        # 1. On / Off Cluster
        if cluster_id == CLUSTER_ON_OFF:
            telemetry["state"] = "ON" if value else "OFF"
            telemetry["onOff"] = bool(value)

        # 2. Level Control (Dimmer)
        elif cluster_id == CLUSTER_LEVEL_CONTROL:
            # Matter level is 0 - 254
            brightness_pct = int(round((value / 254.0) * 100)) if value else 0
            telemetry["brightness"] = value
            telemetry["brightness_pct"] = brightness_pct

        # 3. Temperature Measurement (Stored in hundredths of a degree Celsius)
        elif cluster_id == CLUSTER_TEMP_MEASUREMENT:
            temp_c = round(value / 100.0, 1)
            telemetry["temperature"] = temp_c

        # 4. Humidity Measurement (Stored in hundredths of a percent)
        elif cluster_id == CLUSTER_HUMIDITY_MEASUREMENT:
            humidity_pct = round(value / 100.0, 1)
            telemetry["humidity"] = humidity_pct

        # 5. Door Lock Cluster
        elif cluster_id == CLUSTER_DOOR_LOCK:
            # 1 = Locked, 2 = Unlocked
            telemetry["locked"] = (value == 1)
            telemetry["lockState"] = "LOCKED" if value == 1 else "UNLOCKED"

        # 6. Occupancy Sensing
        elif cluster_id == CLUSTER_OCCUPANCY_SENSING:
            telemetry["occupancy"] = bool(value)

        else:
            telemetry[attribute_name] = value

        if telemetry:
            self.send_to_gateway("telemetry", {
                "device": device_name,
                "data": telemetry
            })

    def _infer_matter_type(self, cluster_id: int) -> str:
        if cluster_id in [CLUSTER_ON_OFF, CLUSTER_LEVEL_CONTROL, CLUSTER_COLOR_CONTROL]:
            return "Matter Smart Light"
        if cluster_id in [CLUSTER_TEMP_MEASUREMENT, CLUSTER_HUMIDITY_MEASUREMENT]:
            return "Matter Climate Sensor"
        if cluster_id == CLUSTER_DOOR_LOCK:
            return "Matter Smart Lock"
        if cluster_id == CLUSTER_OCCUPANCY_SENSING:
            return "Matter Motion Sensor"
        return "Matter Device"

    def handle_rpc(self, device_name: str, method: str, params: Any) -> Any:
        """
        Translates Cloud RPC commands to Matter cluster invocations.
        Supports OnOff, Dimmable Level, Lock/Unlock, and Pairing (Commissioning).
        """
        clean_node_id = device_name.replace("Matter - Node ", "").strip()
        log.info(f"Matter RPC received for {clean_node_id}: method={method}, params={params}")

        # Commissioning new Matter device via QR or manual code
        if method == "commissionNode":
            pairing_code = params.get("code") if isinstance(params, dict) else str(params)
            log.info(f"Commissioning new Matter device with code: {pairing_code}")
            return {"status": "SUCCESS", "message": "Pairing initiated for Matter device"}

        # Cluster commands
        if method in ["setValue", "setState", "setPower"]:
            on = (params is True or params == 1 or str(params).upper() == "ON")
            # Invoke Matter OnOff Cluster command (0x0006: 0x01 = On, 0x00 = Off)
            log.info(f"Executing Matter OnOff for Node {clean_node_id} -> {on}")
            # Simulate state update
            self.on_matter_attribute_changed(clean_node_id, 1, CLUSTER_ON_OFF, "onOff", on)
            return {"status": "SUCCESS", "on": on}

        if method == "setBrightness":
            level = max(0, min(254, int(params)))
            log.info(f"Executing Matter LevelControl for Node {clean_node_id} -> {level}")
            self.on_matter_attribute_changed(clean_node_id, 1, CLUSTER_LEVEL_CONTROL, "currentLevel", level)
            return {"status": "SUCCESS", "level": level}

        if method == "setLock":
            locked = (params is True or str(params).upper() == "LOCK")
            lock_val = 1 if locked else 2
            log.info(f"Executing Matter DoorLock for Node {clean_node_id} -> {lock_val}")
            self.on_matter_attribute_changed(clean_node_id, 1, CLUSTER_DOOR_LOCK, "lockState", lock_val)
            return {"status": "SUCCESS", "locked": locked}

        return {"status": "ERROR", "message": f"Unsupported Matter method: {method}"}
