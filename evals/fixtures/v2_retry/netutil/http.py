def parse_status_line(line):
    """'HTTP/1.1 200 OK' -> (200, 'OK')"""
    parts = line.split(" ", 2)
    return int(parts[1]), parts[2] if len(parts) > 2 else ""
