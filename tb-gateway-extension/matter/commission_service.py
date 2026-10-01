# -*- coding: utf-8 -*-
# Copyright 2026 UNIQ Smart Home
# Local HTTP Commissioning Microservice & Web Dashboard Server for UNIQ Hub

import json
import logging
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Optional

from .hub_auth import HubAuthManager

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

        # 3. Change Device Category API
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

        # 4. Delete / Decommission Device API
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

        # 5. Change PIN API
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

        from .device_mapper import resolve_device_type_and_category

        devices = []
        registry = self.connector.mapper._registry
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
                device_type_ids=[]
            )

            category = dev.get("category")
            if not category or category == "other" or resolved_cat != "other":
                category = resolved_cat
                if resolved_type != "Smart Device":
                    dev_type = resolved_type

            # Check if device has OnOff capability
            has_onoff = any(kw in dev_type for kw in ["Light", "Relay", "Socket", "Plug", "Switch", "Generic Switch"]) or category in ["lighting", "socket", "switch"]

            # Get live state from mapper cache
            state_data = self.connector.mapper.get_device_state(node_id, endpoint_id)
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

    def remove_device(self, node_id: int) -> Dict[str, Any]:
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
