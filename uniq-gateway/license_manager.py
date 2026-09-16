#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UNIQ Smart Home - Protocol License & Feature Gating Manager
Controls which protocols (Zigbee, Matter, BLE, Modbus) are authorized to run on the Hub.
"""

import logging
import json
from typing import List, Dict, Callable

log = logging.getLogger("UniqLicenseManager")

class HubTier:
    LITE = "LITE"         # Wi-Fi + Matter
    PRO = "PRO"           # Wi-Fi + Matter + Zigbee
    ENTERPRISE = "ULTRA"  # Wi-Fi + Matter + Zigbee + BLE + Custom

DEFAULT_TIER_PROTOCOLS = {
    HubTier.LITE: ["wifi", "matter"],
    HubTier.PRO: ["wifi", "matter", "zigbee"],
    HubTier.ENTERPRISE: ["wifi", "matter", "zigbee", "ble"]
}

class LicenseManager:
    def __init__(self, hub_serial: str, initial_tier: str = HubTier.PRO):
        self.hub_serial = hub_serial
        self.tier = initial_tier.upper()
        self.licensed_protocols = set(DEFAULT_TIER_PROTOCOLS.get(self.tier, ["wifi", "matter"]))
        self.max_devices = 64 if self.tier == HubTier.LITE else 256
        self.license_key = ""
        self._on_license_changed_callbacks: List[Callable] = []

    def is_protocol_licensed(self, protocol_name: str) -> bool:
        """Checks whether a specific protocol (e.g., 'zigbee' or 'matter') is currently licensed."""
        protocol = protocol_name.lower().strip()
        licensed = protocol in self.licensed_protocols
        if not licensed:
            log.warning(f"Protocol [{protocol.upper()}] is NOT licensed for Hub [{self.hub_serial}] (Tier: {self.tier})")
        return licensed

    def get_licensed_protocols(self) -> List[str]:
        """Returns list of currently active licensed protocols."""
        return sorted(list(self.licensed_protocols))

    def update_license_from_cloud(self, attributes: Dict):
        """
        Called when UNIQ Cloud updates shared attributes on the Hub.
        Allows remote upgrading or unlocking of protocols on demand.
        """
        changed = False

        if "tier" in attributes:
            new_tier = str(attributes["tier"]).upper()
            if new_tier != self.tier and new_tier in DEFAULT_TIER_PROTOCOLS:
                log.info(f"Hub tier upgraded from {self.tier} to {new_tier}")
                self.tier = new_tier
                self.licensed_protocols = set(DEFAULT_TIER_PROTOCOLS[self.tier])
                changed = True

        if "licensedProtocols" in attributes:
            custom_protocols = attributes["licensedProtocols"]
            if isinstance(custom_protocols, list):
                new_set = {p.lower().strip() for p in custom_protocols}
                if new_set != self.licensed_protocols:
                    log.info(f"Licensed protocols updated remotely: {new_set}")
                    self.licensed_protocols = new_set
                    changed = True

        if "maxDevices" in attributes:
            self.max_devices = int(attributes["maxDevices"])

        if "licenseKey" in attributes:
            self.license_key = str(attributes["licenseKey"])

        if changed:
            log.info(f"Active licensed protocols for Hub: {self.get_licensed_protocols()}")
            for callback in self._on_license_changed_callbacks:
                try:
                    callback(self.get_licensed_protocols())
                except Exception as e:
                    log.error(f"Error executing license change callback: {e}")

    def on_license_changed(self, callback: Callable):
        """Register listener for license updates."""
        self._on_license_changed_callbacks.append(callback)
