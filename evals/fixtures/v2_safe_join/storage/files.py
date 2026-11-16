from .paths import safe_join


def resolve_upload(base, name):
    """上传文件在存储中的绝对路径。"""
    return safe_join(base, "uploads/" + name)


def resolve_avatar(base, user_id):
    return safe_join(base, f"avatars/{user_id}.png")
