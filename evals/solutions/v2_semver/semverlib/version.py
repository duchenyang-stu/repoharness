import functools
import re

_NUM = r"(0|[1-9]\d*)"
_IDENT = r"[0-9A-Za-z-]+"
_PATTERN = re.compile(
    rf"^{_NUM}\.{_NUM}\.{_NUM}(?:-({_IDENT}(?:\.{_IDENT})*))?(?:\+({_IDENT}(?:\.{_IDENT})*))?$"
)


def _prerelease_key(text):
    parts = []
    for part in text.split("."):
        if part.isdigit():
            if len(part) > 1 and part.startswith("0"):
                raise ValueError(f"numeric identifier has leading zero: {part!r}")
            parts.append((0, int(part), ""))
        else:
            parts.append((1, 0, part))
    return tuple(parts)


@functools.total_ordering
class Version:
    def __init__(self, text):
        match = _PATTERN.match(text.strip())
        if not match:
            raise ValueError(f"invalid version: {text!r}")
        self.major, self.minor, self.patch = (int(match.group(i)) for i in (1, 2, 3))
        self.prerelease = match.group(4) or ""
        self.build = match.group(5) or ""
        self._pre = _prerelease_key(self.prerelease) if self.prerelease else ()

    def _key(self):
        # A release (no prerelease) sorts above any prerelease of the same triple.
        return (self.major, self.minor, self.patch, 0 if self.prerelease else 1, self._pre)

    def __lt__(self, other):
        return self._key() < other._key()

    def __eq__(self, other):
        return isinstance(other, Version) and self._key() == other._key()

    def __hash__(self):
        return hash(self._key())

    def __repr__(self):
        return f"Version({str(self)!r})"

    def __str__(self):
        text = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            text += "-" + self.prerelease
        if self.build:
            text += "+" + self.build
        return text
