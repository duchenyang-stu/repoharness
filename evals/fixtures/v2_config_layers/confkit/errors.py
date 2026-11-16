class ConfigError(Exception):
    def __init__(self, key, message):
        super().__init__(f"{key}: {message}")
        self.key = key
        self.message = message
