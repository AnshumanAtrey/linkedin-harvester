"""Uniform scanner interface. Every scanner is a Scanner instance with an async run()."""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Awaitable, Callable


@dataclass
class ScanResult:
    scanner: str            # machine name, e.g. "phone_basic"
    title: str              # human label, e.g. "Phone Basics"
    status: str             # "ok" | "empty" | "error"
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    elapsed_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Scanner:
    name: str
    title: str
    run_fn: Callable[[str], Awaitable[dict[str, Any]]]

    async def run(self, target: str) -> ScanResult:
        start = time.perf_counter()
        try:
            data = await self.run_fn(target)
            status = "ok" if data else "empty"
            return ScanResult(
                scanner=self.name,
                title=self.title,
                status=status,
                data=data or {},
                elapsed_ms=int((time.perf_counter() - start) * 1000),
            )
        except Exception as exc:  # noqa: BLE001 - surface any scanner failure to UI
            return ScanResult(
                scanner=self.name,
                title=self.title,
                status="error",
                error=str(exc),
                elapsed_ms=int((time.perf_counter() - start) * 1000),
            )
