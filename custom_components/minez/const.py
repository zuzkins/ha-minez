"""Constants for the MineZ integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "minez"

CONF_TLS = "tls"

DEFAULT_NAME = "MineZ Miner"
DEFAULT_PORT = 50051
DEFAULT_SCAN_INTERVAL = 5
DEFAULT_TIMEOUT = 15

UPDATE_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

MANUFACTURER = "Braiins"

ATTR_COORDINATOR = "coordinator"
ATTR_CLIENT = "client"
