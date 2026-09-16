#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UNIQ Smart Home - Base Connector Interface
Abstract base class for all UNIQ Hub radio/protocol connectors.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Callable

class BaseConnector(ABC):
    def __init__(self, name: str, config: Dict[str, Any], gateway_callback: Callable):
        self.name = name
        self.config = config
        self.gateway_callback = gateway_callback
        self.is_running = False

    @abstractmethod
    def start(self):
        """Starts connector listening loop and connects to hardware/service."""
        pass

    @abstractmethod
    def stop(self):
        """Stops connector and releases resources."""
        pass

    @abstractmethod
    def handle_rpc(self, device_name: str, method: str, params: Any) -> Any:
        """Handles remote procedure call from UNIQ Cloud to control a sub-device."""
        pass

    def send_to_gateway(self, message_type: str, data: Dict[str, Any]):
        """
        Sends formatted data to the main UNIQ Gateway.
        message_type can be:
          - 'connect': sub-device connected
          - 'disconnect': sub-device disconnected
          - 'telemetry': sub-device telemetry update
          - 'attributes': sub-device attributes update
        """
        if self.gateway_callback:
            self.gateway_callback(self.name, message_type, data)
