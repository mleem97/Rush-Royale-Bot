"""Rush Royale build discovery and fail-closed compatibility policy.

The modernization runtime must never infer live-game compatibility from a package name
or a broad marketing version alone.  This module reads the exact installed Android build,
matches it against a reviewed support matrix, and reduces every unknown or insufficiently
validated build to capture-only operation.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from importlib.resources import files
from pathlib import Path
from typing import Any, Protocol, Self

DEFAULT_GAME_PACKAGE = "com.my.defense"
DEFAULT_SUPPORT_MATRIX_RESOURCE = "data/support-matrix.toml"


class GameVersionError(RuntimeError):
    """Base error for game-build inspection and compatibility decisions."""


class GamePackageNotFound(GameVersionError):
    """Raised when the configured Android package is not installed or not readable."""


class SupportMatrixError(GameVersionError):
    """Raised for malformed or ambiguous compatibility policy."""


class LiveActionsBlocked(PermissionError):
    """Raised when code tries to execute live input for an unvalidated build."""


class GameCompatibilityStatus(StrEnum):
    """Validation stage assigned to one exact or broadly matched game build."""

    UNSUPPORTED = "unsupported"
    CAPTURE_ONLY = "capture_only"
    REPLAY_VALIDATED = "replay_validated"
    SHADOW_VALIDATED = "shadow_validated"
    LIVE_VALIDATED = "live_validated"
    DEPRECATED = "deprecated"

    @property
    def maximum_runtime_mode(self) -> RuntimeMode:
        if self is GameCompatibilityStatus.LIVE_VALIDATED:
            return RuntimeMode.LIVE
        if self is GameCompatibilityStatus.SHADOW_VALIDATED:
            return RuntimeMode.SHADOW
        if self is GameCompatibilityStatus.REPLAY_VALIDATED:
            return RuntimeMode.REPLAY
        return RuntimeMode.CAPTURE_ONLY

    @property
    def live_actions_allowed(self) -> bool:
        return self is GameCompatibilityStatus.LIVE_VALIDATED


class RuntimeMode(StrEnum):
    """Requested or effective game-runtime mode, ordered by interaction risk."""

    CAPTURE_ONLY = "capture_only"
    REPLAY = "replay"
    SHADOW = "shadow"
    LIVE = "live"


_RUNTIME_MODE_RISK: Mapping[RuntimeMode, int] = {
    RuntimeMode.CAPTURE_ONLY: 0,
    RuntimeMode.REPLAY: 1,
    RuntimeMode.SHADOW: 2,
    RuntimeMode.LIVE: 3,
}


@dataclass(frozen=True, slots=True)
class GameBuildInfo:
    """Version information extracted from ``dumpsys package`` for one installed APK."""

    package_name: str
    version_name: str | None
    version_code: int | None
    min_sdk: int | None = None
    target_sdk: int | None = None
    first_install_time: str | None = None
    last_update_time: str | None = None
    installer_package_name: str | None = None

    def __post_init__(self) -> None:
        _validate_package_name(self.package_name)
        if self.version_code is not None and self.version_code < 0:
            raise ValueError("Android versionCode must not be negative.")

    @property
    def build_id(self) -> str:
        name = self.version_name or "unknown"
        code = "unknown" if self.version_code is None else str(self.version_code)
        return f"{self.package_name}@{name}+{code}"

    def as_dict(self) -> dict[str, object]:
        return {
            "package_name": self.package_name,
            "version_name": self.version_name,
            "version_code": self.version_code,
            "min_sdk": self.min_sdk,
            "target_sdk": self.target_sdk,
            "first_install_time": self.first_install_time,
            "last_update_time": self.last_update_time,
            "installer_package_name": self.installer_package_name,
            "build_id": self.build_id,
        }


class PackageShellBackend(Protocol):
    """Minimal ADB capability required to inspect an installed package."""

    def shell(self, serial: str, arguments: Sequence[str | int | float]) -> str:
        ...


_PACKAGE_NAME_RE = re.compile(r"^[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+$")
_VERSION_CODE_RE = re.compile(r"(?m)^\s*versionCode=(\d+)(?:\s|$)")
_MIN_SDK_RE = re.compile(r"\bminSdk=(\d+)\b")
_TARGET_SDK_RE = re.compile(r"\btargetSdk=(\d+)\b")
_NOT_FOUND_MARKERS = (
    "unable to find package",
    "unknown package",
    "package not found",
)


def _validate_package_name(package_name: str) -> str:
    candidate = package_name.strip()
    if not _PACKAGE_NAME_RE.fullmatch(candidate):
        raise ValueError(f"Invalid Android package name: {package_name!r}")
    return candidate


def _line_value(output: str, key: str) -> str | None:
    match = re.search(rf"(?m)^\s*{re.escape(key)}=(.*?)\s*$", output)
    if match is None:
        return None
    value = match.group(1).strip()
    return None if not value or value.lower() == "null" else value


def _integer_match(pattern: re.Pattern[str], output: str) -> int | None:
    match = pattern.search(output)
    return int(match.group(1)) if match else None


def parse_dumpsys_package(output: str, package_name: str = DEFAULT_GAME_PACKAGE) -> GameBuildInfo:
    """Parse stable package/version fields from Android's ``dumpsys package`` output.

    Android vendors may add or reorder unrelated fields, so parsing is deliberately line- and
    key-based rather than tied to the complete output layout.
    """

    package = _validate_package_name(package_name)
    normalized = output.strip()
    lowered = normalized.lower()
    if not normalized or any(marker in lowered for marker in _NOT_FOUND_MARKERS):
        raise GamePackageNotFound(f"Android package is not installed or readable: {package}")

    version_code = _integer_match(_VERSION_CODE_RE, normalized)
    version_name = _line_value(normalized, "versionName")
    if version_code is None and version_name is None:
        raise GamePackageNotFound(
            f"ADB returned no version metadata for Android package: {package}"
        )

    return GameBuildInfo(
        package_name=package,
        version_name=version_name,
        version_code=version_code,
        min_sdk=_integer_match(_MIN_SDK_RE, normalized),
        target_sdk=_integer_match(_TARGET_SDK_RE, normalized),
        first_install_time=_line_value(normalized, "firstInstallTime"),
        last_update_time=_line_value(normalized, "lastUpdateTime"),
        installer_package_name=_line_value(normalized, "installerPackageName"),
    )


def inspect_game_build(
    backend: PackageShellBackend,
    serial: str,
    package_name: str = DEFAULT_GAME_PACKAGE,
) -> GameBuildInfo:
    """Read and parse the exact installed game build through one explicit ADB serial."""

    target_serial = serial.strip()
    if not target_serial:
        raise ValueError("ADB serial must not be empty.")
    package = _validate_package_name(package_name)
    output = backend.shell(target_serial, ["dumpsys", "package", package])
    return parse_dumpsys_package(output, package)


@dataclass(frozen=True, slots=True)
class SupportRule:
    """One match rule from the support matrix."""

    rule_id: str
    package_name: str
    status: GameCompatibilityStatus
    reason: str
    version_code: int | None = None
    version_name: str | None = None
    version_name_prefix: str | None = None
    version_code_min: int | None = None
    version_code_max: int | None = None

    def __post_init__(self) -> None:
        if not self.rule_id.strip():
            raise SupportMatrixError("Support rule id must not be empty.")
        _validate_package_name(self.package_name)
        if not self.reason.strip():
            raise SupportMatrixError(f"Support rule {self.rule_id!r} needs a reason.")
        if all(
            selector is None
            for selector in (
                self.version_code,
                self.version_name,
                self.version_name_prefix,
                self.version_code_min,
                self.version_code_max,
            )
        ):
            raise SupportMatrixError(
                f"Support rule {self.rule_id!r} must constrain a game version."
            )
        if self.version_code is not None and self.version_code < 0:
            raise SupportMatrixError("version_code must not be negative.")
        if (
            self.version_code is not None
            and self.version_code_min is not None
            and self.version_code < self.version_code_min
        ):
            raise SupportMatrixError("version_code must not be below version_code_min.")
        if (
            self.version_code is not None
            and self.version_code_max is not None
            and self.version_code > self.version_code_max
        ):
            raise SupportMatrixError("version_code must not exceed version_code_max.")
        if (
            self.version_name is not None
            and self.version_name_prefix is not None
            and not self.version_name.startswith(self.version_name_prefix)
        ):
            raise SupportMatrixError("version_name must match version_name_prefix.")
        if self.version_code_min is not None and self.version_code_min < 0:
            raise SupportMatrixError("version_code_min must not be negative.")
        if self.version_code_max is not None and self.version_code_max < 0:
            raise SupportMatrixError("version_code_max must not be negative.")
        if (
            self.version_code_min is not None
            and self.version_code_max is not None
            and self.version_code_min > self.version_code_max
        ):
            raise SupportMatrixError("version_code_min must not exceed version_code_max.")
        if self.status in {
            GameCompatibilityStatus.REPLAY_VALIDATED,
            GameCompatibilityStatus.SHADOW_VALIDATED,
            GameCompatibilityStatus.LIVE_VALIDATED,
        } and self.version_code is None:
            raise SupportMatrixError(
                f"Validated rule {self.rule_id!r} must match one exact version_code."
            )

    @property
    def specificity(self) -> int:
        """Return deterministic precedence; exact build matches override broad capture rules."""

        score = 0
        if self.version_code is not None:
            score += 1000
        if self.version_name is not None:
            score += 500
        if self.version_name_prefix is not None:
            score += 100
        if self.version_code_min is not None:
            score += 25
        if self.version_code_max is not None:
            score += 25
        return score

    def matches(self, build: GameBuildInfo) -> bool:
        if build.package_name != self.package_name:
            return False
        if self.version_code is not None and build.version_code != self.version_code:
            return False
        if self.version_name is not None and build.version_name != self.version_name:
            return False
        if self.version_name_prefix is not None:
            if build.version_name is None or not build.version_name.startswith(
                self.version_name_prefix
            ):
                return False
        if self.version_code_min is not None:
            if build.version_code is None or build.version_code < self.version_code_min:
                return False
        if self.version_code_max is not None:
            if build.version_code is None or build.version_code > self.version_code_max:
                return False
        return True

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> Self:
        required = ("id", "package", "status", "reason")
        missing = [key for key in required if key not in value]
        if missing:
            raise SupportMatrixError(
                f"Support rule is missing required keys: {', '.join(missing)}"
            )
        try:
            status = GameCompatibilityStatus(str(value["status"]))
        except ValueError as exc:
            raise SupportMatrixError(f"Unknown compatibility status: {value['status']!r}") from exc

        return cls(
            rule_id=str(value["id"]),
            package_name=str(value["package"]),
            status=status,
            reason=str(value["reason"]),
            version_code=_optional_int(value, "version_code"),
            version_name=_optional_str(value, "version_name"),
            version_name_prefix=_optional_str(value, "version_name_prefix"),
            version_code_min=_optional_int(value, "version_code_min"),
            version_code_max=_optional_int(value, "version_code_max"),
        )


@dataclass(frozen=True, slots=True)
class RuntimeAuthorization:
    """Result of reducing a requested mode to the highest validated safe mode."""

    requested_mode: RuntimeMode
    effective_mode: RuntimeMode
    downgraded: bool
    reason: str

    def as_dict(self) -> dict[str, object]:
        return {
            "requested_mode": self.requested_mode.value,
            "effective_mode": self.effective_mode.value,
            "downgraded": self.downgraded,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class SupportDecision:
    """Fail-closed compatibility result for one installed build."""

    build: GameBuildInfo
    status: GameCompatibilityStatus
    reason: str
    rule_id: str | None

    @property
    def live_actions_allowed(self) -> bool:
        return self.status.live_actions_allowed

    @property
    def maximum_runtime_mode(self) -> RuntimeMode:
        return self.status.maximum_runtime_mode

    def authorize(self, requested_mode: RuntimeMode | str) -> RuntimeAuthorization:
        requested = RuntimeMode(requested_mode)
        maximum = self.maximum_runtime_mode
        effective = (
            requested
            if _RUNTIME_MODE_RISK[requested] <= _RUNTIME_MODE_RISK[maximum]
            else maximum
        )
        downgraded = effective is not requested
        reason = self.reason
        if downgraded:
            reason = (
                f"Requested {requested.value} mode was reduced to {effective.value}: "
                f"{self.reason}"
            )
        return RuntimeAuthorization(
            requested_mode=requested,
            effective_mode=effective,
            downgraded=downgraded,
            reason=reason,
        )

    def require_live_actions(self) -> None:
        if not self.live_actions_allowed:
            raise LiveActionsBlocked(
                f"Live actions are blocked for {self.build.build_id}: {self.reason}"
            )

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "reason": self.reason,
            "rule_id": self.rule_id,
            "maximum_runtime_mode": self.maximum_runtime_mode.value,
            "live_actions_allowed": self.live_actions_allowed,
            "build": self.build.as_dict(),
        }


@dataclass(frozen=True, slots=True)
class SupportMatrix:
    """Reviewed compatibility policy loaded from TOML."""

    schema_version: int
    default_status: GameCompatibilityStatus
    default_reason: str
    rules: tuple[SupportRule, ...]

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise SupportMatrixError(
                f"Unsupported support-matrix schema version: {self.schema_version}"
            )
        if self.default_status in {
            GameCompatibilityStatus.REPLAY_VALIDATED,
            GameCompatibilityStatus.SHADOW_VALIDATED,
            GameCompatibilityStatus.LIVE_VALIDATED,
        }:
            raise SupportMatrixError(
                "The default matrix status must fail closed and cannot be a validated status."
            )
        if not self.default_reason.strip():
            raise SupportMatrixError("The support matrix needs a default_reason.")
        identifiers = [rule.rule_id for rule in self.rules]
        if len(identifiers) != len(set(identifiers)):
            raise SupportMatrixError("Support rule ids must be unique.")

    @classmethod
    def from_toml(cls, text: str) -> Self:
        try:
            payload = tomllib.loads(text)
        except tomllib.TOMLDecodeError as exc:
            raise SupportMatrixError(f"Invalid support-matrix TOML: {exc}") from exc
        try:
            schema_version = int(payload["schema_version"])
            default_status = GameCompatibilityStatus(str(payload["default_status"]))
            default_reason = str(payload["default_reason"])
        except KeyError as exc:
            raise SupportMatrixError(
                f"Support matrix is missing required key: {exc.args[0]}"
            ) from exc
        except ValueError as exc:
            raise SupportMatrixError(
                "Support matrix contains an invalid status or schema."
            ) from exc

        raw_rules = payload.get("builds", [])
        if not isinstance(raw_rules, list):
            raise SupportMatrixError("Support matrix 'builds' must be an array of tables.")
        parsed_rules: list[SupportRule] = []
        for index, rule in enumerate(raw_rules):
            if not isinstance(rule, dict):
                raise SupportMatrixError(
                    f"Support matrix build at index {index} must be a TOML table."
                )
            parsed_rules.append(SupportRule.from_mapping(rule))
        rules = tuple(parsed_rules)
        return cls(
            schema_version=schema_version,
            default_status=default_status,
            default_reason=default_reason,
            rules=rules,
        )

    @classmethod
    def load(cls, path: str | Path | None = None) -> Self:
        if path is not None:
            text = Path(path).expanduser().read_text(encoding="utf-8")
        else:
            resource = files("rushbot").joinpath(DEFAULT_SUPPORT_MATRIX_RESOURCE)
            text = resource.read_text(encoding="utf-8")
        return cls.from_toml(text)

    def evaluate(self, build: GameBuildInfo) -> SupportDecision:
        matches = [rule for rule in self.rules if rule.matches(build)]
        if not matches:
            return SupportDecision(
                build=build,
                status=self.default_status,
                reason=self.default_reason,
                rule_id=None,
            )

        highest_specificity = max(rule.specificity for rule in matches)
        finalists = [rule for rule in matches if rule.specificity == highest_specificity]
        if len(finalists) != 1:
            ids = ", ".join(sorted(rule.rule_id for rule in finalists))
            raise SupportMatrixError(
                f"Ambiguous support rules for {build.build_id}: {ids}"
            )
        selected = finalists[0]
        return SupportDecision(
            build=build,
            status=selected.status,
            reason=selected.reason,
            rule_id=selected.rule_id,
        )


def _optional_int(value: Mapping[str, Any], key: str) -> int | None:
    item = value.get(key)
    if item is None:
        return None
    if isinstance(item, bool):
        raise SupportMatrixError(f"{key} must be an integer, not a boolean.")
    try:
        return int(item)
    except (TypeError, ValueError) as exc:
        raise SupportMatrixError(f"{key} must be an integer.") from exc


def _optional_str(value: Mapping[str, Any], key: str) -> str | None:
    item = value.get(key)
    if item is None:
        return None
    text = str(item).strip()
    if not text:
        raise SupportMatrixError(f"{key} must not be empty.")
    return text
