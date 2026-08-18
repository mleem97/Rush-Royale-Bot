from __future__ import annotations

from rushbot.cli import build_parser


def test_pair_command_parses_without_plaintext_code() -> None:
    args = build_parser().parse_args(["pair", "192.168.1.8:37123"])
    assert args.command == "pair"
    assert args.code is None


def test_mirror_command_parses_device_and_v4l2() -> None:
    args = build_parser().parse_args(
        ["mirror", "emulator-5554", "--view-only", "--v4l2-sink", "/dev/video10"]
    )
    assert args.command == "mirror"
    assert args.serial == "emulator-5554"
    assert args.view_only is True
