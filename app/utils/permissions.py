from __future__ import annotations

from functools import wraps
from typing import Dict, List, Optional

from flask import abort, g
from flask_login import current_user

from app.models.mongodb_database import mongodb


# Standard-Rechte-Matrix (kann per Admin-UI überschrieben werden)
ALLOWED_ACTIONS: Dict[str, List[str]] = {
    "tools": ["view", "create", "edit", "delete", "export"],
    "consumables": ["view", "create", "edit", "delete", "export"],
    "workers": ["view", "create", "edit", "delete"],
    "tickets": ["view", "create", "edit", "assign", "delete", "export"],
    "jobs": ["view", "create", "edit", "delete"],
    "settings": ["manage"],
}

def get_all_actions() -> List[str]:
    actions: List[str] = []
    for acts in ALLOWED_ACTIONS.values():
        for a in acts:
            if a not in actions:
                actions.append(a)
    return sorted(actions)

def normalize_permissions(permissions: Dict[str, Dict[str, List[str]]]) -> Dict[str, Dict[str, List[str]]]:
    """Filtert nicht erlaubte Aktionen je Bereich heraus."""
    normalized: Dict[str, Dict[str, List[str]]] = {}
    for role, areas in permissions.items():
        for area, actions in areas.items():
            allowed = set(ALLOWED_ACTIONS.get(area, []))
            valid_actions = [a for a in actions if a in allowed]
            if not valid_actions:
                continue
            normalized.setdefault(role, {})[area] = sorted(list(set(valid_actions)))
    return normalized

DEFAULT_ROLE_PERMISSIONS: Dict[str, Dict[str, List[str]]] = {
    # Admin: Vollzugriff ohne Einschränkungen
    "admin": {
        "tools": ["view", "create", "edit", "delete", "export"],
        "consumables": ["view", "create", "edit", "delete", "export"],
        "workers": ["view", "create", "edit", "delete"],
        "tickets": ["view", "create", "edit", "assign", "delete", "export"],
        "jobs": ["view", "create", "edit", "delete"],
        "settings": ["manage"],
    },
    # Mitarbeiter: Vollzugriff wie Admin, jedoch nur innerhalb der eigenen Abteilung (durch Scoping erzwungen)
    "mitarbeiter": {
        "tools": ["view", "create", "edit", "delete", "export"],
        "consumables": ["view", "create", "edit", "delete", "export"],
        "workers": ["view", "create", "edit", "delete"],
        "tickets": ["view", "create", "edit", "assign", "delete", "export"],
        "jobs": ["view", "create", "edit", "delete"],
        # kein Zugriff auf settings
    },
    # Anwender: Vollzugriff innerhalb der eigenen Abteilung, keine Einstellungen
    "anwender": {
        "tools": ["view", "create", "edit", "delete", "export"],
        "consumables": ["view", "create", "edit", "delete", "export"],
        "workers": ["view", "create", "edit", "delete"],
        "tickets": ["view", "create", "edit", "assign", "delete", "export"],
        "jobs": ["view", "create", "edit", "delete"],
        # kein Zugriff auf settings
    },
    # Teilnehmer: Zugriff auf Tickets (view/create) und Jobbörse (view)
    "teilnehmer": {
        "tickets": ["view", "create"],
        "jobs": ["view"],
    },
}


def get_role_permissions() -> Dict[str, Dict[str, List[str]]]:
    """Gibt die festen Rollenrechte zurück (DB wird ignoriert)."""
    return DEFAULT_ROLE_PERMISSIONS


def set_role_permissions(permissions: Dict[str, Dict[str, List[str]]]) -> bool:
    """Schreibt die Rollenrechte in die Settings-Collection (Upsert)."""
    # Nicht erlaubte Kombinationen herausfiltern
    filtered = normalize_permissions(permissions)
    return bool(
        mongodb.update_one(
            "settings",
            {"key": "role_permissions"},
            {"$set": {"value": filtered}},
            upsert=True,
        )
    )


def ensure_default_role_permissions() -> None:
    """Legt bei Bedarf die Default-Matrix an (ohne Admin zu entmachten)."""
    setting = mongodb.find_one("settings", {"key": "role_permissions"})
    if not setting:
        set_role_permissions(DEFAULT_ROLE_PERMISSIONS)


def has_permission(role: str, area: str, action: str, department: Optional[str] = None) -> bool:
    """Prüft, ob eine Rolle eine Aktion in einem Bereich ausführen darf.

    department wird für zukünftige Abteilungs-Overrides reserviert.
    """
    if not role:
        return False
    # Admin darf immer alles (Guardrail)
    if role == "admin":
        return True
    matrix = get_role_permissions()
    role_entry = matrix.get(role, {})
    allowed_actions = role_entry.get(area, [])
    return action in allowed_actions


def permission_required(area: str, action: str):
    """Decorator für Routen, die eine bestimmte Berechtigung verlangen."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            # Muss eingeloggt sein (wir verlassen uns auf vorhandenes login_required)
            if not getattr(current_user, "is_authenticated", False):
                abort(401)
            current_dept = getattr(g, "current_department", None)
            if not has_permission(current_user.role, area, action, current_dept):
                abort(403)
            return view_func(*args, **kwargs)

        return wrapped

    return decorator


