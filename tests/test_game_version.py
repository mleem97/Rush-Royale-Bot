from __future__ import annotations

from textwrap import dedent

import pytest

from rushbot.game_version import (
    GameBuildInfo,
    GameCompatibilityStatus,
    GamePackageNotFound,
    LiveActionsBlocked,
    RuntimeMode,
    SupportMatrix,
    SupportMatrixError,
    inspect_game_build,
    parse_dumpsys_package,
)


DUMPSYS_37 = dedent(
    """
    Packages:
      Package [com.my.defense] (1a2b3c):
        userId=10342
        versionCode=3700123 minSdk=24 targetSdk=35
        versionName=37.0.1
        installerPackageName=com.android.vending
        firstInstallTime=2026-08-01 10:11:12
        lastUpdateTime=2026-08-14 08:02:03
    """
)


def test_parse_dumpsys_package_extracts_exact_build() -> None:
    build = parse_dumpsys_package(DUMPSYS_37)

    assert build.package_name == "com.my.defense"
    assert build.version_name == "37.0.1"
    assert build.version_code == 3_700_123
    assert build.min_sdk == 24
    assert build.target_sdk == 35
    assert build.installer_package_name == "com.android.vending"
    assert build.first_install_time == "2026-08-01 10:11:12"
    assert build.last_update_time == "2026-08-14 08:02:03"
    assert build.build_id == "com.my.defense@37.0.1+3700123"


def test_parse_dumpsys_package_rejects_missing_package() -> None:
    with pytest.raises(GamePackageNotFound):
        parse_dumpsys_package("Unable to find package: com.my.defense")


def test_inspector_routes_to_exact_adb_serial() -> None:
    calls: list[tuple[str, list[str | int | float]]] = []

    class Backend:
        def shell(self, serial: str, arguments: list[str | int | float]) -> str:
            calls.append((serial, arguments))
            return DUMPSYS_37

    build = inspect_game_build(Backend(), "192.168.1.20:5555")

    assert build.version_code == 3_700_123
    assert calls == [
        ("192.168.1.20:5555", ["dumpsys", "package", "com.my.defense"])
    ]


def test_default_policy_blocks_unknown_and_future_builds() -> None:
    matrix = SupportMatrix.from_toml(
        dedent(
            """
            schema_version = 1
            default_status = "capture_only"
            default_reason = "Unreviewed build."

            [[builds]]
            id = "known-37"
            package = "com.my.defense"
            version_code = 3700123
            version_name = "37.0.1"
            status = "live_validated"
            reason = "Exact build passed live validation."
            """
        )
    )
    future = GameBuildInfo("com.my.defense", "38.0.0", 3_800_001)

    decision = matrix.evaluate(future)

    assert decision.status is GameCompatibilityStatus.CAPTURE_ONLY
    assert decision.maximum_runtime_mode is RuntimeMode.CAPTURE_ONLY
    assert decision.authorize(RuntimeMode.LIVE).effective_mode is RuntimeMode.CAPTURE_ONLY
    assert decision.authorize(RuntimeMode.LIVE).downgraded is True
    with pytest.raises(LiveActionsBlocked):
        decision.require_live_actions()


def test_broad_rule_can_never_be_marked_live_validated() -> None:
    with pytest.raises(SupportMatrixError, match="exact version_code"):
        SupportMatrix.from_toml(
            dedent(
                """
                schema_version = 1
                default_status = "capture_only"
                default_reason = "Default."

                [[builds]]
                id = "unsafe-prefix"
                package = "com.my.defense"
                version_name_prefix = "37."
                status = "live_validated"
                reason = "Too broad."
                """
            )
        )


def test_exact_live_validated_build_passes_gate() -> None:
    matrix = SupportMatrix.from_toml(
        dedent(
            """
            schema_version = 1
            default_status = "capture_only"
            default_reason = "Default."

            [[builds]]
            id = "validated-37-0-1"
            package = "com.my.defense"
            version_code = 3700123
            version_name = "37.0.1"
            status = "live_validated"
            reason = "Validated using the release replay and live suite."
            """
        )
    )

    decision = matrix.evaluate(GameBuildInfo("com.my.defense", "37.0.1", 3_700_123))

    assert decision.live_actions_allowed is True
    assert decision.authorize("live").effective_mode is RuntimeMode.LIVE
    decision.require_live_actions()


def test_exact_rule_overrides_capture_only_prefix() -> None:
    matrix = SupportMatrix.from_toml(
        dedent(
            """
            schema_version = 1
            default_status = "capture_only"
            default_reason = "Default."

            [[builds]]
            id = "37-prefix"
            package = "com.my.defense"
            version_name_prefix = "37."
            status = "capture_only"
            reason = "Capture baseline."

            [[builds]]
            id = "validated-exact"
            package = "com.my.defense"
            version_code = 3700123
            version_name = "37.0.1"
            status = "live_validated"
            reason = "Validated exact build."
            """
        )
    )

    decision = matrix.evaluate(GameBuildInfo("com.my.defense", "37.0.1", 3_700_123))

    assert decision.rule_id == "validated-exact"
    assert decision.status is GameCompatibilityStatus.LIVE_VALIDATED


def test_same_specificity_conflict_is_rejected_at_evaluation() -> None:
    matrix = SupportMatrix.from_toml(
        dedent(
            """
            schema_version = 1
            default_status = "capture_only"
            default_reason = "Default."

            [[builds]]
            id = "first"
            package = "com.my.defense"
            version_code = 3700123
            status = "replay_validated"
            reason = "First."

            [[builds]]
            id = "second"
            package = "com.my.defense"
            version_code = 3700123
            status = "shadow_validated"
            reason = "Second."
            """
        )
    )

    with pytest.raises(SupportMatrixError, match="Ambiguous"):
        matrix.evaluate(GameBuildInfo("com.my.defense", "37.0.1", 3_700_123))


def test_statuses_expose_monotonic_maximum_modes() -> None:
    assert GameCompatibilityStatus.UNSUPPORTED.maximum_runtime_mode is RuntimeMode.CAPTURE_ONLY
    assert GameCompatibilityStatus.CAPTURE_ONLY.maximum_runtime_mode is RuntimeMode.CAPTURE_ONLY
    assert GameCompatibilityStatus.DEPRECATED.maximum_runtime_mode is RuntimeMode.CAPTURE_ONLY
    assert GameCompatibilityStatus.REPLAY_VALIDATED.maximum_runtime_mode is RuntimeMode.REPLAY
    assert GameCompatibilityStatus.SHADOW_VALIDATED.maximum_runtime_mode is RuntimeMode.SHADOW
    assert GameCompatibilityStatus.LIVE_VALIDATED.maximum_runtime_mode is RuntimeMode.LIVE


def test_build_validation_and_serial_validation() -> None:
    with pytest.raises(ValueError, match="package"):
        GameBuildInfo("not-a-package", "37.0", 1)
    with pytest.raises(ValueError, match="versionCode"):
        GameBuildInfo("com.my.defense", "37.0", -1)

    class Backend:
        def shell(self, serial: str, arguments: list[str | int | float]) -> str:
            raise AssertionError("must not run")

    with pytest.raises(ValueError, match="serial"):
        inspect_game_build(Backend(), "  ")


def test_parser_accepts_version_name_when_code_is_absent() -> None:
    build = parse_dumpsys_package("versionName=37.0-custom\n")
    assert build.version_name == "37.0-custom"
    assert build.version_code is None


def test_parser_rejects_output_without_version_metadata() -> None:
    with pytest.raises(GamePackageNotFound, match="no version metadata"):
        parse_dumpsys_package("Package [com.my.defense]\nuserId=10001")


@pytest.mark.parametrize(
    ("rule", "message"),
    [
        (
            'id = ""\npackage = "com.my.defense"\nversion_code = 1\n'
            'status = "capture_only"\nreason = "x"',
            "id",
        ),
        (
            'id = "x"\npackage = "com.my.defense"\nversion_code = 1\n'
            'status = "capture_only"\nreason = ""',
            "reason",
        ),
        (
            'id = "x"\npackage = "com.my.defense"\n'
            'status = "capture_only"\nreason = "x"',
            "constrain",
        ),
        (
            'id = "x"\npackage = "com.my.defense"\nversion_code = -1\n'
            'status = "capture_only"\nreason = "x"',
            "negative",
        ),
        (
            'id = "x"\npackage = "com.my.defense"\nversion_code_min = 5\n'
            'version_code_max = 4\nstatus = "capture_only"\nreason = "x"',
            "must not exceed",
        ),
        (
            'id = "x"\npackage = "com.my.defense"\nversion_code = 4\n'
            'version_code_min = 5\nstatus = "capture_only"\nreason = "x"',
            "below",
        ),
        (
            'id = "x"\npackage = "com.my.defense"\nversion_code = 6\n'
            'version_code_max = 5\nstatus = "capture_only"\nreason = "x"',
            "exceed",
        ),
        (
            'id = "x"\npackage = "com.my.defense"\nversion_name = "38.0"\n'
            'version_name_prefix = "37."\nstatus = "capture_only"\nreason = "x"',
            "prefix",
        ),
    ],
)
def test_rule_invariants_are_fail_closed(rule: str, message: str) -> None:
    with pytest.raises(SupportMatrixError, match=message):
        SupportMatrix.from_toml(
            "schema_version = 1\n"
            'default_status = "capture_only"\n'
            'default_reason = "default"\n\n'
            "[[builds]]\n"
            f"{rule}\n"
        )


@pytest.mark.parametrize(
    "document",
    [
        "not = [valid",
        'schema_version = 1\ndefault_status = "capture_only"',
        (
            'schema_version = 1\ndefault_status = "made_up"\n'
            'default_reason = "default"\n'
        ),
        (
            'schema_version = 1\ndefault_status = "live_validated"\n'
            'default_reason = "unsafe"\n'
        ),
        (
            'schema_version = 2\ndefault_status = "capture_only"\n'
            'default_reason = "default"\n'
        ),
        (
            'schema_version = 1\ndefault_status = "capture_only"\n'
            'default_reason = "default"\nbuilds = 1\n'
        ),
        (
            'schema_version = 1\ndefault_status = "capture_only"\n'
            'default_reason = "default"\nbuilds = [1]\n'
        ),
    ],
)
def test_invalid_matrix_documents_are_rejected(document: str) -> None:
    with pytest.raises(SupportMatrixError):
        SupportMatrix.from_toml(document)


def test_duplicate_rule_ids_are_rejected() -> None:
    with pytest.raises(SupportMatrixError, match="unique"):
        SupportMatrix.from_toml(
            dedent(
                """
                schema_version = 1
                default_status = "capture_only"
                default_reason = "default"

                [[builds]]
                id = "same"
                package = "com.my.defense"
                version_code = 1
                status = "capture_only"
                reason = "one"

                [[builds]]
                id = "same"
                package = "com.my.defense"
                version_code = 2
                status = "capture_only"
                reason = "two"
                """
            )
        )


def test_range_rule_and_mode_authorization() -> None:
    matrix = SupportMatrix.from_toml(
        dedent(
            """
            schema_version = 1
            default_status = "unsupported"
            default_reason = "outside range"

            [[builds]]
            id = "legacy-range"
            package = "com.my.defense"
            version_code_min = 100
            version_code_max = 200
            status = "deprecated"
            reason = "legacy capture only"
            """
        )
    )
    decision = matrix.evaluate(GameBuildInfo("com.my.defense", "old", 150))
    assert decision.rule_id == "legacy-range"
    assert decision.as_dict()["maximum_runtime_mode"] == "capture_only"
    assert decision.authorize(RuntimeMode.CAPTURE_ONLY).downgraded is False
    assert decision.authorize(RuntimeMode.REPLAY).effective_mode is RuntimeMode.CAPTURE_ONLY


def test_matrix_loads_custom_path_and_packaged_default(tmp_path) -> None:
    custom = tmp_path / "matrix.toml"
    custom.write_text(
        'schema_version = 1\ndefault_status = "capture_only"\n'
        'default_reason = "custom"\n',
        encoding="utf-8",
    )
    assert SupportMatrix.load(custom).default_reason == "custom"
    assert SupportMatrix.load().schema_version == 1


def test_boolean_version_code_is_rejected() -> None:
    with pytest.raises(SupportMatrixError, match="boolean"):
        SupportMatrix.from_toml(
            dedent(
                """
                schema_version = 1
                default_status = "capture_only"
                default_reason = "default"

                [[builds]]
                id = "bad"
                package = "com.my.defense"
                version_code = true
                status = "capture_only"
                reason = "bad"
                """
            )
        )
