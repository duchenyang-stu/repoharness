class DuplicateIdError(ValueError):
    def __init__(self, order_id, line):
        super().__init__(f"duplicate id {order_id!r} at line {line}")
        self.order_id = order_id
        self.line = line


class MissingColumnError(ValueError):
    def __init__(self, column):
        super().__init__(f"missing column {column!r}")
        self.column = column
