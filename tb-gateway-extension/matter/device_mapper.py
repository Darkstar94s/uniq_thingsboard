# -*- coding: utf-8 -*-
# Copyright 2026 UNIQ Smart Home
# Matter to ThingsBoard Topology Parser, Cluster Converter & Device Registry

import json
import logging
import os
import threading
from typing import Dict, Any, List, Tuple, Optional

log = logging.getLogger("UniqMatterDeviceMapper")

# Standard Matter Device Types
DEVICE_TYPE_ROOT_NODE = 0x0016           # 22
DEVICE_TYPE_AGGREGATOR_BRIDGE = 0x000E   # 14
DEVICE_TYPE_BRIDGED_NODE = 0x0013        # 19
DEVICE_TYPE_ON_OFF_LIGHT = 0x0100        # 256
DEVICE_TYPE_DIMMABLE_LIGHT = 0x0101      # 257
DEVICE_TYPE_COLOR_LIGHT = 0x0102         # 258
DEVICE_TYPE_EXT_COLOR_LIGHT = 0x010D     # 269
DEVICE_TYPE_ON_OFF_LIGHT_SWITCH = 0x0103 # 259
DEVICE_TYPE_DIMMER_SWITCH = 0x0104       # 260
DEVICE_TYPE_GENERIC_SWITCH = 0x000F      # 15
DEVICE_TYPE_ON_OFF_PLUG = 0x010A         # 266
DEVICE_TYPE_DIMMABLE_PLUG = 0x010B       # 267
DEVICE_TYPE_DOOR_LOCK = 0x000A           # 10
DEVICE_TYPE_WINDOW_COVERING = 0x0202     # 514
DEVICE_TYPE_THERMOSTAT = 0x0301          # 769
DEVICE_TYPE_FAN = 0x002B                 # 43
DEVICE_TYPE_TEMP_SENSOR = 0x0302         # 770
DEVICE_TYPE_HUMIDITY_SENSOR = 0x0307     # 775
DEVICE_TYPE_OCCUPANCY_SENSOR = 0x0107    # 263
DEVICE_TYPE_CONTACT_SENSOR = 0x0015      # 21
DEVICE_TYPE_LIGHT_SENSOR = 0x0106        # 262
DEVICE_TYPE_AIR_QUALITY_SENSOR = 0x002C  # 44

DEVICE_TYPE_NAMES = {
    DEVICE_TYPE_ON_OFF_LIGHT: "Smart Light",
    DEVICE_TYPE_DIMMABLE_LIGHT: "Dimmable Light",
    DEVICE_TYPE_COLOR_LIGHT: "Color Light",
    DEVICE_TYPE_EXT_COLOR_LIGHT: "Extended Color Light",
    DEVICE_TYPE_ON_OFF_LIGHT_SWITCH: "Smart Switch",
    DEVICE_TYPE_DIMMER_SWITCH: "Dimmer Switch",
    DEVICE_TYPE_GENERIC_SWITCH: "Generic Switch",
    DEVICE_TYPE_ON_OFF_PLUG: "Smart Socket",
    DEVICE_TYPE_DIMMABLE_PLUG: "Dimmable Socket",
    DEVICE_TYPE_DOOR_LOCK: "Smart Door Lock",
    DEVICE_TYPE_WINDOW_COVERING: "Smart Curtain/Cover",
    DEVICE_TYPE_THERMOSTAT: "Smart Thermostat",
    DEVICE_TYPE_FAN: "Smart Fan",
    DEVICE_TYPE_TEMP_SENSOR: "Temperature Sensor",
    DEVICE_TYPE_HUMIDITY_SENSOR: "Humidity Sensor",
    DEVICE_TYPE_OCCUPANCY_SENSOR: "Motion Sensor",
    DEVICE_TYPE_CONTACT_SENSOR: "Door/Window Sensor",
    DEVICE_TYPE_LIGHT_SENSOR: "Light Sensor",
    DEVICE_TYPE_AIR_QUALITY_SENSOR: "Air Quality Sensor",
}

# Standard Matter Cluster IDs
CLUSTER_DESCRIPTOR = 0x001D              # 29
CLUSTER_POWER_SOURCE = 0x0001            # 1
CLUSTER_ON_OFF = 0x0006                  # 6
CLUSTER_LEVEL_CONTROL = 0x0008           # 8
CLUSTER_BASIC_INFORMATION = 0x0028       # 40
CLUSTER_BRIDGED_DEVICE_BASIC = 0x0039    # 57
CLUSTER_DOOR_LOCK = 0x0101               # 257
CLUSTER_COLOR_CONTROL = 0x0300           # 768
CLUSTER_TEMP_MEASUREMENT = 0x0402        # 1026
CLUSTER_HUMIDITY_MEASUREMENT = 0x0405    # 1029
CLUSTER_OCCUPANCY_SENSING = 0x0406       # 1030
CLUSTER_POWER_MEASUREMENT = 0x0090       # 144 (Matter 1.3 Electrical Power Measurement)
CLUSTER_ENERGY_MEASUREMENT = 0x0091      # 145 (Matter 1.3 Electrical Energy Measurement)
CLUSTER_METERING = 0x0702                # 1794 (Simple Metering)
CLUSTER_ELECTRICAL_MEASUREMENT = 0x0B04  # 2820 (Electrical Measurement)

# Functional clusters that indicate an actionable smart-home endpoint
FUNCTIONAL_CLUSTERS = {
    str(CLUSTER_ON_OFF),
    str(CLUSTER_LEVEL_CONTROL),
    str(CLUSTER_COLOR_CONTROL),
    str(CLUSTER_DOOR_LOCK),
    str(CLUSTER_TEMP_MEASUREMENT),
    str(CLUSTER_HUMIDITY_MEASUREMENT),
    str(CLUSTER_OCCUPANCY_SENSING),
    str(CLUSTER_ELECTRICAL_MEASUREMENT),
    str(CLUSTER_POWER_MEASUREMENT),
    str(CLUSTER_ENERGY_MEASUREMENT),
    str(CLUSTER_METERING),
}

def resolve_device_type_and_category(
    product_name: str = "",
    vendor_name: str = "",
    device_type_ids: list = None,
    clusters: dict = None,
    endpoint_count: int = 1
) -> Tuple[str, str]:
    """
    Accurately identifies device type (e.g. 'Smart Switch', 'Smart Socket', 'Smart Light')
    and category ('switch', 'socket', 'lighting', 'sensor', 'climate', 'security', 'bridge', 'other')
    by prioritizing product name and electrical measurement clusters over generic Matter device type IDs.
    """
    p_lower = (product_name or "").lower()
    v_lower = (vendor_name or "").lower()
    combined_name = f"{v_lower} {p_lower}"
    cl_keys = set(str(k) for k in (clusters or {}).keys()) if clusters else set()
    dt_ids = device_type_ids or []

    # 1. Matter Bridges & Hubs
    if any(k in combined_name for k in ["bridge", "aggregator", "hub", "gateway", "موزع", "جسر"]):
        return ("Matter Bridge", "bridge")
    if DEVICE_TYPE_AGGREGATOR_BRIDGE in dt_ids:
        return ("Matter Bridge", "bridge")

    # 2. Smart Sockets / Plugs / Outlets (e.g. Smart Plug, Socket, Outlet, Huayu Lian plug, Tuya plug)
    has_power_cluster = bool(cl_keys.intersection({
        str(CLUSTER_ELECTRICAL_MEASUREMENT), "2820", "0x0B04", "0x0b04",
        str(CLUSTER_POWER_MEASUREMENT), "144", "0x0090",
        str(CLUSTER_METERING), "1794", "0x0702",
        str(CLUSTER_ENERGY_MEASUREMENT), "145", "0x0091"
    }))

    is_known_plug_vendor = any(k in v_lower or k in combined_name for k in ["huayu", "huayu lian", "huayulian", "tuya", "gosund", "meross", "kasa", "tapo", "eve"])
    if any(k in combined_name for k in ["plug", "socket", "outlet", "power plug", "مقبس", "فيش", "بلك", "افياش"]):
        return ("Smart Socket", "socket")
    if is_known_plug_vendor and endpoint_count <= 1:
        return ("Smart Socket", "socket")
    if has_power_cluster:
        return ("Smart Socket", "socket")
    if any(dt in [DEVICE_TYPE_ON_OFF_PLUG, DEVICE_TYPE_DIMMABLE_PLUG] for dt in dt_ids):
        return ("Smart Socket", "socket")

    # 3. Wall Switches / Multi-gang Switches (e.g. SONOFF SwitchMan, Aqara Switch, Tuya Switch)
    if any(k in combined_name for k in ["switchman", "wall switch", "gang", "relay", "breaker", "مفتاح", "رليه", "قاطع"]) or (
        "switch" in combined_name and "socket" not in combined_name and "plug" not in combined_name
    ):
        return ("Smart Switch", "switch")
    if endpoint_count > 1 and any(dt in [DEVICE_TYPE_ON_OFF_LIGHT_SWITCH, DEVICE_TYPE_DIMMER_SWITCH, DEVICE_TYPE_GENERIC_SWITCH, DEVICE_TYPE_ON_OFF_LIGHT] for dt in dt_ids):
        return ("Smart Switch", "switch")

    # 4. Smart Lighting (Bulbs, Lamps, Downlights, LED Strips)
    if any(k in combined_name for k in ["bulb", "lamp", "downlight", "spotlight", "strip", "ceiling", "لمبة", "إنارة", "إضاءة", "سبوت"]) or (
        "light" in combined_name and "switch" not in combined_name
    ):
        return ("Smart Light", "lighting")
    if any(dt in [DEVICE_TYPE_COLOR_LIGHT, DEVICE_TYPE_EXT_COLOR_LIGHT, DEVICE_TYPE_DIMMABLE_LIGHT] for dt in dt_ids):
        return ("Smart Light", "lighting")
    if cl_keys.intersection({str(CLUSTER_COLOR_CONTROL), "768", str(CLUSTER_LEVEL_CONTROL), "8"}):
        return ("Smart Light", "lighting")

    # 5. Sensors
    if any(k in combined_name for k in ["sensor", "temp", "humidity", "motion", "occupancy", "contact", "door", "window", "حساس"]):
        return ("Sensor", "sensor")
    if any(dt in [DEVICE_TYPE_TEMP_SENSOR, DEVICE_TYPE_HUMIDITY_SENSOR, DEVICE_TYPE_OCCUPANCY_SENSOR, DEVICE_TYPE_CONTACT_SENSOR, DEVICE_TYPE_LIGHT_SENSOR, DEVICE_TYPE_AIR_QUALITY_SENSOR] for dt in dt_ids):
        for dt in dt_ids:
            if dt in DEVICE_TYPE_NAMES:
                return (DEVICE_TYPE_NAMES[dt], "sensor")
        return ("Sensor", "sensor")
    if cl_keys.intersection({str(CLUSTER_TEMP_MEASUREMENT), "1026", str(CLUSTER_HUMIDITY_MEASUREMENT), "1029", str(CLUSTER_OCCUPANCY_SENSING), "1030"}):
        return ("Sensor", "sensor")

    # 6. Climate & Security
    if any(k in combined_name for k in ["thermostat", "fan", "hvac", "ac", "تكييف", "مروحة"]):
        return ("Smart Thermostat", "climate")
    if any(k in combined_name for k in ["lock", "curtain", "blind", "shade", "قفل", "ستارة"]):
        return ("Smart Lock/Cover", "security")

    # 7. Fallback based on Matter device type or OnOff cluster
    for dt in dt_ids:
        if dt in DEVICE_TYPE_NAMES:
            name = DEVICE_TYPE_NAMES[dt]
            cat = "switch" if "Switch" in name else ("socket" if "Socket" in name else ("lighting" if "Light" in name else "other"))
            return (name, cat)

    if cl_keys.intersection({str(CLUSTER_ON_OFF), "6"}):
        return ("Smart Switch", "switch")

    return ("Smart Device", "other")


def infer_device_category(device_type: str, clusters: dict = None, product_name: str = "") -> str:
    """Wrapper helper for backward compatibility."""
    _, cat = resolve_device_type_and_category(product_name=product_name, clusters=clusters, device_type_ids=[])
    if cat != "other":
        return cat
    dt = (device_type or "").lower()
    if any(k in dt for k in ["switch", "relay", "مفتاح"]): return "switch"
    if any(k in dt for k in ["plug", "socket", "outlet", "مقبس"]): return "socket"
    if any(k in dt for k in ["light", "bulb", "lamp", "إنارة"]): return "lighting"
    if any(k in dt for k in ["sensor", "temp", "حساس"]): return "sensor"
    return "other"

# Basic Information cluster attribute IDs (Matter spec)
BASIC_ATTR_VENDOR_NAME = "1"
BASIC_ATTR_VENDOR_ID = "2"
BASIC_ATTR_PRODUCT_NAME = "3"
BASIC_ATTR_PRODUCT_ID = "4"
BASIC_ATTR_NODE_LABEL = "5"
BASIC_ATTR_SERIAL_NUMBER = "15"
BASIC_ATTR_UNIQUE_ID = "18"


class MatterDeviceMapper:
    """
    Manages persistent registry of Matter devices and converts Matter clusters into
    ThingsBoard telemetry and attributes.  Correctly isolates bridged nodes from
    Matter bridges.  Supports both nested endpoint/cluster format and flat
    matter.js ``"ep/cluster/attr"`` attribute format.
    """

    def __init__(self, registry_file_path: str):
        self.registry_file_path = registry_file_path
        self._lock = threading.Lock()
        # Mapping: "(node_id)_(endpoint_id)" -> device metadata dict
        self._registry: Dict[str, Dict[str, Any]] = {}
        # Reverse mapping: "ThingsBoard Device Name" -> (node_id, endpoint_id)
        self._name_to_node_ep: Dict[str, Tuple[int, int]] = {}
        # Live device states cache: "(node_id)_(endpoint_id)" -> {state, brightness, …}
        self._device_states: Dict[str, Dict[str, Any]] = {}
        self._load_registry()

    # =========================================================================
    # Persistence
    # =========================================================================

    def _load_registry(self):
        with self._lock:
            if os.path.exists(self.registry_file_path):
                try:
                    with open(self.registry_file_path, "r", encoding="utf-8") as f:
                        raw_data = json.load(f)

                    # Support both new structure { "registry": ..., "device_states": ... } and legacy flat dict
                    if isinstance(raw_data, dict) and "registry" in raw_data:
                        self._registry = raw_data.get("registry", {})
                        self._device_states = raw_data.get("device_states", {})
                    elif isinstance(raw_data, dict):
                        self._registry = raw_data
                        self._device_states = {}

                    for key, data in self._registry.items():
                        device_name = data.get("device_name")
                        node_id = data.get("node_id")
                        endpoint_id = data.get("endpoint_id")
                        if device_name and node_id is not None and endpoint_id is not None:
                            self._name_to_node_ep[device_name] = (int(node_id), int(endpoint_id))

                    log.info(f"Loaded {len(self._registry)} mapped Matter devices and {len(self._device_states)} cached device states.")
                except Exception as e:
                    log.error(f"Failed to load Matter device registry: {e}")
                    self._registry = {}
                    self._device_states = {}

    def _save_registry(self):
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.registry_file_path)), exist_ok=True)
            with open(self.registry_file_path, "w", encoding="utf-8") as f:
                data_to_save = {
                    "registry": self._registry,
                    "device_states": self._device_states
                }
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log.error(f"Failed to save Matter device registry: {e}")

    # =========================================================================
    # Public helpers
    # =========================================================================

    def get_node_endpoint_by_device_name(self, device_name: str) -> Optional[Tuple[int, int]]:
        return self._name_to_node_ep.get(device_name)

    def update_device_state(self, node_id: int, endpoint_id: int, state_data: Dict[str, Any]):
        """Update the live state cache for a device endpoint and persist."""
        key = f"{node_id}_{endpoint_id}"
        with self._lock:
            if key not in self._device_states:
                self._device_states[key] = {}
            self._device_states[key].update(state_data)
            self._save_registry()

    def get_device_state(self, node_id: int, endpoint_id: int) -> Dict[str, Any]:
        """Get the cached live state for a device endpoint."""
        with self._lock:
            state = self._device_states.get(f"{node_id}_{endpoint_id}")
            if state:
                return dict(state)
            # Fallback to endpoint 1 if looking up node
            fallback = self._device_states.get(f"{node_id}_1")
            return dict(fallback) if fallback else {}

    def remove_node(self, node_id: int) -> List[str]:
        """
        Removes all endpoints, states, and mappings for a given node_id from registry.
        Returns the list of removed ThingsBoard device names.
        """
        removed_devices = []
        with self._lock:
            prefix = f"{node_id}_"
            keys_to_del = [k for k in self._registry.keys() if k.startswith(prefix) or k == str(node_id)]
            for k in keys_to_del:
                entry = self._registry.pop(k, None)
                if entry and "device_name" in entry:
                    d_name = entry["device_name"]
                    removed_devices.append(d_name)
                    self._name_to_node_ep.pop(d_name, None)

            # Remove from device states cache
            state_keys_to_del = [k for k in self._device_states.keys() if k.startswith(prefix) or k == str(node_id)]
            for k in state_keys_to_del:
                self._device_states.pop(k, None)

            self._save_registry()
            log.info(f"Removed node {node_id} from registry. Removed device names: {removed_devices}")
        return removed_devices

    # =========================================================================
    # Flat Attribute Format Parser (matter.js server)
    # =========================================================================

    def _parse_flat_attributes_to_endpoints(self, attributes: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
        """
        Converts matter.js flat attribute format (e.g., ``"1/6/0": false``)
        into structured endpoint dict with clusters and device_types.
        """
        ep_dict: Dict[int, Dict[str, Any]] = {}

        for attr_path, value in attributes.items():
            parts = str(attr_path).split("/")
            if len(parts) != 3:
                continue
            try:
                ep_id = int(parts[0])
                cluster_id = int(parts[1])
                attr_id = int(parts[2])
            except (ValueError, TypeError):
                continue

            if ep_id not in ep_dict:
                ep_dict[ep_id] = {"endpoint_id": ep_id, "clusters": {}, "device_types": []}

            cluster_key = str(cluster_id)
            if cluster_key not in ep_dict[ep_id]["clusters"]:
                ep_dict[ep_id]["clusters"][cluster_key] = {}

            ep_dict[ep_id]["clusters"][cluster_key][str(attr_id)] = value

            # Descriptor cluster (29), attribute 0 = deviceTypeList
            if cluster_id == CLUSTER_DESCRIPTOR and attr_id == 0 and isinstance(value, list):
                for dt_entry in value:
                    if isinstance(dt_entry, dict):
                        dt_id = dt_entry.get("0") or dt_entry.get("device_type")
                        if dt_id is not None:
                            ep_dict[ep_id]["device_types"].append({"device_type": int(dt_id)})

        return ep_dict

    @staticmethod
    def _has_functional_cluster(ep_content: Dict[str, Any]) -> bool:
        """Check if endpoint has actionable smart home clusters."""
        clusters = ep_content.get("clusters", {})
        return bool(FUNCTIONAL_CLUSTERS.intersection(clusters.keys()))

    # =========================================================================
    # Node Topology Parsing
    # =========================================================================

    def parse_node_topology(self, node_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parses a Matter node object received from matterjs-server.
        Supports both nested endpoint format and flat matter.js attribute format.
        Splits Matter bridges into separate ThingsBoard device definitions.
        Creates separate devices for multi-endpoint nodes (e.g., 3-gang switches).
        Returns a list of device definitions to register/update in ThingsBoard.
        """
        node_id = int(node_data.get("node_id", 0))
        if not node_id:
            return []

        # ── Build endpoint dict from either nested or flat format ──
        endpoints = node_data.get("endpoints", {})
        ep_dict: Dict[int, Dict[str, Any]] = {}

        if endpoints:
            if isinstance(endpoints, dict):
                for k, v in endpoints.items():
                    try:
                        ep_dict[int(k)] = v
                    except ValueError:
                        pass
            elif isinstance(endpoints, list):
                for ep in endpoints:
                    ep_id = ep.get("endpoint_id")
                    if ep_id is not None:
                        ep_dict[int(ep_id)] = ep

        if not ep_dict and "attributes" in node_data:
            ep_dict = self._parse_flat_attributes_to_endpoints(node_data.get("attributes", {}))

        if not ep_dict:
            log.warning(f"No endpoints found for node {node_id}. Cannot parse topology.")
            return []

        # ── Extract basic node info from root endpoint (0) ──
        root_ep = ep_dict.get(0, {})
        root_clusters = root_ep.get("clusters", {})
        basic_info = (
            root_clusters.get(str(CLUSTER_BASIC_INFORMATION), {})
            or root_clusters.get(CLUSTER_BASIC_INFORMATION, {})
        )

        # Matter Basic Information attribute IDs (1=vendorName, 3=productName, 15=serialNumber)
        vendor_name = (
            basic_info.get("vendorName")
            or basic_info.get(BASIC_ATTR_VENDOR_NAME)
            or "Matter"
        )
        product_name = (
            basic_info.get("productName")
            or basic_info.get(BASIC_ATTR_PRODUCT_NAME)
            or "Device"
        )
        serial_number = (
            basic_info.get("serialNumber")
            or basic_info.get(BASIC_ATTR_SERIAL_NUMBER)
            or f"NODE-{node_id}"
        )

        # ── Determine if node is a Matter Bridge (Aggregator) ──
        is_bridge = False
        for ep_id, ep_content in ep_dict.items():
            device_types = ep_content.get("device_types", [])
            for dt in device_types:
                dt_id = dt.get("device_type") if isinstance(dt, dict) else dt
                if dt_id == DEVICE_TYPE_AGGREGATOR_BRIDGE:
                    is_bridge = True
                    break

        devices_to_sync = []

        if is_bridge:
            # ── Bridge Device ──
            bridge_name = f"Matter Bridge - {vendor_name} {product_name} ({node_id})"
            root_device = self._get_or_create_device_entry(
                node_id=node_id, endpoint_id=0, device_name=bridge_name,
                device_type="Matter Bridge", vendor_name=vendor_name,
                product_name=product_name, serial_number=serial_number,
                is_bridged=False, bridge_name=None
            )
            devices_to_sync.append(root_device)

            for ep_id, ep_content in ep_dict.items():
                if ep_id == 0:
                    continue

                clusters = ep_content.get("clusters", {})
                bridged_info = (
                    clusters.get(str(CLUSTER_BRIDGED_DEVICE_BASIC), {})
                    or clusters.get(CLUSTER_BRIDGED_DEVICE_BASIC, {})
                )
                node_label = bridged_info.get("nodeLabel") or bridged_info.get("5") or ""
                b_vendor = bridged_info.get("vendorName") or bridged_info.get("1") or vendor_name
                b_product = bridged_info.get("productName") or bridged_info.get("3") or ""
                b_serial = bridged_info.get("serialNumber") or bridged_info.get("15") or f"{serial_number}-EP{ep_id}"

                inferred_type = "Bridged Smart Device"
                for dt in ep_content.get("device_types", []):
                    dt_id = dt.get("device_type") if isinstance(dt, dict) else dt
                    if dt_id in DEVICE_TYPE_NAMES:
                        inferred_type = DEVICE_TYPE_NAMES[dt_id]
                        break

                display_title = node_label or b_product or inferred_type
                bridged_device_name = f"Bridged - {vendor_name} {display_title} (N{node_id}-EP{ep_id})"

                bridged_device = self._get_or_create_device_entry(
                    node_id=node_id, endpoint_id=ep_id, device_name=bridged_device_name,
                    device_type=inferred_type, vendor_name=b_vendor,
                    product_name=b_product or display_title, serial_number=b_serial,
                    is_bridged=True, bridge_name=bridge_name
                )
                devices_to_sync.append(bridged_device)

        else:
            # ── Direct Matter Device (Wi-Fi Plug, Switch, Light, Lock, Sensor) ──
            # Find all functional endpoints (skip root endpoint 0)
            functional_eps = {}
            for ep_id, ep_content in ep_dict.items():
                if ep_id == 0:
                    continue
                if self._has_functional_cluster(ep_content):
                    functional_eps[ep_id] = ep_content

            if len(functional_eps) > 1:
                # Multi-endpoint device (e.g., 3-gang switch) → one device per endpoint
                for ep_id in sorted(functional_eps.keys()):
                    ep_content = functional_eps[ep_id]
                    dt_ids = [dt.get("device_type") if isinstance(dt, dict) else dt for dt in ep_content.get("device_types", [])]
                    resolved_type, resolved_cat = resolve_device_type_and_category(
                        product_name=product_name,
                        vendor_name=vendor_name,
                        device_type_ids=dt_ids,
                        clusters=ep_content.get("clusters", {}),
                        endpoint_count=len(functional_eps)
                    )

                    ep_device_name = f"Matter - {product_name} CH{ep_id} (N{node_id})"
                    ep_device = self._get_or_create_device_entry(
                        node_id=node_id, endpoint_id=ep_id,
                        device_name=ep_device_name, device_type=resolved_type,
                        vendor_name=vendor_name, product_name=product_name,
                        serial_number=f"{serial_number}-CH{ep_id}",
                        is_bridged=False, bridge_name=None,
                        category=resolved_cat
                    )
                    devices_to_sync.append(ep_device)
            else:
                # Single endpoint device
                if functional_eps:
                    primary_ep_id = list(functional_eps.keys())[0]
                else:
                    primary_ep_id = 1 if 1 in ep_dict else 0
                primary_ep = ep_dict.get(primary_ep_id, {})
                dt_ids = [dt.get("device_type") if isinstance(dt, dict) else dt for dt in primary_ep.get("device_types", [])]

                resolved_type, resolved_cat = resolve_device_type_and_category(
                    product_name=product_name,
                    vendor_name=vendor_name,
                    device_type_ids=dt_ids,
                    clusters=primary_ep.get("clusters", {}),
                    endpoint_count=1
                )

                direct_device_name = f"Matter - {vendor_name} {product_name} ({node_id})"
                direct_device = self._get_or_create_device_entry(
                    node_id=node_id, endpoint_id=primary_ep_id,
                    device_name=direct_device_name, device_type=resolved_type,
                    vendor_name=vendor_name, product_name=product_name,
                    serial_number=serial_number,
                    is_bridged=False, bridge_name=None,
                    category=resolved_cat
                )
                devices_to_sync.append(direct_device)

        return devices_to_sync

    # =========================================================================
    # Device Entry Factory
    # =========================================================================

    def _get_or_create_device_entry(
        self,
        node_id: int,
        endpoint_id: int,
        device_name: str,
        device_type: str,
        vendor_name: str,
        product_name: str,
        serial_number: str,
        is_bridged: bool,
        bridge_name: Optional[str],
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        key = f"{node_id}_{endpoint_id}"
        if not category:
            _, category = resolve_device_type_and_category(product_name=product_name, vendor_name=vendor_name)

        with self._lock:
            existing = self._registry.get(key)
            if existing:
                # Keep existing consistent name
                assigned_name = existing.get("device_name", device_name)
                # Auto-correct category and device type if re-inferred
                existing["device_type"] = device_type
                existing["category"] = category
            else:
                assigned_name = device_name
                self._registry[key] = {
                    "node_id": node_id,
                    "endpoint_id": endpoint_id,
                    "device_name": assigned_name,
                    "device_type": device_type,
                    "category": category,
                    "vendor_name": vendor_name,
                    "product_name": product_name,
                    "serial_number": serial_number,
                    "is_bridged": is_bridged,
                    "bridge_name": bridge_name
                }
                self._save_registry()

            self._name_to_node_ep[assigned_name] = (node_id, endpoint_id)

            return {
                "node_id": node_id,
                "endpoint_id": endpoint_id,
                "device_name": assigned_name,
                "device_type": device_type,
                "category": category,
                "attributes": {
                    "vendor": vendor_name,
                    "model": product_name,
                    "category": category,
                    "serialNumber": serial_number,
                    "nodeId": node_id,
                    "endpointId": endpoint_id,
                    "isBridged": is_bridged,
                    "bridgeName": bridge_name or "None",
                    "protocol": "Matter over Wi-Fi" if not is_bridged else "Matter Bridge"
                }
            }

    # =========================================================================
    # Attribute Update Conversion
    # =========================================================================

    def convert_attribute_update(
        self,
        node_id: int,
        endpoint_id: int,
        cluster_id: int,
        attribute_id: int,
        value: Any
    ) -> Optional[Tuple[str, Dict[str, Any], Dict[str, Any]]]:
        """
        Translates a Matter cluster attribute update into ThingsBoard (device_name, telemetry, attributes).
        Also updates the internal state cache.
        Returns None if attribute does not map to relevant smart home state.
        """
        key = f"{node_id}_{endpoint_id}"
        entry = self._registry.get(key)
        if not entry:
            # Auto-fallback: try matching node_id with primary endpoint
            key = f"{node_id}_1"
            entry = self._registry.get(key)

        if not entry:
            return None

        device_name = entry["device_name"]
        telemetry: Dict[str, Any] = {}
        attributes: Dict[str, Any] = {}

        # 1. OnOff Cluster (0x0006)
        if cluster_id == CLUSTER_ON_OFF:
            # Attribute 0 is onOff
            if attribute_id in [0, "0", "onOff"]:
                state_val = "ON" if value in [True, 1, "true", "True"] else "OFF"
                telemetry["state"] = state_val
                telemetry["onOff"] = (state_val == "ON")

        # 2. LevelControl Cluster (0x0008 - Dimmers)
        elif cluster_id == CLUSTER_LEVEL_CONTROL:
            if attribute_id in [0, "0", "currentLevel"]:
                try:
                    level_int = int(value)
                    # Matter level ranges 0..254
                    percent = int(round((level_int / 254.0) * 100))
                    telemetry["brightness"] = max(0, min(100, percent))
                except Exception:
                    pass

        # 3. Temperature Measurement (0x0402 / 1026)
        elif cluster_id == CLUSTER_TEMP_MEASUREMENT:
            if attribute_id in [0, "0", "measuredValue"]:
                try:
                    raw_temp = float(value)
                    # Matter reports temperature in 100ths of a degree Celsius (e.g. 2150 = 21.5°C)
                    telemetry["temperature"] = round(raw_temp / 100.0, 2)
                except Exception:
                    pass

        # 4. Relative Humidity Measurement (0x0405 / 1029)
        elif cluster_id == CLUSTER_HUMIDITY_MEASUREMENT:
            if attribute_id in [0, "0", "measuredValue"]:
                try:
                    raw_hum = float(value)
                    # Matter reports relative humidity in 100ths of 1% (e.g. 5500 = 55.0%)
                    telemetry["humidity"] = round(raw_hum / 100.0, 2)
                except Exception:
                    pass

        # 5. Door Lock Cluster (0x0101 / 257)
        elif cluster_id == CLUSTER_DOOR_LOCK:
            if attribute_id in [0, "0", "lockState"]:
                # 1 = Locked, 2 = Unlocked
                is_locked = (value == 1 or value == "Locked")
                telemetry["lockState"] = "LOCKED" if is_locked else "UNLOCKED"
                telemetry["locked"] = is_locked

        # 6. Power Source Cluster (0x0001 / 1 - Battery)
        elif cluster_id == CLUSTER_POWER_SOURCE:
            if attribute_id in [12, "12", "batteryPercentRemaining"]:
                try:
                    # Stored in half percents (0..200 represents 0..100%)
                    telemetry["battery"] = round(float(value) / 2.0, 1)
                except Exception:
                    pass

        # 7. Electrical Measurement (0x0B04 / 2820)
        elif cluster_id == CLUSTER_ELECTRICAL_MEASUREMENT:
            # RMSVoltage = 0x0505 (1285), RMSCurrent = 0x0508 (1288), ActivePower = 0x050B (1291)
            if attribute_id in [0x050B, 1291, "1291", "activePower"]:
                telemetry["power"] = round(float(value), 2)
            elif attribute_id in [0x0505, 1285, "1285", "rmsVoltage"]:
                telemetry["voltage"] = round(float(value), 2)
            elif attribute_id in [0x0508, 1288, "1288", "rmsCurrent"]:
                # In mA or A
                cur_val = float(value)
                telemetry["current"] = round(cur_val / 1000.0, 3) if cur_val > 50 else round(cur_val, 3)

        # 8. Metering (0x0702 / 1794)
        elif cluster_id == CLUSTER_METERING:
            if attribute_id in [0, "0", "currentSummationDelivered"]:
                telemetry["energy"] = round(float(value) / 1000.0 if float(value) > 10000 else float(value), 3)

        # 9. Electrical Power Measurement (0x0090 / 144 - Matter 1.3)
        elif cluster_id == CLUSTER_POWER_MEASUREMENT:
            if attribute_id in [4, "4", "activePower"]:
                # in mW or W
                p_val = float(value)
                telemetry["power"] = round(p_val / 1000.0, 2) if p_val > 1000 else round(p_val, 2)
            elif attribute_id in [0, "0", "voltage"]:
                v_val = float(value)
                telemetry["voltage"] = round(v_val / 1000.0, 2) if v_val > 1000 else round(v_val, 2)
            elif attribute_id in [1, "1", "activeCurrent"]:
                c_val = float(value)
                telemetry["current"] = round(c_val / 1000.0, 3) if c_val > 1000 else round(c_val, 3)

        # 10. Electrical Energy Measurement (0x0091 / 145 - Matter 1.3)
        elif cluster_id == CLUSTER_ENERGY_MEASUREMENT:
            if attribute_id in [0, "0", "cumulativeEnergyImported"]:
                try:
                    if isinstance(value, dict):
                        e_val = float(value.get("energy", 0))
                    else:
                        e_val = float(value)
                    telemetry["energy"] = round(e_val / 1000000.0, 3) if e_val > 10000 else round(e_val, 3)
                except Exception:
                    pass

        # 11. Occupancy (0x0406 / 1030)
        elif cluster_id == CLUSTER_OCCUPANCY_SENSING:
            if attribute_id in [0, "0", "occupancy"]:
                telemetry["occupancy"] = bool(int(value) & 1)

        if not telemetry and not attributes:
            return None

        # Update live state cache
        if telemetry:
            self.update_device_state(node_id, endpoint_id, telemetry)

        return (device_name, telemetry, attributes)

    def set_device_category(self, node_id: int, endpoint_id: int, category: str, device_type: Optional[str] = None) -> bool:
        """Manually override the category of a device endpoint and save."""
        key = f"{node_id}_{endpoint_id}"
        with self._lock:
            entry = self._registry.get(key)
            if entry:
                entry["category"] = category
                if device_type:
                    entry["device_type"] = device_type
                self._save_registry()
                return True
        return False

    # =========================================================================
    # RPC to Matter Command Mapping
    # =========================================================================

    def map_rpc_to_matter_command(
        self,
        device_name: Optional[str] = None,
        method: str = "setState",
        params: Any = True,
        node_id: Optional[int] = None,
        endpoint_id: Optional[int] = None
    ) -> Optional[Tuple[int, int, int, str, Dict[str, Any]]]:
        """
        Maps a ThingsBoard RPC command to a Matter cluster command.
        Returns: (node_id, endpoint_id, cluster_id, command_name, command_args)
        """
        if node_id is None or endpoint_id is None:
            if device_name:
                node_ep = self.get_node_endpoint_by_device_name(device_name)
                if node_ep:
                    node_id, endpoint_id = node_ep

        if node_id is None or endpoint_id is None:
            log.warning(f"Device name '{device_name}' or (node_id, endpoint_id) not found in Matter registry for RPC.")
            return None

        # A. On / Off commands
        if method in ["setState", "setValue", "writeState"]:
            is_on = params in [True, 1, "ON", "true", "True", "on"]
            cmd_name = "on" if is_on else "off"
            return (node_id, endpoint_id, CLUSTER_ON_OFF, cmd_name, {})

        elif method in ["toggle", "toggleState"]:
            return (node_id, endpoint_id, CLUSTER_ON_OFF, "toggle", {})

        # B. Level / Dimmer commands
        elif method in ["setBrightness", "setLevel"]:
            try:
                percent = float(params)
                level_254 = max(0, min(254, int(round((percent / 100.0) * 254))))
                return (node_id, endpoint_id, CLUSTER_LEVEL_CONTROL, "MoveToLevel", {
                    "level": level_254,
                    "transitionTime": 0
                })
            except Exception:
                pass

        # C. Door Lock commands
        elif method in ["setLock", "setDoorLock"]:
            lock = params in [True, 1, "LOCK", "locked", "true"]
            cmd_name = "LockDoor" if lock else "UnlockDoor"
            return (node_id, endpoint_id, CLUSTER_DOOR_LOCK, cmd_name, {})

        return None
