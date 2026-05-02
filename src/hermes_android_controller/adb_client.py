"""Small, testable ADB subprocess wrapper."""

from __future__ import annotations

from dataclasses import dataclass
import subprocess
from typing import Sequence


DEFAULT_TIMEOUT_SECONDS = 15.0


@dataclass(frozen=True)
class AdbCommandResult:
    """Result shape returned by every ADB command."""

    command: list[str]
    timeout: float
    stdout: str | bytes
    stderr: str | bytes
    returncode: int
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "command": self.command,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "returncode": self.returncode,
        }


class AdbClient:
    """ADB client that always invokes subprocess.run with argv lists."""

    def __init__(
        self,
        adb_path: str = "adb",
        device_id: str | None = None,
        serial: str | None = None,
        default_timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.adb_path = adb_path
        self.device_id = device_id or serial
        self.default_timeout = default_timeout

    def build_command(self, args: Sequence[str]) -> list[str]:
        command = [self.adb_path]
        if self.device_id:
            command.extend(["-s", self.device_id])
        command.extend(str(arg) for arg in args)
        return command

    def run(
        self,
        args: Sequence[str],
        timeout: float | None = None,
        *,
        text: bool = True,
    ) -> AdbCommandResult:
        effective_timeout = self.default_timeout if timeout is None else timeout
        command = self.build_command(args)
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=text,
                timeout=effective_timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return AdbCommandResult(
                command=command,
                timeout=effective_timeout,
                stdout=exc.stdout or ("" if text else b""),
                stderr=exc.stderr or ("" if text else b""),
                returncode=-1,
                timed_out=True,
            )

        return AdbCommandResult(
            command=command,
            timeout=effective_timeout,
            stdout=completed.stdout,
            stderr=completed.stderr,
            returncode=completed.returncode,
        )

    def shell(self, args: Sequence[str], timeout: float | None = None) -> AdbCommandResult:
        return self.run(["shell", *[str(arg) for arg in args]], timeout=timeout)


def get_default_client() -> AdbClient:
    return AdbClient()
