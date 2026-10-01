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
from typing import Dict, Any, Optional
from connectors.base_connector import BaseConnector

try:
    from matter.matter_client import MatterClient
    from matter.commission_service import MatterCommissionService
except Exception:
    try:
        from ..matter.matter_client import MatterClient
        from ..matter.commission_service import MatterCommissionService
    except Exception:
        MatterClient = None
        MatterCommissionService = None

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
        self.commission_port = int(self.config.get("commission_port", 8282))
        self.known_nodes = {}
        self.client: Optional[Any] = None
        self.commission_service: Optional[Any] = None

        if MatterClient:
            self.client = MatterClient(
                server_url=self.server_url,
                on_node_event=self._on_matter_node_event,
                on_attribute_event=self._on_matter_attribute_event,
                on_connection_change=self._on_matter_connection_change,
                reconnect_interval_sec=5
            )

        if MatterCommissionService:
            self.commission_service = MatterCommissionService(
                host="0.0.0.0",
                port=self.commission_port,
                matter_connector=self
            )

    def start(self):
        log.info(f"Starting UNIQ Matter Connector (Target: {self.server_url})...")
        self.is_running = True

        if self.client:
            self.client.start()

        if self.commission_service:
            self.commission_service.start()

        log.info(f"UNIQ Matter Connector running. Local Web Dashboard on http://0.0.0.0:{self.commission_port}/")

    def stop(self):
        log.info("Stopping UNIQ Matter Connector...")
        self.is_running = False
        if self.commission_service:
            self.commission_service.stop()
        if self.client:
            self.client.stop()

    def _on_matter_connection_change(self, is_connected: bool):
        log.info(f"Matter server connection status: {'CONNECTED' if is_connected else 'DISCONNECTED'}")
        if is_connected and self.client:
            # Query existing nodes
            threading.Thread(target=self._initial_sync, daemon=True).start()

    def _initial_sync(self):
        time.sleep(1)
        if not self.client or not self.client.is_connected:
            return
        res = self.client.get_nodes()
        if res.get("success"):
            nodes = res.get("result", {})
            if isinstance(nodes, dict):
                for nid, node_data in nodes.items():
                    self._register_node(str(nid), node_data)
            elif isinstance(nodes, list):
                for node_data in nodes:
                    nid = str(node_data.get("node_id", ""))
                    if nid:
                        self._register_node(nid, node_data)

    def _on_matter_node_event(self, event_type: str, data: Dict[str, Any]):
        node_id = str(data.get("node_id", ""))
        log.info(f"Matter node event [{event_type}] for node {node_id}")
        if event_type in ["node_added", "node_updated"]:
            self._register_node(node_id, data)

    def _on_matter_attribute_event(self, node_id: int, endpoint_id: int, cluster_id: int, attribute_id: int, value: Any):
        self.on_matter_attribute_changed(str(node_id), endpoint_id, cluster_id, f"attr_{attribute_id}", value)

    def _register_node(self, node_id: str, node_data: Dict[str, Any]):
        device_name = f"Matter - Node {node_id}"
        dev_type = "Matter Device"

        endpoints = node_data.get("endpoints", {})
        if isinstance(endpoints, dict):
            for ep_id, ep in endpoints.items():
                clusters = ep.get("clusters", {})
                if 6 in clusters or "6" in clusters:
                    dev_type = "Matter Smart Light"
                elif 257 in clusters or "257" in clusters:
                    dev_type = "Matter Smart Lock"
                elif 1026 in clusters or "1026" in clusters:
                    dev_type = "Matter Climate Sensor"

        self.known_nodes[node_id] = {"type": dev_type, "data": node_data}

        self.send_to_gateway("connect", {
            "device": device_name,
            "type": dev_type
        })
        self.send_to_gateway("attributes", {
            "device": device_name,
            "data": {
                "protocol": "Matter 1.3",
                "nodeId": node_id,
                "transport": "Wi-Fi / Thread"
            }
        })

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

        if cluster_id == CLUSTER_ON_OFF:
            telemetry["state"] = "ON" if value else "OFF"
            telemetry["onOff"] = bool(value)
        elif cluster_id == CLUSTER_LEVEL_CONTROL:
            brightness_pct = int(round((value / 254.0) * 100)) if value else 0
            telemetry["brightness"] = value
            telemetry["brightness_pct"] = brightness_pct
        elif cluster_id == CLUSTER_TEMP_MEASUREMENT:
            temp_c = round(value / 100.0, 1)
            telemetry["temperature"] = temp_c
        elif cluster_id == CLUSTER_HUMIDITY_MEASUREMENT:
            humidity_pct = round(value / 100.0, 1)
            telemetry["humidity"] = humidity_pct
        elif cluster_id == CLUSTER_DOOR_LOCK:
            telemetry["locked"] = (value == 1)
            telemetry["lockState"] = "LOCKED" if value == 1 else "UNLOCKED"
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

    def sync_node_by_id(self, node_id: int):
        if self.client and self.client.is_connected:
            resp = self.client.get_node(node_id)
            if resp.get("success"):
                self._register_node(str(node_id), resp.get("result", {}))

    def handle_rpc(self, device_name: str, method: str, params: Any) -> Any:
        """
        Translates Cloud RPC commands to Matter cluster invocations.
        """
        clean_node_id = device_name.replace("Matter - Node ", "").strip()
        log.info(f"Matter RPC received for {clean_node_id}: method={method}, params={params}")

        # Commissioning
        if method == "commissionNode":
            code = params.get("code") if isinstance(params, dict) else str(params)
            if self.client:
                res = self.client.commission_with_code(code=code)
                return res
            return {"status": "SUCCESS", "message": "Pairing initiated for Matter device"}

        # Cluster commands
        if method in ["setValue", "setState", "setPower"]:
            on = (params is True or params == 1 or str(params).upper() == "ON")
            cmd = "On" if on else "Off"
            if self.client and clean_node_id.isdigit():
                self.client.device_command(int(clean_node_id), 1, CLUSTER_ON_OFF, cmd)
            self.on_matter_attribute_changed(clean_node_id, 1, CLUSTER_ON_OFF, "onOff", on)
            return {"status": "SUCCESS", "on": on}

        if method == "setBrightness":
            level = max(0, min(254, int(params)))
            if self.client and clean_node_id.isdigit():
                self.client.device_command(int(clean_node_id), 1, CLUSTER_LEVEL_CONTROL, "MoveToLevel", {"level": level, "transitionTime": 0})
            self.on_matter_attribute_changed(clean_node_id, 1, CLUSTER_LEVEL_CONTROL, "currentLevel", level)
            return {"status": "SUCCESS", "level": level}

        if method == "setLock":
            locked = (params is True or str(params).upper() == "LOCK")
            lock_cmd = "LockDoor" if locked else "UnlockDoor"
            if self.client and clean_node_id.isdigit():
                self.client.device_command(int(clean_node_id), 1, CLUSTER_DOOR_LOCK, lock_cmd)
            self.on_matter_attribute_changed(clean_node_id, 1, CLUSTER_DOOR_LOCK, "lockState", 1 if locked else 2)
            return {"status": "SUCCESS", "locked": locked}

        return {"status": "ERROR", "message": f"Unsupported Matter method: {method}"}

