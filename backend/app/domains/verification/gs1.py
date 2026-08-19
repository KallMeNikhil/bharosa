from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qsl, urlsplit

GTIN_AI = "01"
CPV_AI = "22"
LOT_AI = "10"
SERIAL_AI = "21"

BHAROSA_SERIAL_PARAM = "bhs"

GTIN_LENGTH = 14
MAX_QUALIFIER_LENGTH = 20

PRIMARY_KEY_AIS = frozenset(
    {
        "00",
        "01",
        "253",
        "255",
        "401",
        "402",
        "403",
        "414",
        "415",
        "417",
        "8003",
        "8004",
        "8006",
        "8010",
        "8013",
        "8017",
        "8018",
    }
)

GTIN_QUALIFIER_ORDER = (CPV_AI, LOT_AI, SERIAL_AI)


class MalformedDigitalLinkError(ValueError):
    pass


@dataclass(frozen=True)
class DigitalLinkReference:
    primary_key_ai: str
    primary_key_value: str
    lot: str | None
    gs1_serial: str | None
    bharosa_serial: str | None

    @property
    def gtin(self) -> str | None:
        return self.primary_key_value if self.primary_key_ai == GTIN_AI else None


def gtin_check_digit(digits: str) -> int:
    total = 0
    for position, character in enumerate(reversed(digits)):
        weight = 3 if position % 2 == 0 else 1
        total += int(character) * weight
    return (10 - total % 10) % 10


def is_valid_gtin(value: str) -> bool:
    if len(value) != GTIN_LENGTH or not value.isdigit():
        return False
    return gtin_check_digit(value[:-1]) == int(value[-1])


def _split_path_pairs(path: str) -> list[tuple[str, str]]:
    segments = [segment for segment in path.split("/") if segment]
    start = None
    for index, segment in enumerate(segments[:-1]):
        if segment in PRIMARY_KEY_AIS:
            start = index
            break
    if start is None:
        raise MalformedDigitalLinkError(
            "No GS1 primary identification key was found in the URI path. "
            "Convenience alphas such as /gtin/ were removed from the standard "
            "in Digital Link 1.3.0 and are not accepted."
        )

    tail = segments[start:]
    if len(tail) % 2:
        raise MalformedDigitalLinkError(
            "GS1 Digital Link path segments must form complete "
            "application-identifier/value pairs."
        )
    return [(tail[i], tail[i + 1]) for i in range(0, len(tail), 2)]


def _validate_qualifiers(pairs: list[tuple[str, str]]) -> dict[str, str]:
    qualifiers: dict[str, str] = {}
    last_position = -1
    for ai, value in pairs:
        if ai not in GTIN_QUALIFIER_ORDER:
            raise MalformedDigitalLinkError(
                f"Application identifier {ai!r} is not a valid key qualifier. "
                f"Only {', '.join(GTIN_QUALIFIER_ORDER)} may follow a GTIN, in "
                f"that order."
            )
        position = GTIN_QUALIFIER_ORDER.index(ai)
        if position <= last_position:
            raise MalformedDigitalLinkError(
                "GS1 key qualifiers must appear in the order "
                f"{', '.join(GTIN_QUALIFIER_ORDER)}."
            )
        if not 1 <= len(value) <= MAX_QUALIFIER_LENGTH:
            raise MalformedDigitalLinkError(
                f"Qualifier {ai} value must be 1 to {MAX_QUALIFIER_LENGTH} characters."
            )
        last_position = position
        qualifiers[ai] = value
    return qualifiers


def _extension_parameters(query: str) -> dict[str, str]:
    extensions: dict[str, str] = {}
    for key, value in parse_qsl(query, keep_blank_values=False):
        if key.isdigit():
            continue
        extensions[key] = value
    return extensions


def parse_digital_link(uri: str) -> DigitalLinkReference:
    parts = urlsplit(uri.strip())
    if parts.scheme not in {"http", "https"}:
        raise MalformedDigitalLinkError(
            "A GS1 Digital Link URI must use the https scheme."
        )

    pairs = _split_path_pairs(parts.path)
    primary_ai, primary_value = pairs[0]

    if primary_ai == GTIN_AI and not is_valid_gtin(primary_value):
        raise MalformedDigitalLinkError(
            f"GTIN {primary_value!r} is not 14 digits with a valid check digit."
        )

    qualifiers = _validate_qualifiers(pairs[1:]) if primary_ai == GTIN_AI else {}
    extensions = _extension_parameters(parts.query)

    return DigitalLinkReference(
        primary_key_ai=primary_ai,
        primary_key_value=primary_value,
        lot=qualifiers.get(LOT_AI),
        gs1_serial=qualifiers.get(SERIAL_AI),
        bharosa_serial=extensions.get(BHAROSA_SERIAL_PARAM),
    )


def build_digital_link(
    *,
    host: str,
    gtin: str,
    bharosa_serial: str,
    lot: str | None = None,
    gs1_serial: str | None = None,
) -> str:
    if not is_valid_gtin(gtin):
        raise MalformedDigitalLinkError(
            f"GTIN {gtin!r} is not 14 digits with a valid check digit."
        )

    path = f"/{GTIN_AI}/{gtin}"
    if lot is not None:
        path += f"/{LOT_AI}/{lot}"
    if gs1_serial is not None:
        path += f"/{SERIAL_AI}/{gs1_serial}"
    return f"https://{host}{path}?{BHAROSA_SERIAL_PARAM}={bharosa_serial}"
