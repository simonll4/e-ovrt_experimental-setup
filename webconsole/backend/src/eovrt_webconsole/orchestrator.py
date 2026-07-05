"""Orquestación del fleet de instancias media-plane vía `docker compose` (spec §3).

El compose de plataforma es la única fuente de verdad del fleet; este módulo
ejecuta exactamente 3 verbos (config/ps/up/stop) con nombres validados contra
la allowlist de labels — nunca input libre hacia el socket de Docker.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Awaitable, Callable

import httpx
from fastapi import FastAPI

from eovrt_webconsole.run_backend import RunBackend
from eovrt_webconsole.settings import ConsoleSettings

logger = logging.getLogger(__name__)

PROJECT_NAME = "eovrt"
INSTANCE_LABEL = "eovrt.instance"
MODEL_REF_LABEL = "eovrt.model_ref"
_COMPOSE_TIMEOUT_S = 60.0

RunCmd = Callable[..., Awaitable[tuple[int, str, str]]]


class ComposeError(RuntimeError):
    """docker compose falló (exit != 0, timeout o salida imparseable)."""


class UnknownInstance(KeyError):
    """Nombre fuera del fleet declarado."""


async def _run_subprocess(*args: str, cwd: Path) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *args, cwd=cwd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=_COMPOSE_TIMEOUT_S)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()  # reap: evita proceso zombie
        raise ComposeError(f"docker compose colgado (> {_COMPOSE_TIMEOUT_S:.0f}s): {' '.join(args)}")
    return proc.returncode or 0, stdout.decode(), stderr.decode()


def _normalize_labels(raw: Any) -> dict[str, str]:
    """compose config puede emitir labels como dict o como lista "k=v"."""
    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items()}
    out: dict[str, str] = {}
    for item in raw or []:
        key, _, value = str(item).partition("=")
        out[key] = value
    return out


class ComposeOrchestrator:
    def __init__(self, compose_dir: Path, run_cmd: RunCmd | None = None) -> None:
        self._dir = compose_dir
        self._run_cmd = run_cmd or _run_subprocess
        self._fleet: dict[str, str] | None = None

    async def _compose(self, *args: str) -> str:
        code, out, err = await self._run_cmd(
            "docker", "compose", "--project-name", PROJECT_NAME, *args, cwd=self._dir
        )
        if code != 0:
            raise ComposeError(err.strip() or out.strip() or f"exit {code}: {' '.join(args)}")
        return out

    async def fleet(self) -> dict[str, str]:
        """Instancias declaradas (label eovrt.instance) → model_ref. Cacheado."""
        if self._fleet is None:
            out = await self._compose("config", "--format", "json")
            try:
                services = json.loads(out).get("services", {})
            except json.JSONDecodeError as exc:
                raise ComposeError(f"config --format json imparseable: {exc}") from exc
            fleet: dict[str, str] = {}
            for name, svc in services.items():
                labels = _normalize_labels(svc.get("labels"))
                if labels.get(INSTANCE_LABEL) == "true":
                    fleet[name] = labels.get(MODEL_REF_LABEL, "?")
            self._fleet = fleet
        return self._fleet

    async def require(self, name: str) -> None:
        if name not in await self.fleet():
            raise UnknownInstance(name)

    async def ps(self) -> dict[str, str]:
        """Estado actual de las instancias del fleet (ausente = nunca creada)."""
        out = await self._compose("ps", "-a", "--format", "json")
        text = out.strip()
        if not text:
            return {}
        try:  # compose emite array JSON o NDJSON según versión
            data = json.loads(text)
            rows = data if isinstance(data, list) else [data]
        except json.JSONDecodeError:
            rows = [json.loads(line) for line in text.splitlines() if line.strip()]
        fleet = await self.fleet()
        return {
            r["Service"]: str(r.get("State", "unknown"))
            for r in rows
            if r.get("Service") in fleet
        }

    async def up(self, name: str) -> None:
        await self.require(name)
        await self._compose("up", "-d", "--no-build", name)

    async def stop(self, name: str) -> None:
        await self.require(name)
        await self._compose("stop", name)


NO_TARGET_URL = "http://eovrt-no-target.invalid:8080"
_SERVICE_PORT = 8080


class PlatformBusy(RuntimeError):
    """Hay un run corriendo en el target actual: no se puede switchear/apagar."""

    def __init__(self, run_id: str) -> None:
        super().__init__(f"Run activo en el target actual: {run_id}")
        self.run_id = run_id


class SwitchFailed(RuntimeError):
    """El switch falló en un paso concreto; sin rollback automático (spec §3.2)."""

    def __init__(self, step: str, detail: str) -> None:
        super().__init__(f"{step}: {detail}")
        self.step = step
        self.detail = detail


class TargetManager:
    """Target dinámico de la consola: la instancia del fleet actualmente activa.

    Es dueño del httpx.AsyncClient/RunBackend en app.state — el swap del target
    reemplaza ambos, así los routers existentes no cambian.
    """

    def __init__(
        self,
        app: FastAPI,
        orchestrator: ComposeOrchestrator,
        settings: ConsoleSettings,
        service_transport: httpx.AsyncBaseTransport | None = None,
        poll_interval: float = 2.0,
    ) -> None:
        self._app = app
        self._orch = orchestrator
        self._settings = settings
        self._transport = service_transport
        self._poll_interval = poll_interval
        self.active: str | None = None

    @staticmethod
    def _url(name: str) -> str:
        return f"http://{name}:{_SERVICE_PORT}"

    async def bootstrap(self) -> None:
        """Adopta el estado real al arrancar: 1 running = target; 0 o N = sin target."""
        ps = await self._orch.ps()
        running = [name for name, state in ps.items() if state == "running"]
        if len(running) > 1:
            logger.warning(
                "Varias instancias running (%s): target indefinido; el próximo activate normaliza",
                running,
            )
        await self._set_target(running[0] if len(running) == 1 else None)

    async def _set_target(self, name: str | None) -> None:
        old = getattr(self._app.state, "http", None)
        client = httpx.AsyncClient(
            base_url=self._url(name) if name else NO_TARGET_URL,
            transport=self._transport,
            timeout=30.0,
        )
        self._app.state.http = client
        self._app.state.backend = RunBackend(client)
        self.active = name
        if old is not None:
            await old.aclose()

    async def _active_run_id(self) -> str | None:
        if self.active is None:
            return None
        try:
            runs = await self._app.state.backend.list_runs()
        except Exception:  # noqa: BLE001 — target caído/no listo: nada que proteger
            return None
        for row in runs:
            if row.get("status") == "running":
                return row.get("run_id")
        return None

    async def _is_ready(self, name: str) -> bool:
        try:
            async with httpx.AsyncClient(
                base_url=self._url(name), transport=self._transport, timeout=5.0
            ) as client:
                return (await client.get("/readyz")).status_code == 200
        except httpx.HTTPError:
            return False

    async def switch(self, name: str) -> dict:
        await self._orch.require(name)
        fleet = await self._orch.fleet()
        ps = await self._orch.ps()
        if name == self.active and ps.get(name) == "running" and await self._is_ready(name):
            return {"target": name, "model_ref": fleet[name]}  # no-op: mismo target, no hay switch real
        run_id = await self._active_run_id()
        if run_id:
            raise PlatformBusy(run_id)
        await self._set_target(None)
        for other, state in ps.items():
            if state == "running":
                try:
                    await self._orch.stop(other)
                except ComposeError as exc:
                    raise SwitchFailed("stop", str(exc)) from exc
        try:
            await self._orch.up(name)
        except ComposeError as exc:
            raise SwitchFailed("up", str(exc)) from exc
        deadline = time.monotonic() + self._settings.switch_timeout_seconds
        while time.monotonic() < deadline:
            if await self._is_ready(name):
                await self._set_target(name)
                return {"target": name, "model_ref": fleet[name]}
            await asyncio.sleep(self._poll_interval)
        raise SwitchFailed(
            "readyz",
            f"{name} no llegó a ready en {self._settings.switch_timeout_seconds:.0f}s "
            "(¿pesos presentes? ver logs del contenedor)",
        )

    async def stop_active(self) -> None:
        if self.active is None:
            return
        run_id = await self._active_run_id()
        if run_id:
            raise PlatformBusy(run_id)
        name = self.active
        await self._set_target(None)
        try:
            await self._orch.stop(name)
        except ComposeError as exc:
            raise SwitchFailed("stop", str(exc)) from exc

    async def _ready(self, name: str, state: str) -> bool:
        return state == "running" and await self._is_ready(name)

    async def instances(self) -> list[dict]:
        fleet = await self._orch.fleet()
        ps = await self._orch.ps()
        names = sorted(fleet)
        states = [ps.get(name, "absent") for name in names]
        ready_flags = await asyncio.gather(
            *(self._ready(name, state) for name, state in zip(names, states))
        )
        return [
            {
                "name": name,
                "model_ref": fleet[name],
                "state": state,
                "ready": ready,
                "is_target": name == self.active,
            }
            for name, state, ready in zip(names, states, ready_flags)
        ]
