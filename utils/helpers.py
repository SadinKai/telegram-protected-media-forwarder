import hashlib
import os
import re
from pathlib import Path


def intify(value: str) -> any:
    """
    Attempts to convert a string chat ID into an integer.
    Supports negative IDs (like channels: -100xxx).
    """
    if not isinstance(value, str):
        return value

    val = value.strip()
    if not val:
        return val

    # Match negative or positive integer format
    if re.match(r"^[-+]?\d+$", val):
        return int(val)
    return val


def sanitize_filename(filename: str) -> str:
    """
    Sanitizes a string to be a safe file name across Windows, Linux, and macOS.
    Removes path traversal components and invalid characters.
    """
    if not filename:
        return "unnamed_file"

    # Remove path components
    filename = os.path.basename(filename)

    # Windows invalid characters: \ / : * ? " < > |
    # Linux/Unix invalid characters: / and null byte
    sanitized = re.sub(r'[\x00-\x1f\\/*?:"<>|]', "_", filename)

    # Strip leading/trailing dots and spaces
    sanitized = sanitized.strip(". ")

    # Ensure it's not empty after cleaning
    if not sanitized:
        sanitized = "safe_file"

    return sanitized


def get_file_hash(file_path: str) -> str:
    """
    Computes the MD5 hash of a local file.
    Reads in chunks to minimize memory usage for large files.
    """
    if not os.path.exists(file_path):
        return ""

    hasher = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return ""


def is_safe_path(base_dir: str, path: str) -> bool:
    """
    Verifies if a file path lies within the specified base directory (prevents path traversal).
    """
    try:
        base_path = Path(base_dir).resolve()
        target_path = Path(path).resolve()
        return base_path in target_path.parents or base_path == target_path
    except Exception:
        return False


def get_chat_type(entity, me_id=None) -> str:
    """
    Returns the user-friendly string category of a Telethon dialog entity.
    """
    from telethon.tl.types import Channel, Chat, User

    if isinstance(entity, User):
        is_self = getattr(entity, "is_self", False) or (
            me_id and getattr(entity, "id", None) == me_id
        )
        if is_self:
            return "Saved Messages"
        return "User"
    elif isinstance(entity, Chat):
        return "Group"
    elif isinstance(entity, Channel):
        if getattr(entity, "megagroup", False):
            return "Supergroup"
        return "Channel"
    return "Unknown"


def get_chat_access(entity) -> str:
    """
    Determines if the user has Read/Write or Read Only privileges in a chat.
    """
    from telethon.tl.types import Channel, Chat, User

    if isinstance(entity, User):
        return "Read/Write"
    elif isinstance(entity, Chat):
        if (
            getattr(entity, "left", False)
            or getattr(entity, "kicked", False)
            or getattr(entity, "deactivated", False)
        ):
            return "Read Only"
        banned_rights = getattr(entity, "banned_rights", None)
        if banned_rights and getattr(banned_rights, "send_messages", False):
            return "Read Only"
        return "Read/Write"
    elif isinstance(entity, Channel):
        if getattr(entity, "left", False):
            return "Read Only"
        if getattr(entity, "megagroup", False):
            # Supergroup
            banned_rights = getattr(entity, "banned_rights", None)
            if banned_rights and getattr(banned_rights, "send_messages", False):
                return "Read Only"
            default_banned = getattr(entity, "default_banned_rights", None)
            if default_banned and getattr(default_banned, "send_messages", False):
                # Check if we are admin/creator to override default restrictions
                if not (getattr(entity, "creator", False) or getattr(entity, "admin_rights", None)):
                    return "Read Only"
            return "Read/Write"
        else:
            # Broadcast Channel: only admins with post_messages can post
            if getattr(entity, "creator", False):
                return "Read/Write"
            admin_rights = getattr(entity, "admin_rights", None)
            if admin_rights and getattr(admin_rights, "post_messages", False):
                return "Read/Write"
            return "Read Only"
    return "Read Only"
