# -*- coding: utf-8 -*-
# Copyright 2026 UNIQ Smart Home
# Robust WebSocket Client for matterjs-server / Matter Controller

import json
import logging
import threading
import time
from typing import Dict, Any, Callable, Optional

log = logging.getLogger("UniqMatterClient")

# Try to import websocket-client or install via ThingsBoard utility if running in gateway
try:
    import websocket
except ImportError:
    try:
        from thingsboard_gateway.tb_utility.tb_utility import TBUtility
        log.info("websocket-client not found. Installing via TBUtility...")
        TBUtility.install_package("websocket-client")
        import websocket
    except Exception as e:
        log.warning(f"Could not load websocket library ({e}). MatterClient will operate in stub/mock mode.")
        websocket = None


class MatterClient:
    """
    WebSocket client interface connecting UNIQ Gateway to matterjs-server.
    Adheres to the official Matter Controller WebSocket RPC protocol.
    """

    def __init__(
        self,
        server_url: str = "ws://127.0.0.1:5580/ws",
        on_node_event: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        on_attribute_event: Optional[Callable[[int, int, int, int, Any], None]] = None,
        on_connection_change: Optional[Callable[[bool], None]] = None,
        reconnect_interval_sec: int = 5
    ):
        self.server_url = server_url
        self.on_node_event = on_node_event
        self.on_attribute_event = on_attribute_event
        self.on_connection_change = on_connection_change
        self.reconnect_interval = reconnect_interval_sec

        self._ws: Optional[Any] = None
        self._is_running = False
        self._is_connected = False
        self._worker_thread: Optional[threading.Thread] = None

        self._message_counter = 0
        self._counter_lock = threading.Lock()
        self._pending_commands: Dict[str, Dict[str, Any]] = {}

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    def start(self):
        if self._is_running:
            return
        self._is_running = True
        self._worker_thread = threading.Thread(target=self._connection_loop, daemon=True, name="MatterClientWorker")
        self._worker_thread.start()
        log.info(f"MatterClient started (target: {self.server_url})")

    def stop(self):
        self._is_running = False
        self._is_connected = False
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
        log.info("MatterClient stopped.")

    def _get_next_message_id(self) -> str:
        with self._counter_lock:
            self._message_counter += 1
            return str(self._message_counter)

    def _connection_loop(self):
        while self._is_running:
            if websocket is None:
                log.warning("WebSocket library unavailable. Retrying in 10s...")
                time.sleep(10)
                continue

            try:
                log.info(f"Connecting to matterjs-server at {self.server_url}...")
                self._ws = websocket.WebSocketApp(
                    self.server_url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close
                )
                self._ws.run_forever(ping_interval=30, ping_timeout=10)
            except Exception as e:
                log.error(f"WebSocket connection error: {e}")

            self._set_connected(False)
            if self._is_running:
                log.info(f"Reconnecting to matterjs-server in {self.reconnect_interval}s...")
                time.sleep(self.reconnect_interval)

    def _set_connected(self, state: bool):
        if self._is_connected != state:
            self._is_connected = state
            log.info(f"MatterClient connection state changed: is_connected = {state}")
            if self.on_connection_change:
                try:
                    self.on_connection_change(state)
                except Exception as e:
                    log.error(f"Error in on_connection_change callback: {e}")

    def _on_open(self, ws):
        log.info("Successfully connected to matterjs-server WebSocket!")
        self._set_connected(True)
        # Immediately subscribe to real-time events stream
        self._subscribe_to_events()

    def _subscribe_to_events(self):
        try:
            log.info("Sending 'start_listening' to stream Matter events...")
            msg_id = self._get_next_message_id()
            payload = json.dumps({"message_id": msg_id, "command": "start_listening"})
            self._ws.send(payload)
        except Exception as e:
            log.error(f"Failed to send start_listening: {e}")

    def _on_message(self, ws, message):
        try:
            msg = json.loads(message)
        except Exception as e:
            log.error(f"Failed to parse incoming WebSocket message: {e} | Raw: {message[:100]}")
            return

        # matterjs-server may send a list of events (batch) - process each item
        if isinstance(msg, list):
            for item in msg:
                if isinstance(item, dict):
                    self._process_single_message(item)
            return

        if isinstance(msg, dict):
            self._process_single_message(msg)

    def _process_single_message(self, msg: dict):
        """Process a single message dict from matterjs-server."""
        # 1. Command Response resolution
        msg_id = str(msg.get("message_id", ""))
        if msg_id and msg_id in self._pending_commands:
            entry = self._pending_commands[msg_id]
            entry["response"] = msg
            entry["event"].set()
            return

        # 2. Real-time Matter Server Events
        event_type = msg.get("event")
        data = msg.get("data")

        if not event_type:
            return

        if event_type in ["node_added", "node_updated", "node_removed"]:
            if isinstance(data, dict):
                if self.on_node_event:
                    try:
                        self.on_node_event(event_type, data)
                    except Exception as e:
                        log.error(f"Error handling node event '{event_type}': {e}")

                # If node_updated contains a flat attributes dict, process each attribute
                node_id = data.get("node_id") or data.get("nodeId")
                flat_attrs = data.get("attributes", {})
                if node_id is not None and isinstance(flat_attrs, dict) and self.on_attribute_event:
                    for attr_path, value in flat_attrs.items():
                        parts = str(attr_path).split("/")
                        if len(parts) == 3:
                            try:
                                ep = int(parts[0])
                                cl = int(parts[1])
                                at = int(parts[2])
                                self.on_attribute_event(int(node_id), ep, cl, at, value)
                            except (ValueError, TypeError):
                                pass

        elif event_type in ["attribute_updated", "node_attribute_updated", "attributeUpdate", "attribute_update"]:
            node_id = None
            endpoint_id = 0
            cluster_id = None
            attribute_id = None
            value = None

            # Format 1: Array format [node_id, "endpoint/cluster/attribute", value] (Standard python-matter-server)
            if isinstance(data, (list, tuple)):
                if len(data) >= 3:
                    node_id = data[0]
                    path_str = str(data[1])
                    value = data[2]
                    parts = path_str.split("/")
                    if len(parts) == 3:
                        try:
                            endpoint_id = int(parts[0])
                            cluster_id = int(parts[1])
                            attribute_id = int(parts[2])
                        except (ValueError, TypeError):
                            pass
                    elif len(data) >= 5:
                        # [node_id, endpoint_id, cluster_id, attribute_id, value]
                        try:
                            endpoint_id = int(data[1])
                            cluster_id = int(data[2])
                            attribute_id = int(data[3])
                            value = data[4]
                        except (ValueError, TypeError):
                            pass

            # Format 2: Dict format
            elif isinstance(data, dict):
                value = data.get("value")
                node_id = data.get("node_id") or data.get("nodeId")

                # Path string "1/6/0" or "node/1/6/0"
                path = data.get("path") or data.get("attribute_path") or data.get("attributePath")
                if isinstance(path, str) and "/" in path:
                    parts = path.split("/")
                    if len(parts) == 3:
                        try:
                            endpoint_id = int(parts[0])
                            cluster_id = int(parts[1])
                            attribute_id = int(parts[2])
                        except (ValueError, TypeError):
                            pass
                    elif len(parts) == 4:
                        try:
                            node_id = int(parts[0])
                            endpoint_id = int(parts[1])
                            cluster_id = int(parts[2])
                            attribute_id = int(parts[3])
                        except (ValueError, TypeError):
                            pass
                elif isinstance(path, dict):
                    node_id = path.get("nodeId") or path.get("node_id") or node_id
                    endpoint_id = path.get("endpointId") or path.get("endpoint_id") or 0
                    cluster_id = path.get("clusterId") or path.get("cluster_id")
                    attribute_id = path.get("attributeId") or path.get("attribute_id")
                else:
                    endpoint_id = data.get("endpoint_id") or data.get("endpointId") or 0
                    cluster_id = data.get("cluster_id") or data.get("clusterId")
                    attribute_id = data.get("attribute_id") or data.get("attributeId")

            if self.on_attribute_event and node_id is not None and cluster_id is not None:
                try:
                    self.on_attribute_event(
                        int(node_id), int(endpoint_id),
                        int(cluster_id), int(attribute_id) if attribute_id is not None else 0,
                        value
                    )
                except Exception as e:
                    log.error(f"Error handling attribute event: {e}")

    def _on_error(self, ws, error):
        log.error(f"WebSocket error encountered: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        log.info(f"WebSocket closed: code={close_status_code}, msg={close_msg}")
        self._set_connected(False)

    def send_command(self, command: str, args: Optional[Dict[str, Any]] = None, timeout: float = 15.0) -> Dict[str, Any]:
        """
        Sends an RPC command to matterjs-server and synchronously waits for response.
        """
        if not self._is_connected or not self._ws:
            return {"success": False, "error": "MatterClient is not connected to matterjs-server"}

        msg_id = self._get_next_message_id()
        payload = {"message_id": msg_id, "command": command}
        if args is not None:
            payload["args"] = args

        event = threading.Event()
        entry = {"event": event, "response": None}
        self._pending_commands[msg_id] = entry

        try:
            self._ws.send(json.dumps(payload))
            signaled = event.wait(timeout=timeout)
            if not signaled:
                return {"success": False, "error": f"Command '{command}' timed out after {timeout}s"}
            
            resp = entry.get("response", {})
            if "error" in resp:
                return {"success": False, "error": resp.get("error")}
            return {"success": True, "result": resp.get("result", resp)}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            self._pending_commands.pop(msg_id, None)

    def get_nodes(self, timeout: float = 10.0) -> Dict[str, Any]:
        """Retrieves all currently commissioned Matter nodes."""
        return self.send_command("get_nodes", timeout=timeout)

    def get_node(self, node_id: int, timeout: float = 10.0) -> Dict[str, Any]:
        """Retrieves details of a specific node."""
        return self.send_command("get_node", args={"node_id": node_id}, timeout=timeout)

    def device_command(
        self,
        node_id: int,
        endpoint_id: int,
        cluster_id: int,
        command_name: str,
        command_args: Optional[Dict[str, Any]] = None,
        timeout: float = 15.0
    ) -> Dict[str, Any]:
        """
        Executes a cluster command on a specific Matter node endpoint.
        Example: device_command(node_id=2, endpoint_id=1, cluster_id=6, command_name="Off")
        """
        args = {
            "node_id": node_id,
            "endpoint_id": endpoint_id,
            "cluster_id": cluster_id,
            "command_name": command_name,
            "args": command_args or {}
        }
        return self.send_command("device_command", args=args, timeout=timeout)

    def commission_with_code(
        self,
        code: str,
        network_only: bool = False,  # False = allow BLE/PASE commissioning
        wifi_ssid: Optional[str] = None,
        wifi_password: Optional[str] = None,
        timeout: float = 180.0  # BLE commissioning can take 1-3 minutes
    ) -> Dict[str, Any]:
        """
        Commissions a Matter device using setup code (QR code or numeric manual code).
        - network_only=False: Uses BLE (PASE) for initial pairing, then hands off to Wi-Fi/Thread
        - network_only=True: Only commissions devices already on the same IP network
        """
        args: Dict[str, Any] = {
            "code": code,
            "network_only": network_only
        }
        if wifi_ssid:
            args["wifi_ssid"] = wifi_ssid
        if wifi_password:
            args["wifi_password"] = wifi_password

        log.info(f"Commissioning with code (network_only={network_only}, ble_enabled={not network_only})")
        return self.send_command("commission_with_code", args=args, timeout=timeout)

    def set_wifi_credentials(
        self,
        ssid: str,
        password: str,
        timeout: float = 10.0
    ) -> Dict[str, Any]:
        """
        Sets WiFi credentials on the Matter controller.
        Must be called before commissioning a WiFi device for the first time.
        """
        args = {
            "ssid": ssid,
            "credentials": password
        }
        log.info(f"Setting WiFi credentials for SSID: {ssid}")
        return self.send_command("set_wifi_credentials", args=args, timeout=timeout)
