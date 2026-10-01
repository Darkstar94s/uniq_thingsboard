# -*- coding: utf-8 -*-
# Copyright 2026 UNIQ Smart Home
# UNIQ Matter Extension Suite for ThingsBoard Gateway

try:
    from .uniq_matter_connector import UniqMatterConnector
except Exception:
    UniqMatterConnector = None

from .matter_client import MatterClient
from .device_mapper import MatterDeviceMapper
from .commission_service import MatterCommissionService

__all__ = [
    "UniqMatterConnector",
    "MatterClient",
    "MatterDeviceMapper",
    "MatterCommissionService"
]
