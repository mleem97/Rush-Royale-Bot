"""Compatibility import for the existing ``ppadb.client.Client`` API."""

from adb_backend import AdbClient as Client

__all__ = ["Client"]
