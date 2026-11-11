"""The integration's own backups (separate from Home Assistant backups).

File format `.mhbackup`: gzip( JSON header line + "\\n" + Fernet(scrypt(password), JSON body) ).
The header is readable without the password (date, version, number of persons – no names) so
the restore preview works; the body contains everything (configuration, key ring, all person
stores with still-encrypted contents, models). Whoever has the file *and* the password can
restore it – the admin area says so.

Older backup formats are migrated on restore (`migrate_body`).
"""
from __future__ import annotations

import base64
import gzip
import json
import logging
import os
import re
from datetime import datetime
from typing import Any

from .const import BACKUP_DIR, BACKUP_EXT, BACKUP_FORMAT, VERSION
from .logic.crypto import CryptoError, b64, decrypt_bytes, derive_key, encrypt_bytes, new_salt, unb64

_LOGGER = logging.getLogger(__name__)
MAGIC = "MHBACKUP"
_NAME_RE = re.compile(r"^[A-Za-z0-9_.\-]+\.mhbackup$")


class BackupError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def build(body: dict, password: str, meta: dict) -> bytes:
    salt = new_salt()
    key = derive_key(password, salt)
    header = {"magic": MAGIC, "format": BACKUP_FORMAT, "version": VERSION, "salt": b64(salt), **meta}
    payload = encrypt_bytes(key, json.dumps(body, separators=(",", ":")).encode("utf-8"))
    return gzip.compress((json.dumps(header) + "\n" + payload).encode("utf-8"), compresslevel=6)


def read_header(blob: bytes) -> dict:
    try:
        raw = gzip.decompress(blob).decode("utf-8")
        header = json.loads(raw.split("\n", 1)[0])
    except (OSError, ValueError, UnicodeDecodeError) as err:
        raise BackupError("invalid_file") from err
    if header.get("magic") != MAGIC:
        raise BackupError("invalid_file")
    return header


def open_body(blob: bytes, password: str) -> tuple[dict, dict]:
    header = read_header(blob)
    raw = gzip.decompress(blob).decode("utf-8").split("\n", 1)[1]
    try:
        key = derive_key(password, unb64(header["salt"]))
        body = json.loads(decrypt_bytes(key, raw).decode("utf-8"))
    except (CryptoError, KeyError, ValueError) as err:
        raise BackupError("wrong_password") from err
    return header, migrate_body(int(header.get("format", 1)), body)


def migrate_body(fmt: int, body: dict) -> dict:
    """Upgrade older backup bodies. Format 1 is the first one."""
    body = dict(body)
    body.setdefault("persons", {})
    body.setdefault("models", {})
    return body


# ------------------------------------------------------------------ Laufzeit-Anbindung
def _dir(rt: Any) -> str:
    return rt.hass.config.path(BACKUP_DIR)


def collect(rt: Any) -> dict:
    """Everything as stored on disk (contents stay encrypted with the person keys)."""
    from .storage import encrypt_model
    return {
        "config": rt._config_data(),
        "keys": rt.keyring.to_dict(),
        "persons": {pid: p.vault.dump() for pid, p in rt.persons.items()},
        "models": {pid: encrypt_model(p.vault.dek, rt._model_data(p)) for pid, p in rt.persons.items()},
    }


def _password_key(rt: Any) -> str | None:
    """The stored backup password (needed for automatic backups). Kept with the master key."""
    pw = rt.settings["backup"].get("password")
    if not pw:
        return None
    try:
        from .logic.crypto import decrypt_json
        return decrypt_json(rt.keyring.master, pw)
    except CryptoError:
        return None


def set_password(rt: Any, password: str | None) -> None:
    from .logic.crypto import encrypt_json
    if password:
        if len(password) < 8:
            raise BackupError("password_short")
        rt.settings["backup"]["password"] = encrypt_json(rt.keyring.master, password)
    else:
        rt.settings["backup"]["password"] = None
    rt.save_config()


async def async_create(rt: Any, password: str | None = None, label: str = "manual") -> dict:
    pw = password or _password_key(rt)
    if not pw:
        raise BackupError("no_password")
    body = collect(rt)
    now = datetime.now().astimezone()
    meta = {"created": now.isoformat(), "persons": len(rt.persons), "label": label}
    blob = await rt.hass.async_add_executor_job(build, body, pw, meta)
    name = f"mental_health_{now.strftime('%Y%m%d_%H%M%S')}_{label}{BACKUP_EXT}"
    await rt.hass.async_add_executor_job(_write, _dir(rt), name, blob)
    rt.backup_info["last"] = now.isoformat()
    rt.save_config()
    await rt.hass.async_add_executor_job(_prune, _dir(rt), int(rt.settings["backup"]["keep"]))
    rt.recompute_hub()
    return {"name": name, "size": len(blob), "created": meta["created"]}


async def async_create_auto(rt: Any) -> dict:
    return await async_create(rt, None, "auto")


def _write(directory: str, name: str, blob: bytes) -> None:
    os.makedirs(directory, exist_ok=True)
    tmp = os.path.join(directory, name + ".tmp")
    with open(tmp, "wb") as f:
        f.write(blob)
    os.replace(tmp, os.path.join(directory, name))


def _prune(directory: str, keep: int) -> None:
    try:
        files = sorted(f for f in os.listdir(directory) if f.endswith(BACKUP_EXT) and "_auto" in f)
    except FileNotFoundError:
        return
    for f in files[:-keep] if keep > 0 else []:
        try:
            os.remove(os.path.join(directory, f))
        except OSError:
            pass


def list_backups(rt: Any) -> list[dict]:
    d = _dir(rt)
    out = []
    try:
        names = sorted((f for f in os.listdir(d) if f.endswith(BACKUP_EXT)), reverse=True)
    except (FileNotFoundError, NotADirectoryError):
        return []
    for f in names[:60]:
        try:
            st = os.stat(os.path.join(d, f))
            out.append({"name": f, "size": st.st_size, "mtime": st.st_mtime})
        except OSError:
            continue
    return out


def read_file(rt: Any, name: str) -> bytes:
    if not _NAME_RE.match(name or ""):
        raise BackupError("invalid_name")
    path = os.path.join(_dir(rt), name)
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError as err:
        raise BackupError("not_found") from err


def decode_upload(data_b64: str) -> bytes:
    try:
        raw = base64.b64decode(data_b64.split(",", 1)[-1])
    except ValueError as err:
        raise BackupError("invalid_file") from err
    if len(raw) > 64 * 1024 * 1024:
        raise BackupError("too_large")
    return raw


def preview(blob: bytes, password: str) -> dict:
    header, body = open_body(blob, password)
    persons = body.get("config", {}).get("persons", {})
    return {
        "created": header.get("created"), "version": header.get("version"), "format": header.get("format"),
        "persons": [{"id": pid, "name": p.get("name"), "days": len((body["persons"].get(pid) or {}).get("days") or {})}
                    for pid, p in persons.items()],
        "size": len(blob),
    }


async def async_restore(rt: Any, blob: bytes, password: str, scope: str = "all", pid: str | None = None) -> dict:
    """Restore. Always writes a safety backup of the current state first (if a password exists)."""
    header, body = await rt.hass.async_add_executor_job(open_body, blob, password)
    safety = None
    try:
        safety = await async_create(rt, password, "before_restore")
    except BackupError:
        safety = None
    from homeassistant.helpers.storage import Store

    from .const import (
        CONFIG_STORE_VERSION, KEY_STORE_VERSION, MODEL_STORE_VERSION, PERSON_STORE_VERSION, STORE_CONFIG,
        STORE_KEYS, STORE_MODEL, STORE_PERSON,
    )
    from .logic.crypto import Keyring
    cfg = body["config"]
    keys = body["keys"]
    if scope == "config":
        cur = rt._config_data()
        merged = {**cur, "settings": cfg.get("settings", cur["settings"])}
        await Store(rt.hass, CONFIG_STORE_VERSION, STORE_CONFIG).async_save(merged)
    elif scope == "person" and pid:
        if pid not in cfg.get("persons", {}):
            raise BackupError("person_not_in_backup")
        cur = rt._config_data()
        cur["persons"][pid] = cfg["persons"][pid]
        ring = Keyring(rt.keyring.to_dict())
        ring.persons[pid] = Keyring(keys).persons[pid]
        # Personenschlüssel mit dem aktuellen Master neu umhüllen
        old = Keyring(keys)
        from .logic.crypto import wrap_key
        ring.persons[pid]["dek"] = wrap_key(ring.master, old.dek(pid))
        if ring.persons[pid].get("tek"):
            ring.persons[pid]["tek"] = wrap_key(ring.master, old.tek_without_pin(pid))
        await Store(rt.hass, CONFIG_STORE_VERSION, STORE_CONFIG).async_save(cur)
        await Store(rt.hass, KEY_STORE_VERSION, STORE_KEYS).async_save(ring.to_dict())
        await Store(rt.hass, PERSON_STORE_VERSION, STORE_PERSON.format(pid=pid)).async_save(body["persons"].get(pid) or {})
        await Store(rt.hass, MODEL_STORE_VERSION, STORE_MODEL.format(pid=pid)).async_save(body["models"].get(pid) or {})
    else:
        rt._paused_writes = True
        for old_pid in list(rt.persons):
            if old_pid not in body["persons"]:
                await Store(rt.hass, PERSON_STORE_VERSION, STORE_PERSON.format(pid=old_pid)).async_remove()
                await Store(rt.hass, MODEL_STORE_VERSION, STORE_MODEL.format(pid=old_pid)).async_remove()
        await Store(rt.hass, CONFIG_STORE_VERSION, STORE_CONFIG).async_save(cfg)
        await Store(rt.hass, KEY_STORE_VERSION, STORE_KEYS).async_save(keys)
        for p_id, data in body["persons"].items():
            await Store(rt.hass, PERSON_STORE_VERSION, STORE_PERSON.format(pid=p_id)).async_save(data)
        for p_id, data in body["models"].items():
            await Store(rt.hass, MODEL_STORE_VERSION, STORE_MODEL.format(pid=p_id)).async_save(data)
    rt._paused_writes = True          # Neuladen übernimmt den wiederhergestellten Stand
    rt.hass.config_entries.async_schedule_reload(rt.entry.entry_id)
    return {"ok": True, "safety": safety, "from": header.get("created")}
