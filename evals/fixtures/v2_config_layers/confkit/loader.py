from .parsers import parse_value


def load_config(schema, defaults, file_data, environ, prefix="APP_"):
    result = dict(defaults)
    for key, typ in schema.items():
        env_key = prefix + key.upper()
        if env_key in environ:
            result[key] = parse_value(typ, environ[env_key])
        if key in file_data:
            result[key] = parse_value(typ, file_data[key])
    return result
