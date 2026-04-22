import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from content_validation import validate_email_address
from default_content import get_default_site_content


def _ensure_parent(path):
    path.parent.mkdir(parents=True, exist_ok=True)


def _write_json(path, payload):
    _ensure_parent(path)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


def _read_json(path, fallback):
    if not path.exists():
        return deepcopy(fallback)

    return json.loads(path.read_text(encoding="utf-8"))


def _append_json_line(path, payload):
    _ensure_parent(path)
    with Path(path).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _merge_content(defaults, overrides):
    if isinstance(defaults, dict) and isinstance(overrides, dict):
        merged = {}
        for key, value in defaults.items():
            merged[key] = _merge_content(value, overrides.get(key))
        return merged

    if isinstance(defaults, list):
        if not isinstance(overrides, list):
            return deepcopy(defaults)
        return deepcopy(overrides)

    if overrides is None:
        return defaults

    return overrides


def normalize_email(email):
    return str(email or "").strip().lower()


def _timestamp_slug():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _backup_path(backups_dir, backup_id):
    return Path(backups_dir) / f"{backup_id}.json"


def _write_backup(backups_dir, content, actor_name="", actor_email="", reason="save"):
    backups_dir = Path(backups_dir)
    backup_id = f"{_timestamp_slug()}-{uuid4().hex[:8]}"
    backup_payload = {
        "id": backup_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "actor_name": actor_name,
        "actor_email": actor_email,
        "content": deepcopy(content),
    }
    _write_json(_backup_path(backups_dir, backup_id), backup_payload)
    return backup_payload


def prune_backups(backups_dir, keep=25):
    backups_dir = Path(backups_dir)
    backups_dir.mkdir(parents=True, exist_ok=True)
    backup_files = sorted(backups_dir.glob("*.json"), reverse=True)

    for backup_file in backup_files[keep:]:
        backup_file.unlink(missing_ok=True)


def list_content_backups(backups_dir, limit=10):
    backups_dir = Path(backups_dir)
    backups_dir.mkdir(parents=True, exist_ok=True)

    backups = []
    for backup_file in sorted(backups_dir.glob("*.json"), reverse=True)[:limit]:
        payload = _read_json(backup_file, {})
        backups.append(
            {
                "id": payload.get("id") or backup_file.stem,
                "created_at": payload.get("created_at", ""),
                "reason": payload.get("reason", "save"),
                "actor_name": payload.get("actor_name", ""),
                "actor_email": payload.get("actor_email", ""),
                "content_meta": payload.get("content", {}).get("meta", {}),
            }
        )

    return backups


def get_content_backup(backups_dir, backup_id):
    payload = _read_json(_backup_path(backups_dir, backup_id), None)
    if not payload:
        raise FileNotFoundError("Backup not found")
    return payload


def get_site_content(content_path):
    content_path = Path(content_path)
    defaults = get_default_site_content()

    if not content_path.exists():
        _write_json(content_path, defaults)
        return defaults

    stored = _read_json(content_path, defaults)
    return _merge_content(defaults, stored)


def save_site_content(
    content_path,
    content,
    backups_dir=None,
    actor_name="",
    actor_email="",
    backup_reason="save",
    backup_keep=25,
):
    content_path = Path(content_path)
    merged = _merge_content(get_default_site_content(), content)

    if backups_dir and content_path.exists():
        current = _read_json(content_path, get_default_site_content())
        _write_backup(
            backups_dir,
            current,
            actor_name=actor_name,
            actor_email=actor_email,
            reason=backup_reason,
        )
        prune_backups(backups_dir, keep=backup_keep)

    _write_json(content_path, merged)
    return merged


def restore_site_content(
    content_path,
    backups_dir,
    backup_id,
    actor_name="",
    actor_email="",
    backup_keep=25,
):
    backup_payload = get_content_backup(backups_dir, backup_id)
    restored = save_site_content(
        content_path,
        backup_payload["content"],
        backups_dir=backups_dir,
        actor_name=actor_name,
        actor_email=actor_email,
        backup_reason=f"restore:{backup_id}",
        backup_keep=backup_keep,
    )
    return restored


def append_audit_event(audit_path, event):
    _append_json_line(Path(audit_path), event)


def get_admin_emails(admins_path, seeded_emails=None):
    admins_path = Path(admins_path)
    seeded_emails = seeded_emails or []

    if admins_path.exists():
        payload = _read_json(admins_path, {"emails": []})
    else:
        payload = {"emails": []}

    existing = {
        normalize_email(email)
        for email in payload.get("emails", [])
        if normalize_email(email)
    }
    existing.update(normalize_email(email) for email in seeded_emails if normalize_email(email))

    normalized = sorted(existing)
    _write_json(admins_path, {"emails": normalized})
    return normalized


def add_admin_email(admins_path, email):
    normalized_email = normalize_email(validate_email_address(email, "admin email"))

    admins = set(get_admin_emails(admins_path))
    admins.add(normalized_email)
    _write_json(Path(admins_path), {"emails": sorted(admins)})
    return sorted(admins)


def remove_admin_email(admins_path, email):
    normalized_email = normalize_email(email)
    admins = set(get_admin_emails(admins_path))

    if normalized_email not in admins:
        raise KeyError("Admin email not found")

    if len(admins) <= 1:
        raise RuntimeError("At least one admin account must remain")

    admins.remove(normalized_email)
    _write_json(Path(admins_path), {"emails": sorted(admins)})
    return sorted(admins)
