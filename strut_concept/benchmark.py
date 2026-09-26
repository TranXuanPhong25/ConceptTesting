"""Fixed real-world benchmark selection and source preparation.

The functions come from Picolibc's Newlib-derived string implementation.  No
benchmark source is vendored: prepared copies and generated artifacts belong in
an external run directory.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Subject:
    name: str
    return_type: str
    parameters: tuple[tuple[str, str, str], ...]


def _s(name: str, ret: str, *params: tuple[str, str, str]) -> Subject:
    return Subject(name, ret, tuple(params))


S = ("const char *", "string", "")
W = ("const wchar_t *", "wstring", "")
N = ("size_t", "integer", "")
V = ("const void *", "bytes", "")

# Order is protocol data: 0:30 was fixed as tuning; all 40 are the full set.
SUBJECTS: tuple[Subject, ...] = (
    _s("strcmp", "int", (S[0], S[1], "s1"), (S[0], S[1], "s2")),
    _s("strncmp", "int", (S[0], S[1], "s1"), (S[0], S[1], "s2"), (N[0], N[1], "n")),
    _s("strcasecmp", "int", (S[0], S[1], "s1"), (S[0], S[1], "s2")),
    _s("strncasecmp", "int", (S[0], S[1], "s1"), (S[0], S[1], "s2"), (N[0], N[1], "n")),
    _s("strlen", "size_t", (S[0], S[1], "str")),
    _s("strnlen", "size_t", (S[0], S[1], "str"), (N[0], N[1], "maxlen")),
    _s("strspn", "size_t", (S[0], S[1], "s1"), (S[0], S[1], "s2")),
    _s("strcspn", "size_t", (S[0], S[1], "s1"), (S[0], S[1], "s2")),
    _s("strverscmp", "int", (S[0], S[1], "s1"), (S[0], S[1], "s2")),
    _s("timingsafe_memcmp", "int", (V[0], V[1], "b1"), (V[0], V[1], "b2"), (N[0], N[1], "len")),
    _s("memcmp", "int", (V[0], V[1], "m1"), (V[0], V[1], "m2"), (N[0], N[1], "n")),
    _s("bcmp", "int", (V[0], V[1], "m1"), (V[0], V[1], "m2"), (N[0], N[1], "n")),
    _s("wmemcmp", "int", (W[0], W[1], "s1"), (W[0], W[1], "s2"), (N[0], N[1], "n")),
    _s("wcscmp", "int", (W[0], W[1], "s1"), (W[0], W[1], "s2")),
    _s("wcsncmp", "int", (W[0], W[1], "s1"), (W[0], W[1], "s2"), (N[0], N[1], "n")),
    _s("wcslen", "size_t", (W[0], W[1], "s")),
    _s("wcsnlen", "size_t", (W[0], W[1], "s"), (N[0], N[1], "maxlen")),
    _s("wcscspn", "size_t", (W[0], W[1], "s1"), (W[0], W[1], "s2")),
    _s("wcsspn", "size_t", (W[0], W[1], "s1"), (W[0], W[1], "s2")),
    _s("wcscasecmp", "int", (W[0], W[1], "s1"), (W[0], W[1], "s2")),
    _s("wcsncasecmp", "int", (W[0], W[1], "s1"), (W[0], W[1], "s2"), (N[0], N[1], "n")),
    _s("ffsl", "int", ("long", "integer", "i")),
    _s("ffsll", "int", ("long long", "integer", "i")),
    _s("fls", "int", ("int", "integer", "i")),
    _s("flsl", "int", ("long", "integer", "i")),
    _s("flsll", "int", ("long long", "integer", "i")),
    _s("timingsafe_bcmp", "int", (V[0], V[1], "b1"), (V[0], V[1], "b2"), (N[0], N[1], "len")),
    _s("wcwidth", "int", ("wchar_t", "wide_char", "wc")),
    _s("strlcpy", "size_t", ("char *", "char_buffer", "dst"), (S[0], S[1], "src"), (N[0], N[1], "siz")),
    _s("strlcat", "size_t", ("char *", "char_buffer", "dst"), (S[0], S[1], "src"), (N[0], N[1], "siz")),
    _s("strchr", "char *", (S[0], S[1], "s1"), ("int", "char_code", "i")),
    _s("strrchr", "char *", (S[0], S[1], "s"), ("int", "char_code", "c")),
    _s("strpbrk", "char *", (S[0], S[1], "s1"), (S[0], S[1], "s2")),
    _s("strchrnul", "char *", (S[0], S[1], "s"), ("int", "char_code", "c")),
    _s("memchr", "void *", (V[0], V[1], "src_void"), ("int", "char_code", "c"), (N[0], N[1], "length")),
    _s("memrchr", "void *", (V[0], V[1], "src_void"), ("int", "char_code", "c"), (N[0], N[1], "length")),
    _s("rawmemchr", "void *", (V[0], V[1], "src_void"), ("int", "char_code", "c")),
    _s("strnstr", "char *", (S[0], S[1], "haystack"), (S[0], S[1], "needle"), (N[0], N[1], "haystack_len")),
    _s("memmem", "void *", (V[0], V[1], "haystack"), (N[0], N[1], "hs_len"), (V[0], V[1], "needle"), (N[0], N[1], "ne_len")),
    _s("strstr", "char *", (S[0], S[1], "haystack"), (S[0], S[1], "needle")),
)

TUNING_COUNT = 30


def default_picolibc_root() -> Path:
    return Path("/usr/lib/tinygo/lib/picolibc/newlib/libc/string")


def prepare_source(subject: Subject, root: Path, destination: Path) -> str:
    """Make a host-buildable copy while preserving implementation lines.

    Picolibc private configuration headers are unavailable outside its build
    tree.  Only those includes are removed; standard includes and bodies stay
    intact.  C23 generic-selection macros are undefined for pointer functions.
    """
    source_path = root / f"{subject.name}.c"
    if not source_path.exists():
        raise FileNotFoundError(f"missing Picolibc subject: {source_path}")
    text = source_path.read_text()
    private = re.compile(r'^#include [<"](?:_ansi|picolib|local|reent|newlib|sys/config|sys/cdefs)\.h[>"]\s*$', re.M)
    text = private.sub("", text)
    marker = f"\n#undef {subject.name}\n"
    matches = list(re.finditer(r"^#include .*$", text, re.M))
    if matches:
        at = matches[-1].end()
        text = text[:at] + marker + text[at:]
    else:
        text = "#include <stddef.h>\n#include <string.h>\n#include <wchar.h>\n" + marker + text
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text)
    return text


def subject_by_name(name: str) -> Subject:
    return next(s for s in SUBJECTS if s.name == name)
