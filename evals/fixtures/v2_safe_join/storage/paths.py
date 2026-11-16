import posixpath


def safe_join(base, user_path):
    return posixpath.normpath(posixpath.join(base, user_path))
