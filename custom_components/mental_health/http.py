"""HTTP endpoints for backup download/upload (admins only; files can exceed websocket limits)."""
from __future__ import annotations

import time
from typing import Any

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from . import archive
from .const import BACKUP_DIR, BACKUP_EXT

MAX_UPLOAD = 64 * 1024 * 1024


def _rt(hass: HomeAssistant) -> Any:
    from .websocket import get_runtime
    return get_runtime(hass)


class BackupDownloadView(HomeAssistantView):
    url = "/api/mental_health/backup/{name}"
    name = "api:mental_health:backup_download"
    requires_auth = True

    async def get(self, request: web.Request, name: str) -> web.StreamResponse:
        hass: HomeAssistant = request.app["hass"]
        user = request["hass_user"]
        rt = _rt(hass)
        if rt is None or not rt.admin_access(user, request.query.get("admin_session")):
            return web.Response(status=403)
        try:
            blob = await hass.async_add_executor_job(archive.read_file, rt, name)
        except archive.BackupError:
            return web.Response(status=404)
        return web.Response(body=blob, content_type="application/octet-stream",
                            headers={"Content-Disposition": f'attachment; filename="{name}"', "Cache-Control": "no-store"})


class BackupUploadView(HomeAssistantView):
    url = "/api/mental_health/backup"
    name = "api:mental_health:backup_upload"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        user = request["hass_user"]
        rt = _rt(hass)
        if rt is None or not rt.admin_access(user, request.query.get("admin_session")):
            return web.Response(status=403)
        body = await request.content.read(MAX_UPLOAD + 1)
        if len(body) > MAX_UPLOAD:
            return web.json_response({"error": "too_large"}, status=413)
        try:
            archive.read_header(body)
        except archive.BackupError as err:
            return web.json_response({"error": err.code}, status=400)
        name = f"mental_health_upload_{time.strftime('%Y%m%d_%H%M%S')}{BACKUP_EXT}"
        await hass.async_add_executor_job(archive._write, hass.config.path(BACKUP_DIR), name, body)
        return web.json_response({"name": name, "size": len(body)})


def register(hass: HomeAssistant) -> None:
    if hass.http is None:
        return
    hass.http.register_view(BackupDownloadView())
    hass.http.register_view(BackupUploadView())

