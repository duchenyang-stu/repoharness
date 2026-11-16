import posixpath


def safe_join(base, user_path):
    if "\x00" in user_path:
        raise ValueError("null byte in path")
    cleaned = user_path.replace("\\", "/")
    if cleaned.startswith("/"):
        raise ValueError("absolute paths are not allowed")
    root = posixpath.normpath(base)
    result = posixpath.normpath(posixpath.join(root, cleaned))
    if result != root and not result.startswith(root.rstrip("/") + "/"):
        raise ValueError("path escapes the storage root")
    return result
