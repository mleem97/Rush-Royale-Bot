"""RushBot's local ppadb compatibility package backed by the official adb CLI."""

from .client import Client
from .device import Device

__all__ = ["Client", "Device"]
