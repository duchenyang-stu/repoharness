from config import merge_config

DEFAULTS = {
    "debug": False,
    "db": {"host": "localhost", "port": 5432, "options": {"timeout": 30, "ssl": False}},
    "tags": ["a"],
}


def build_settings(overrides=None):
    return merge_config(DEFAULTS, overrides or {})
