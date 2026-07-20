"""Compatibility import for the existing ``ppadb.device.Device`` API."""

from adb_backend import AdbDevice as Device

__all__ = ["Device"]
