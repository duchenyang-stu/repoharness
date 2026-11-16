from .errors import ConfigError
from .parsers import parse_value


def load_config(schema, defaults, file_data, environ, prefix="APP_"):
    result = {}
    for key, typ in schema.items():
        env_key = prefix + key.upper()
        try:
            if env_key in environ:
                result[key] = parse_value(typ, environ[env_key])
            elif key in file_data:
                result[key] = parse_value(typ, file_data[key])
            elif key in defaults:
                result[key] = defaults[key]
            else:
                raise ConfigError(key, "missing")
        except ValueError as exc:
            raise ConfigError(key, str(exc)) from exc
    return result
