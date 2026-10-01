#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UNIQ Smart Home - Native Matter Connector (Matter over Thread & Wi-Fi)
Integrates with Matter Controller Server, translates Matter clusters into telemetry,
manages Bridge decomposition via MatterDeviceMapper, and executes cluster RPC commands.
"""

import json
import logging
import os
import threading
import time
from typing import Dict, Any, Optional, Tuple
from connectors.base_connector import BaseConnector

try:
    from matter.matter_client import MatterClient
    from matter.commission_service import MatterCommissionService
    from matter.device_mapper import MatterDeviceMapper
except Exception:
    try:
        from ..matter.matter_client import MatterClient
        from ..matter.commission_service import MatterCommissionService
        from ..matter.device_mapper import MatterDeviceMapper
    except Exception:
        MatterClient = None
        MatterCommissionService = None
        MatterDeviceMapper = None

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
        
        # Persistent storage for mapped devices
        storage_path = self.config.get("storage_path", "/var/lib/uniq-gateway/matter")
        os.makedirs(storage_path, exist_ok=True)
        registry_file = os.path.join(storage_path, "matter_device_registry.json")

        self.mapper: Optional[Any] = MatterDeviceMapper(registry_file) if MatterDeviceMapper else None
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

        # Restore known devices from persistent registry
        self._restore_from_registry()

    def _restore_from_registry(self):
        if not self.mapper:
            return
        log.info(f"Restoring {len(self.mapper._registry)} devices from persistent Matter registry...")
        for key, dev in self.mapper._registry.items():
            device_name = dev.get("device_name")
            device_type = dev.get("device_type", "Matter Device")
            if device_name:
                self.send_to_gateway("connect", {
                    "device": device_name,
                    "type": device_type
                })

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
            try:
                self.commission_service.stop()
            except Exception:
                pass
        if self.client:
            try:
                self.client.stop()
            except Exception:
                pass

    def _on_matter_connection_change(self, is_connected: bool):
        log.info(f"Matter server connection status: {'CONNECTED' if is_connected else 'DISCONNECTED'}")
        if is_connected and self.client:
            threading.Thread(target=self._initial_sync, daemon=True, name="MatterInitialSync").start()

    def _initial_sync(self):
        time.sleep(1.5)
        if not self.client or not self.client.is_connected:
            return
        log.info("Fetching commissioned Matter nodes from matterjs-server...")
        res = self.client.get_nodes()
        if res.get("success"):
            nodes = res.get("result", {})
            if isinstance(nodes, dict):
                for nid, node_data in nodes.items():
                    self._sync_single_node(node_data)
            elif isinstance(nodes, list):
                for node_data in nodes:
                    self._sync_single_node(node_data)
        else:
            log.warning(f"Failed to fetch Matter nodes on initial sync: {res.get('error')}")

    def sync_node_by_id(self, node_id: int):
        """Called when a new device is commissioned or refreshed."""
        log.info(f"Synchronizing newly commissioned Matter node {node_id}...")
        if self.client and self.client.is_connected:
            resp = self.client.get_node(node_id)
            if resp.get("success"):
                node_data = resp.get("result", {})
                self._sync_single_node(node_data)
            else:
                log.warning(f"Could not fetch details for node {node_id}: {resp.get('error')}")

    def _sync_single_node(self, node_data: Dict[str, Any]):
        node_id = str(node_data.get("node_id", ""))
        if not node_id:
            return

        log.info(f"Processing topology for Matter Node {node_id}...")
        self.known_nodes[node_id] = node_data

        if self.mapper:
            devices = self.mapper.parse_node_topology(node_data)
            log.info(f"Matter Node {node_id} unpacked into {len(devices)} device(s): {[d['device_name'] for d in devices]}")
            for dev in devices:
                device_name = dev["device_name"]
                device_type = dev["device_type"]
                attributes = dev.get("attributes", {})

                self.send_to_gateway("connect", {
                    "device": device_name,
                    "type": device_type
                })
                self.send_to_gateway("attributes", {
                    "device": device_name,
                    "data": attributes
                })
        else:
            # Fallback direct registration
            device_name = f"Matter - Node {node_id}"
            self.send_to_gateway("connect", {"device": device_name, "type": "Matter Device"})

    def _on_matter_node_event(self, event_type: str, data: Dict[str, Any]):
        node_id = str(data.get("node_id", ""))
        log.info(f"Matter node event [{event_type}] received for node {node_id}")
        if event_type in ["node_added", "node_updated"]:
            self._sync_single_node(data)

    def _on_matter_attribute_event(self, node_id: int, endpoint_id: int, cluster_id: int, attribute_id: int, value: Any):
        """Translates cluster attribute update into device telemetry."""
        # Find corresponding device name from mapper
        target_device = None
        if self.mapper:
            for key, dev in self.mapper._registry.items():
                if int(dev.get("node_id", -1)) == int(node_id) and int(dev.get("endpoint_id", -1)) == int(endpoint_id):
                    target_device = dev.get("device_name")
                    break

        if not target_device:
            target_device = f"Matter - Node {node_id}"

        telemetry = {}

        if cluster_id == CLUSTER_ON_OFF:
            on = bool(value)
            telemetry["state"] = "ON" if on else "OFF"
            telemetry["onOff"] = on
            # Update live state in mapper
            if self.mapper and target_device:
                for k, d in self.mapper._registry.items():
                    if d.get("device_name") == target_device:
                        d["state"] = "ON" if on else "OFF"

        elif cluster_id == CLUSTER_LEVEL_CONTROL:
            brightness_pct = int(round((value / 254.0) * 100)) if value else 0
            telemetry["brightness"] = value
            telemetry["brightness_pct"] = brightness_pct
        elif cluster_id == CLUSTER_TEMP_MEASUREMENT:
            telemetry["temperature"] = round(value / 100.0, 1)
        elif cluster_id == CLUSTER_HUMIDITY_MEASUREMENT:
            telemetry["humidity"] = round(value / 100.0, 1)
        elif cluster_id == CLUSTER_DOOR_LOCK:
            telemetry["locked"] = (value == 1)
            telemetry["lockState"] = "LOCKED" if value == 1 else "UNLOCKED"
        elif cluster_id == CLUSTER_OCCUPANCY_SENSING:
            telemetry["occupancy"] = bool(value)
        else:
            telemetry[f"cluster_{cluster_id}_attr_{attribute_id}"] = value

        if telemetry:
            self.send_to_gateway("telemetry", {
                "device": target_device,
                "data": telemetry
            })

    def handle_rpc(self, device_name: str, method: str, params: Any) -> Any:
        """
        Translates Cloud or Local Web RPC commands to Matter cluster invocations.
        """
        log.info(f"Matter RPC received for [{device_name}]: method={method}, params={params}")

        # Commissioning request
        if method == "commissionNode":
            code = params.get("code") if isinstance(params, dict) else str(params)
            if self.client:
                return self.client.commission_with_code(code=code)
            return {"status": "ERROR", "message": "Matter client offline"}

        # Resolve node_id and endpoint_id
        node_id = None
        endpoint_id = 1

        if self.mapper:
            node_ep = self.mapper.get_node_endpoint_by_device_name(device_name)
            if node_ep:
                node_id, endpoint_id = node_ep

        if node_id is None:
            clean = device_name.replace("Matter - Node ", "").strip()
            if clean.isdigit():
                node_id = int(clean)

        if node_id is None:
            return {"status": "ERROR", "message": f"Could not resolve Matter node for device: {device_name}"}

        # Cluster commands
        if method in ["setValue", "setState", "setPower"]:
            on = (params is True or params == 1 or str(params).upper() == "ON")
            cmd = "On" if on else "Off"
            if self.client:
                res = self.client.device_command(node_id, endpoint_id, CLUSTER_ON_OFF, cmd)
                log.info(f"Matter device_command OnOff ({cmd}) result: {res}")
            self._on_matter_attribute_event(node_id, endpoint_id, CLUSTER_ON_OFF, 0, 1 if on else 0)
            return {"status": "SUCCESS", "on": on}

        elif method == "setBrightness":
            level = max(0, min(254, int(params)))
            if self.client:
                res = self.client.device_command(node_id, endpoint_id, CLUSTER_LEVEL_CONTROL, "MoveToLevel", {"level": level, "transitionTime": 0})
                log.info(f"Matter device_command MoveToLevel ({level}) result: {res}")
            self._on_matter_attribute_event(node_id, endpoint_id, CLUSTER_LEVEL_CONTROL, 0, level)
            return {"status": "SUCCESS", "level": level}

        elif method == "setLock":
            locked = (params is True or str(params).upper() == "LOCK")
            lock_cmd = "LockDoor" if locked else "UnlockDoor"
            if self.client:
                res = self.client.device_command(node_id, endpoint_id, CLUSTER_DOOR_LOCK, lock_cmd)
                log.info(f"Matter device_command DoorLock ({lock_cmd}) result: {res}")
            self._on_matter_attribute_event(node_id, endpoint_id, CLUSTER_DOOR_LOCK, 0, 1 if locked else 2)
            return {"status": "SUCCESS", "locked": locked}

        return {"status": "ERROR", "message": f"Unsupported Matter method: {method}"}

    def server_side_rpc_handler(self, rpc_request: Dict[str, Any]) -> Dict[str, Any]:
        dev = rpc_request.get("device", "")
        data = rpc_request.get("data", {})
        method = data.get("method", "")
        params = data.get("params")
        return self.handle_rpc(dev, method, params)
