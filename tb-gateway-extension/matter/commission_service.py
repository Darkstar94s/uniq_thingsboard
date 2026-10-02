# -*- coding: utf-8 -*-
# Copyright 2026 UNIQ Smart Home
# Local HTTP Commissioning Microservice & Web Dashboard Server for UNIQ Hub

import json
import logging
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Optional, Dict, List, Tuple, Union

try:
    from .hub_auth import HubAuthManager
except Exception:
    try:
        from hub_auth import HubAuthManager
    except Exception:
        from matter.hub_auth import HubAuthManager

log = logging.getLogger("UniqMatterCommissionService")

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
INDEX_HTML_PATH = os.path.join(WEB_DIR, "index.html")


class CommissionRequestHandler(BaseHTTPRequestHandler):
    """
    Handles local Hub web dashboard, authentication, device control, and commissioning.
    """

    def log_message(self, format, *args):
        # Silence default HTTP access logs into standard python logger
        log.debug("%s - - [%s] %s" % (self.address_string(), self.log_date_time_string(), format % args))

    def _send_json_response(self, status_code: int, data: Any):
        response_bytes = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(response_bytes)

    def _send_html_response(self, html_content: str):
        response_bytes = html_content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def _get_auth_token(self) -> Optional[str]:
        auth_hdr = self.headers.get("Authorization", "")
        if auth_hdr.startswith("Bearer "):
            return auth_hdr.replace("Bearer ", "").strip()
        return None

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        service = self.server.service  # type: ignore
        from urllib.parse import urlparse, parse_qs
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)

        # 1. Web Dashboard (Home Page)
        if parsed_path.path in ["/", "/index.html"]:
            if os.path.exists(INDEX_HTML_PATH):
                with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
                    self._send_html_response(f.read())
            else:
                self._send_html_response("<h1>UNIQ Smart Hub Web UI</h1><p>Dashboard template not found.</p>")
            return

        # 1.1 Static Web Assets (Logos & Favicon)
        elif parsed_path.path in ["/uniq-logo.png", "/uniq-logo-dark.png", "/uniq-logo-light.png", "/favicon.ico"]:
            filename = parsed_path.path.lstrip("/")
            if filename == "favicon.ico":
                filename = "uniq-logo-dark.png"
            asset_path = os.path.join(os.path.dirname(INDEX_HTML_PATH), filename)
            if os.path.exists(asset_path):
                with open(asset_path, "rb") as f:
                    img_data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(img_data)))
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                self.wfile.write(img_data)
                return

        # 2. System Status API
        elif parsed_path.path in ["/matter/status", "/status", "/api/status"]:
            status_data = service.get_status()
            self._send_json_response(200, status_data)
            return

        # 3. Live Devices API (Protected)
        elif parsed_path.path in ["/api/devices"]:
            token = self._get_auth_token()
            if not service.auth_manager.validate_token(token):
                self._send_json_response(401, {"error": "Unauthorized. Please login with valid Hub PIN."})
                return

            devices_data = service.get_live_devices()
            self._send_json_response(200, {"devices": devices_data})
            return

        # 4. Raw Matter Node Clusters & Datapoints Inspection (Protected)
        elif parsed_path.path in ["/api/devices/raw", "/api/node/raw"]:
            token = self._get_auth_token()
            if not service.auth_manager.validate_token(token):
                self._send_json_response(401, {"error": "Unauthorized"})
                return

            nid_list = query_params.get("node_id", []) or query_params.get("id", [])
            if not nid_list:
                self._send_json_response(400, {"error": "Missing node_id query param"})
                return

            try:
                nid = int(nid_list[0])
                if service.connector and service.connector.client:
                    node_raw = service.connector.client.get_node(nid)
                    self._send_json_response(200, node_raw)
                else:
                    self._send_json_response(503, {"error": "Matter client not available"})
            except Exception as e:
                self._send_json_response(500, {"error": str(e)})
            return

        # 5. Rooms API (Protected)
        elif parsed_path.path == "/api/rooms":
            token = self._get_auth_token()
            if not service.auth_manager.validate_token(token):
                self._send_json_response(401, {"error": "Unauthorized"})
                return
            self._send_json_response(200, service.get_rooms_data())
            return

        # 6. Floorplan API (Protected)
        elif parsed_path.path == "/api/floorplan":
            token = self._get_auth_token()
            if not service.auth_manager.validate_token(token):
                self._send_json_response(401, {"error": "Unauthorized"})
                return
            self._send_json_response(200, service.get_floorplan_data())
            return

        # 7. Scenarios API (Protected)
        elif parsed_path.path == "/api/scenarios":
            token = self._get_auth_token()
            if not service.auth_manager.validate_token(token):
                self._send_json_response(401, {"error": "Unauthorized"})
                return
            self._send_json_response(200, service.get_scenarios_data())
            return

        # 8. Cloud Config & Sync API (Protected)
        elif parsed_path.path == "/api/cloud/config":
            token = self._get_auth_token()
            if not service.auth_manager.validate_token(token):
                self._send_json_response(401, {"error": "Unauthorized"})
                return
            self._send_json_response(200, service.get_cloud_config())
            return

        else:
            self._send_json_response(404, {"error": "Not Found", "path": self.path})

    def do_POST(self):
        service = self.server.service  # type: ignore
        from urllib.parse import urlparse
        req_path = urlparse(self.path).path

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length <= 0:
            self._send_json_response(400, {"status": "error", "error": "Empty request body"})
            return

        try:
            post_body = self.rfile.read(content_length)
            req_data = json.loads(post_body.decode("utf-8"))
        except Exception as e:
            self._send_json_response(400, {"status": "error", "error": f"Invalid JSON body: {e}"})
            return

        # 1. Admin PIN Login
        if req_path == "/api/login":
            pin = req_data.get("pin", "")
            token = service.auth_manager.verify_pin(pin)
            if token:
                self._send_json_response(200, {"success": True, "token": token})
            else:
                self._send_json_response(401, {"success": False, "error": "Invalid PIN"})
            return

        # 2. Local Device RPC Control
        elif req_path == "/api/control":
            token = self._get_auth_token()
            if not service.auth_manager.validate_token(token):
                self._send_json_response(401, {"error": "Unauthorized"})
                return

            device_name = req_data.get("device")
            method = req_data.get("method", "setState")
            params = req_data.get("params", True)
            node_id = req_data.get("node_id")
            endpoint_id = req_data.get("endpoint_id")

            result = service.control_device(
                device_name=device_name,
                method=method,
                params=params,
                node_id=int(node_id) if node_id is not None else None,
                endpoint_id=int(endpoint_id) if endpoint_id is not None else None
            )
            self._send_json_response(200, result)
            return

        # 3. Rename Device API
        elif req_path == "/api/devices/rename":
            token = self._get_auth_token()
            if not service.auth_manager.validate_token(token):
                self._send_json_response(401, {"error": "Unauthorized"})
                return

            nid = req_data.get("node_id")
            epid = req_data.get("endpoint_id", 1)
            new_name = req_data.get("name", "").strip()
            if nid is not None and new_name and service.connector and service.connector.mapper:
                ok = service.connector.mapper.rename_device(int(nid), int(epid), new_name)
                self._send_json_response(200, {"success": ok, "name": new_name})
            else:
                self._send_json_response(400, {"success": False, "error": "Missing parameters"})
            return

        # 4. Change Device Category API
        elif req_path == "/api/devices/set_category":
            token = self._get_auth_token()
            if not service.auth_manager.validate_token(token):
                self._send_json_response(401, {"error": "Unauthorized"})
                return

            nid = req_data.get("node_id")
            epid = req_data.get("endpoint_id", 1)
            new_cat = req_data.get("category", "socket")
            new_type = req_data.get("device_type")
            if nid is not None and service.connector and service.connector.mapper:
                service.connector.mapper.set_device_category(int(nid), int(epid), str(new_cat), new_type)
                self._send_json_response(200, {"success": True, "message": f"Category updated to {new_cat}"})
            else:
                self._send_json_response(400, {"success": False, "error": "Missing node_id"})
            return

        # 5. Delete / Decommission Device API
        elif req_path in ["/api/devices/delete", "/api/devices/remove"]:
            token = self._get_auth_token()
            if not service.auth_manager.validate_token(token):
                self._send_json_response(401, {"error": "Unauthorized"})
                return

            nid = req_data.get("node_id")
            if nid is None:
                self._send_json_response(400, {"success": False, "error": "Missing node_id parameter"})
                return

            res = service.remove_device(int(nid))
            self._send_json_response(200, res)
            return

        # 6. Rooms Save API
        elif req_path == "/api/rooms":
            token = self._get_auth_token()
            if not service.auth_manager.validate_token(token):
                self._send_json_response(401, {"error": "Unauthorized"})
                return
            ok = service.save_rooms_data(req_data)
            self._send_json_response(200, {"success": ok})
            return

        # 7. Floorplan Save API
        elif req_path == "/api/floorplan":
            token = self._get_auth_token()
            if not service.auth_manager.validate_token(token):
                self._send_json_response(401, {"error": "Unauthorized"})
                return
            ok = service.save_floorplan_data(req_data)
            self._send_json_response(200, {"success": ok})
            return

        # 8. Scenarios Save & Run API
        elif req_path == "/api/scenarios":
            token = self._get_auth_token()
            if not service.auth_manager.validate_token(token):
                self._send_json_response(401, {"error": "Unauthorized"})
                return
            ok = service.save_scenarios_data(req_data)
            self._send_json_response(200, {"success": ok})
            return

        elif req_path == "/api/scenarios/run":
            token = self._get_auth_token()
            if not service.auth_manager.validate_token(token):
                self._send_json_response(401, {"error": "Unauthorized"})
                return
            scen_id = req_data.get("scenario_id")
            res = service.run_scenario(scen_id)
            self._send_json_response(200, res)
            return

        # 9. Cloud Config Save & Manual Sync API
        elif req_path == "/api/cloud/config":
            token = self._get_auth_token()
            if not service.auth_manager.validate_token(token):
                self._send_json_response(401, {"error": "Unauthorized"})
                return
            res = service.save_cloud_config(req_data)
            self._send_json_response(200, res)
            return

        elif req_path == "/api/cloud/sync":
            token = self._get_auth_token()
            if not service.auth_manager.validate_token(token):
                self._send_json_response(401, {"error": "Unauthorized"})
                return
            res = service.sync_all_to_cloud()
            self._send_json_response(200, res)
            return

        # 10. Change PIN API
        elif req_path == "/api/settings/pin":
            token = self._get_auth_token()
            if not service.auth_manager.validate_token(token):
                self._send_json_response(401, {"error": "Unauthorized"})
                return

            cur = req_data.get("current_pin", "")
            new_p = req_data.get("new_pin", "")
            ok = service.auth_manager.change_pin(cur, new_p)
            if ok:
                self._send_json_response(200, {"success": True, "message": "PIN updated successfully"})
            else:
                self._send_json_response(400, {"success": False, "error": "Current PIN is incorrect or new PIN is too short"})
            return

        # 5. Matter Commissioning Endpoint
        elif self.path in ["/matter/commission", "/commission", "/api/commission"]:
            code = req_data.get("code")
            if not code:
                self._send_json_response(400, {
                    "status": "error",
                    "error": "Missing required 'code' parameter (e.g. Matter QR code string 'MT:...' or setup PIN)."
                })
                return

            network_only = bool(req_data.get("network_only", False))  # False = allow BLE commissioning
            wifi_ssid = req_data.get("wifi_ssid")
            wifi_password = req_data.get("wifi_password")

            result = service.commission_device(
                code=code,
                network_only=network_only,
                wifi_ssid=wifi_ssid,
                wifi_password=wifi_password
            )

            status_code = 200 if result.get("status") == "success" else 400
            self._send_json_response(status_code, result)
            return

        else:
            self._send_json_response(404, {"error": "Not Found", "path": self.path})


class MatterCommissionService:
    """
    Runs the lightweight local REST API and Web Dashboard on UNIQ Hub.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8282, matter_connector: Any = None):
        self.host = host
        self.port = port
        self.connector = matter_connector
        self.auth_manager = HubAuthManager()
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._is_running = False

    def start(self):
        if self._is_running:
            return
        self._is_running = True
        try:
            HTTPServer.allow_reuse_address = True
            self._server = HTTPServer((self.host, self.port), CommissionRequestHandler)
            self._server.service = self  # type: ignore
            self._thread = threading.Thread(
                target=self._server.serve_forever,
                daemon=True,
                name="MatterCommissionHttpServer"
            )
            self._thread.start()
            log.info(f"UNIQ Hub Local Web Dashboard & API listening on http://{self.host}:{self.port}")
        except Exception as e:
            log.error(f"Failed to start UNIQ Hub Local HTTP Service: {e}")

    def stop(self):
        self._is_running = False
        if self._server:
            try:
                self._server.shutdown()
                self._server.server_close()
            except Exception:
                pass
        log.info("UNIQ Hub Local Web Dashboard stopped.")

    def get_status(self) -> dict:
        is_connected = False
        registered_count = 0
        server_url = "unknown"

        if self.connector:
            if hasattr(self.connector, "client") and self.connector.client:
                is_connected = self.connector.client.is_connected
                server_url = self.connector.client.server_url
            if hasattr(self.connector, "mapper") and self.connector.mapper:
                registered_count = len(self.connector.mapper._registry)

        return {
            "status": "online" if self._is_running else "offline",
            "matterjs_connected": is_connected,
            "matterjs_server_url": server_url,
            "commissioned_devices_count": registered_count,
            "hub": "UNIQ Smart Home Hub",
            "version": "2.4.0-uniq",
            "local_web_gui": f"http://{self.host}:{self.port}/"
        }

    def get_live_devices(self) -> list:
        if not self.connector or not hasattr(self.connector, "mapper"):
            return []

        try:
            from .device_mapper import resolve_device_type_and_category
        except Exception:
            try:
                from device_mapper import resolve_device_type_and_category
            except Exception:
                from matter.device_mapper import resolve_device_type_and_category

        devices = []
        registry = self.connector.mapper._registry

        # Attempt to retrieve live node data from Matter client
        nodes_cache = {}
        if hasattr(self.connector, "client") and self.connector.client and self.connector.client.is_connected:
            try:
                nodes_resp = self.connector.client.get_nodes(timeout=2.0)
                if nodes_resp.get("success"):
                    raw_n = nodes_resp.get("result", [])
                    if isinstance(raw_n, dict):
                        nodes_cache = raw_n
                    elif isinstance(raw_n, list):
                        for n in raw_n:
                            n_id = n.get("node_id") or n.get("nodeId")
                            if n_id is not None:
                                nodes_cache[int(n_id)] = n
            except Exception as e:
                log.debug(f"Could not query live nodes cache: {e}")

        for key, dev in registry.items():
            device_name = dev.get("device_name")
            is_bridged = dev.get("is_bridged", False)
            node_id = dev.get("node_id")
            endpoint_id = dev.get("endpoint_id")
            dev_type = dev.get("device_type", "Smart Device")
            product_name = dev.get("product_name", "")
            vendor_name = dev.get("vendor_name", "Matter")

            # Resolve accurate category and device_type from product name and vendor
            resolved_type, resolved_cat = resolve_device_type_and_category(
                product_name=product_name,
                vendor_name=vendor_name,
                device_type_ids=[],
                is_bridged=is_bridged
            )

            category = dev.get("category")
            if not category or category == "other" or resolved_cat != "other":
                category = resolved_cat
                if resolved_type != "Smart Device":
                    dev_type = resolved_type

            # Check if device has OnOff capability
            has_onoff = any(kw in dev_type for kw in ["Light", "Relay", "Socket", "Plug", "Switch", "Generic Switch"]) or category in ["lighting", "socket", "switch"]

            # Get live state from mapper cache
            state_data = dict(self.connector.mapper.get_device_state(node_id, endpoint_id))

            # If state_data lacks sensor/power data, scan raw node attributes
            if node_id in nodes_cache:
                nd = nodes_cache[node_id]
                flat_attrs = nd.get("attributes", {})
                ep_clusters = {}
                endpoints = nd.get("endpoints", {})
                if isinstance(endpoints, dict):
                    ep_clusters = (endpoints.get(str(endpoint_id)) or endpoints.get(endpoint_id, {})).get("clusters", {})
                elif isinstance(endpoints, list):
                    for ep in endpoints:
                        if ep.get("endpoint_id") == endpoint_id:
                            ep_clusters = ep.get("clusters", {})
                            break

                # 1. Temperature (Cluster 1026 / 0x0402)
                for t_key in [f"{endpoint_id}/1026/0", f"{endpoint_id}/1026/measuredValue", f"{endpoint_id}/0x0402/0", f"{endpoint_id}/0x0402/measuredValue", "0/1026/0"]:
                    if t_key in flat_attrs:
                        try:
                            raw_t = float(flat_attrs[t_key])
                            if raw_t not in [-32768, 0x8000]:
                                state_data["temperature"] = round(raw_t / 100.0 if raw_t > 200 else raw_t, 2)
                                break
                        except Exception:
                            pass
                if ep_clusters:
                    c1026 = ep_clusters.get("1026") or ep_clusters.get(1026) or ep_clusters.get("0x0402") or {}
                    t_val = c1026.get("measuredValue") if "measuredValue" in c1026 else c1026.get("0")
                    if t_val is not None:
                        try:
                            raw_t = float(t_val)
                            if raw_t not in [-32768, 0x8000]:
                                state_data["temperature"] = round(raw_t / 100.0 if raw_t > 200 else raw_t, 2)
                        except Exception:
                            pass

                # 2. Humidity (Cluster 1029 / 0x0405)
                for h_key in [f"{endpoint_id}/1029/0", f"{endpoint_id}/1029/measuredValue", f"{endpoint_id}/0x0405/0", f"{endpoint_id}/0x0405/measuredValue", "0/1029/0"]:
                    if h_key in flat_attrs:
                        try:
                            raw_h = float(flat_attrs[h_key])
                            if raw_h not in [0xFFFF, 65535]:
                                state_data["humidity"] = round(raw_h / 100.0 if raw_h > 100 else raw_h, 2)
                                break
                        except Exception:
                            pass
                if ep_clusters:
                    c1029 = ep_clusters.get("1029") or ep_clusters.get(1029) or ep_clusters.get("0x0405") or {}
                    h_val = c1029.get("measuredValue") if "measuredValue" in c1029 else c1029.get("0")
                    if h_val is not None:
                        try:
                            raw_h = float(h_val)
                            if raw_h not in [0xFFFF, 65535]:
                                state_data["humidity"] = round(raw_h / 100.0 if raw_h > 100 else raw_h, 2)
                        except Exception:
                            pass

                # 3. Battery (Cluster 1 / 0x0001)
                for b_key in [f"{endpoint_id}/1/12", f"{endpoint_id}/1/batteryPercentRemaining", f"{endpoint_id}/0x0001/12", "0/1/12", "0/1/batteryPercentRemaining"]:
                    if b_key in flat_attrs:
                        try:
                            raw_b = float(flat_attrs[b_key])
                            state_data["battery"] = round(raw_b / 2.0 if raw_b <= 200 else raw_b, 1)
                            break
                        except Exception:
                            pass

                # 4. State / OnOff (Cluster 6 / 0x0006) - Real-time Sync for ON and OFF
                matched_onoff = False
                for s_key in [f"{endpoint_id}/6/0", f"{endpoint_id}/6/onOff", f"{endpoint_id}/0x0006/0"]:
                    if s_key in flat_attrs:
                        val = flat_attrs[s_key]
                        state_data["state"] = "ON" if val in [True, 1, "true", "True", "on", "ON"] else "OFF"
                        matched_onoff = True
                        break
                if not matched_onoff and ep_clusters:
                    c6 = ep_clusters.get("6") or ep_clusters.get(6) or ep_clusters.get("0x0006") or {}
                    if "onOff" in c6 or "0" in c6:
                        val = c6.get("onOff") if "onOff" in c6 else c6.get("0")
                        state_data["state"] = "ON" if val in [True, 1, "true", "True", "on", "ON"] else "OFF"

                # 5. Electrical Measurement (Cluster 2820 / 1794 / 144)
                for p_key in [f"{endpoint_id}/2820/1291", f"{endpoint_id}/2820/0x050B", f"{endpoint_id}/1794/1024", f"{endpoint_id}/144/4"]:
                    if p_key in flat_attrs:
                        try:
                            p_raw = float(flat_attrs[p_key])
                            state_data["power"] = round(p_raw / 1000.0 if p_raw > 50000 else (p_raw / 10.0 if p_raw > 5000 else p_raw), 2)
                            break
                        except Exception:
                            pass

                self.connector.mapper.update_device_state(node_id, endpoint_id, state_data)

            current_state = state_data.get("state", "OFF")

            dev_info = {
                "device_name": device_name,
                "device_type": dev_type,
                "category": category,
                "node_id": node_id,
                "endpoint_id": endpoint_id,
                "vendor": dev.get("vendor_name", "Matter"),
                "model": dev.get("product_name", ""),
                "serial_number": dev.get("serial_number", ""),
                "is_bridged": is_bridged,
                "bridge_name": dev.get("bridge_name"),
                "has_onoff": has_onoff,
                "state": current_state,
                "temperature": state_data.get("temperature"),
                "humidity": state_data.get("humidity"),
                "battery": state_data.get("battery"),
                "brightness": state_data.get("brightness"),
                "power": state_data.get("power"),
                "voltage": state_data.get("voltage"),
                "current": state_data.get("current"),
                "energy": state_data.get("energy"),
            }
            devices.append(dev_info)

        return devices

    def control_device(self, device_name: Optional[str] = None, method: str = "setState", params: Any = True, node_id: Optional[int] = None, endpoint_id: Optional[int] = None) -> dict:
        if not self.connector:
            return {"success": False, "error": "Connector not initialized"}

        # Direct cluster command execution
        if node_id is not None and endpoint_id is not None and self.connector.client and self.connector.client.is_connected:
            is_on = params in [True, 1, "ON", "true", "True", "on"]
            cmd_name = "on" if is_on else "off"
            if method in ["toggle", "toggleState"]:
                cmd_name = "toggle"

            resp = self.connector.client.device_command(
                node_id=int(node_id),
                endpoint_id=int(endpoint_id),
                cluster_id=6,
                command_name=cmd_name,
                command_args={},
                timeout=8.0
            )

            # Update live state in mapper cache immediately
            if method in ["toggle", "toggleState"]:
                cur = self.connector.mapper.get_device_state(int(node_id), int(endpoint_id))
                is_on = (cur.get("state") != "ON")

            state_update = {"state": "ON" if is_on else "OFF", "onOff": is_on}
            self.connector.mapper.update_device_state(int(node_id), int(endpoint_id), state_update)
            return {"success": True, "result": resp.get("result"), "state": state_update["state"]}

        # If node_id and endpoint_id are given, resolve device_name if needed
        if not device_name and node_id is not None and endpoint_id is not None:
            key = f"{node_id}_{endpoint_id}"
            reg_entry = self.connector.mapper._registry.get(key)
            if reg_entry:
                device_name = reg_entry.get("device_name")

        if not device_name:
            return {"success": False, "error": "device_name or (node_id, endpoint_id) is required"}

        rpc_request = {
            "device": device_name,
            "data": {
                "id": 1,
                "method": method,
                "params": params
            }
        }
        res = self.connector.server_side_rpc_handler(rpc_request)
        return res

    def remove_device(self, node_id: int) -> dict:
        """
        Safely decommissions and removes a Matter node from the local fabric,
        cleans up registry and device states, and unbinds from ThingsBoard Gateway.
        """
        log.info(f"Initiating full decommissioning and removal for Matter Node #{node_id}")
        if not self.connector:
            return {"success": False, "error": "Matter Connector is not initialized or offline."}

        try:
            results = self.connector.remove_node(int(node_id))
            return {
                "success": True,
                "node_id": node_id,
                "message": f"Device #{node_id} successfully decommissioned and removed.",
                "details": results
            }
        except Exception as e:
            log.error(f"Error removing device #{node_id}: {e}")
            return {"success": False, "error": str(e)}

    def commission_device(
        self,
        code: str,
        network_only: bool = False,  # False = allow BLE/PASE commissioning
        wifi_ssid: Optional[str] = None,
        wifi_password: Optional[str] = None
    ) -> dict:
        log.info(f"Received commissioning request for code: {code[:12]}... (network_only={network_only})")

        if not self.connector or not self.connector.client:
            return {"status": "error", "error": "Matter Connector is not initialized or offline."}

        client = self.connector.client
        if not client.is_connected:
            return {
                "status": "error",
                "error": "Cannot commission: UNIQ Hub is not currently connected to matterjs-server."
            }

        # Auto-set WiFi credentials on the matter server before commissioning
        if wifi_ssid and wifi_password:
            wifi_resp = client.set_wifi_credentials(wifi_ssid, wifi_password, timeout=10.0)
            if wifi_resp.get("success"):
                log.info(f"WiFi credentials set successfully for SSID: {wifi_ssid}")
            else:
                log.warning(f"WiFi credentials setting returned: {wifi_resp} - proceeding with commission anyway")

        resp = client.commission_with_code(
            code=code,
            network_only=network_only,
            wifi_ssid=wifi_ssid,
            wifi_password=wifi_password,
            timeout=180.0
        )

        if not resp.get("success"):
            return {
                "status": "error",
                "error": resp.get("error", "Commissioning failed in matterjs-server.")
            }

        result_data = resp.get("result", {})

        # Support multiple matterjs-server response formats for node_id
        node_id = None
        if isinstance(result_data, dict):
            node_id = (
                result_data.get("node_id")
                or result_data.get("nodeId")
                or result_data.get("id")
                or result_data.get("fabricNodeId")
            )
        elif isinstance(result_data, (int, str)):
            # Some versions return node_id directly as result
            try:
                node_id = int(result_data)
            except (ValueError, TypeError):
                pass

        log.info(f"Commissioning result: node_id={node_id}, raw_result={result_data}")

        if node_id is not None and hasattr(self.connector, "sync_node_by_id"):
            try:
                self.connector.sync_node_by_id(int(node_id))
            except Exception as e:
                log.warning(f"sync_node_by_id failed: {e}")

        return {
            "status": "success",
            "node_id": node_id,
            "result": result_data,
            "message": f"Device successfully commissioned on Matter Fabric with Node ID {node_id}."
        }

    # =========================================================================
    # Rooms Management
    # =========================================================================

    def _get_storage_file(self, filename: str) -> str:
        base_dir = "/var/lib/uniq-gateway"
        if not os.path.exists(base_dir):
            base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        os.makedirs(base_dir, exist_ok=True)
        return os.path.join(base_dir, filename)

    def get_rooms_data(self) -> dict:
        filepath = self._get_storage_file("rooms.json")
        default_rooms = {
            "rooms": [
                {"id": "living_room", "name": "غرفة المعيشة", "icon": "🛋️"},
                {"id": "majlis", "name": "المجلس", "icon": "☕"},
                {"id": "master_bed", "name": "غرفة النوم الرئيسية", "icon": "🛏️"},
                {"id": "kitchen", "name": "المطبخ", "icon": "🍳"},
                {"id": "entrance", "name": "المدخل الرئيسي", "icon": "🚪"}
            ],
            "device_rooms": {}
        }
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return default_rooms

    def save_rooms_data(self, data: dict) -> bool:
        filepath = self._get_storage_file("rooms.json")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            log.error(f"Failed to save rooms data: {e}")
            return False

    # =========================================================================
    # Interactive Floorplan Management
    # =========================================================================

    def get_floorplan_data(self) -> dict:
        filepath = self._get_storage_file("floorplan.json")
        default_fp = {
            "image": "",
            "pins": {}
        }
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return default_fp

    def save_floorplan_data(self, data: dict) -> bool:
        filepath = self._get_storage_file("floorplan.json")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            log.error(f"Failed to save floorplan data: {e}")
            return False

    # =========================================================================
    # Scenarios & Automations
    # =========================================================================

    def get_scenarios_data(self) -> dict:
        filepath = self._get_storage_file("scenarios.json")
        default_scenarios = {
            "scenarios": [
                {
                    "id": "all_off",
                    "name": "إطفاء الكل (وضع الخروج)",
                    "icon": "🚪",
                    "desc": "إيقاف تشغيل جميع المفاتيح والمقابس والإنارة دفعة واحدة عند مغادرة المنزل.",
                    "actions": [{"action": "turn_all_off"}]
                },
                {
                    "id": "sleep_mode",
                    "name": "وضع النوم الهادئ",
                    "icon": "🌙",
                    "desc": "إطفاء جميع الأجهزة الرئيسية والإبقاء على أجهزة الأمان والتكييف.",
                    "actions": [{"action": "turn_all_off"}]
                },
                {
                    "id": "all_on",
                    "name": "تشغيل الكل",
                    "icon": "⚡",
                    "desc": "تشغيل كافة أجهزة المنزل في الحالات الطارئة أو الاستقبال.",
                    "actions": [{"action": "turn_all_on"}]
                }
            ]
        }
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return default_scenarios

    def save_scenarios_data(self, data: dict) -> bool:
        filepath = self._get_storage_file("scenarios.json")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            log.error(f"Failed to save scenarios data: {e}")
            return False

    def run_scenario(self, scenario_id: str) -> dict:
        log.info(f"Executing Smart Home Scenario: [{scenario_id}]")
        scenarios = self.get_scenarios_data().get("scenarios", [])
        matched = next((s for s in scenarios if s.get("id") == scenario_id), None)
        if not matched:
            return {"success": False, "error": f"Scenario '{scenario_id}' not found"}

        executed_actions = 0
        devices = self.get_live_devices()

        for act in matched.get("actions", []):
            action_type = act.get("action")
            if action_type in ["turn_all_off", "turn_all_on"]:
                target_state = (action_type == "turn_all_on")
                for d in devices:
                    if d.get("has_onoff") and d.get("node_id") is not None:
                        try:
                            self.control_device(
                                node_id=int(d["node_id"]),
                                endpoint_id=int(d.get("endpoint_id", 1)),
                                method="setState",
                                params=target_state
                            )
                            executed_actions += 1
                        except Exception as e:
                            log.warning(f"Error executing scenario on device #{d['node_id']}: {e}")
            elif action_type == "device_command":
                nid = act.get("node_id")
                epid = act.get("endpoint_id", 1)
                st = act.get("state", True)
                if nid is not None:
                    self.control_device(node_id=int(nid), endpoint_id=int(epid), method="setState", params=st)
                    executed_actions += 1

        return {
            "success": True,
            "scenario": matched.get("name"),
            "executed_actions": executed_actions,
            "message": f"تم تفعيل سيناريو '{matched.get('name')}' بنجاح."
        }

    # =========================================================================
    # Cloud Config & Connectivity Management
    # =========================================================================

    def get_cloud_config(self) -> dict:
        config_file = "/opt/uniq-gateway/config/gateway.yaml"
        if not os.path.exists(config_file):
            config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "gateway.yaml")

        cloud_info = {
            "host": "18.134.221.206",
            "port": 1883,
            "access_token": "",
            "cloud_connected": False,
            "mqtt_topic_status": "v1/gateway/telemetry",
            "server_type": "ThingsBoard Professional / Community"
        }

        # Check connector live cloud connectivity
        if self.connector:
            gw = getattr(self.connector, "_gateway", None)
            if gw:
                client = getattr(gw, "tb_client", None) or getattr(gw, "mqtt_client", None)
                if client and hasattr(client, "is_connected"):
                    cloud_info["cloud_connected"] = bool(client.is_connected())

        # Read config file values if exists
        if os.path.exists(config_file):
            try:
                import yaml
                with open(config_file, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                    c_cfg = cfg.get("cloud", {})
                    cloud_info["host"] = c_cfg.get("host", cloud_info["host"])
                    cloud_info["port"] = c_cfg.get("port", cloud_info["port"])
                    tok = c_cfg.get("access_token", "")
                    cloud_info["access_token"] = tok
            except Exception:
                pass

        return cloud_info

    def save_cloud_config(self, req_data: dict) -> dict:
        config_file = "/opt/uniq-gateway/config/gateway.yaml"
        if not os.path.exists(config_file):
            config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "gateway.yaml")

        new_host = req_data.get("host", "").strip()
        new_port = int(req_data.get("port", 1883))
        new_token = req_data.get("access_token", "").strip()

        if not os.path.exists(config_file):
            return {"success": False, "error": f"Config file not found at {config_file}"}

        try:
            import yaml
            with open(config_file, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}

            if "cloud" not in cfg:
                cfg["cloud"] = {}
            if new_host:
                cfg["cloud"]["host"] = new_host
            if new_port:
                cfg["cloud"]["port"] = new_port
            if new_token:
                cfg["cloud"]["access_token"] = new_token

            with open(config_file, "w", encoding="utf-8") as f:
                yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)

            return {
                "success": True,
                "message": "تم حفظ إعدادات السحابة بنجاح. سيتم تطبيق الاتصال فور إعادة تشغيل البوابة.",
                "reboot_required": True
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def sync_all_to_cloud(self) -> dict:
        """
        Manually announces all registered sub-devices and their latest attributes/telemetry to ThingsBoard Gateway.
        """
        synced_count = 0
        if not self.connector:
            return {"success": False, "error": "Matter connector is not initialized"}

        mapper = getattr(self.connector, "mapper", None)
        if not mapper:
            return {"success": False, "error": "Device mapper not available"}

        try:
            for key, dev in list(mapper._registry.items()):
                device_name = dev.get("device_name")
                device_type = dev.get("device_type", "Matter Device")
                if not device_name:
                    continue

                # 1. Connect
                self.connector.send_to_gateway("connect", {
                    "device": device_name,
                    "type": device_type
                })

                # 2. Attributes
                attrs = dev.get("attributes", {})
                self.connector.send_to_gateway("attributes", {
                    "device": device_name,
                    "data": attrs
                })

                # 3. Telemetry (current state)
                state = dev.get("state", {})
                if state:
                    self.connector.send_to_gateway("telemetry", {
                        "device": device_name,
                        "data": state
                    })

                synced_count += 1

            return {
                "success": True,
                "synced_count": synced_count,
                "message": f"تمت مزامنة {synced_count} جهاز بنجاح مع بوابة السحابة (ThingsBoard)."
            }
        except Exception as e:
            log.error(f"Error during manual cloud sync: {e}")
            return {"success": False, "error": str(e)}

