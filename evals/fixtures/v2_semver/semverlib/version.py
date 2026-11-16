import re

_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+([0-9A-Za-z.-]+))?$")


class Version:
    def __init__(self, text):
        match = _PATTERN.match(text.strip())
        if not match:
            raise ValueError(f"invalid version: {text!r}")
        self.major, self.minor, self.patch = (int(match.group(i)) for i in (1, 2, 3))
        self.prerelease = match.group(4) or ""
        self.build = match.group(5) or ""

    def _key(self):
        return (self.major, self.minor, self.patch, self.prerelease)

    def __lt__(self, other):
        return self._key() < other._key()

    def __eq__(self, other):
        return self._key() == other._key() and self.build == other.build

    def __repr__(self):
        return f"Version({str(self)!r})"

    def __str__(self):
        text = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            text += "-" + self.prerelease
        if self.build:
            text += "+" + self.build
        return text
