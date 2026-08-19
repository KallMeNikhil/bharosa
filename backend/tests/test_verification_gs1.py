import pytest

from app.domains.verification import (
    MalformedDigitalLinkError,
    build_digital_link,
    is_valid_gtin,
    parse_digital_link,
)

GTIN = "09520123456788"
SERIAL = "AAAAAAAAAAAAAAAAAAAAAAAAAA"


def test_valid_gtin_check_digit():
    assert is_valid_gtin(GTIN) is True


def test_invalid_gtin_check_digit_is_rejected():
    assert is_valid_gtin("09520123456789") is False


def test_gtin_shorter_than_fourteen_digits_is_rejected():
    assert is_valid_gtin("9520123456788") is False


def test_parses_gtin_only_path():
    reference = parse_digital_link(f"https://id.bharosa.example/01/{GTIN}")
    assert reference.gtin == GTIN
    assert reference.lot is None
    assert reference.gs1_serial is None


def test_parses_full_qualifier_path_in_mandatory_order():
    reference = parse_digital_link(
        f"https://id.bharosa.example/01/{GTIN}/10/LOT123/21/SER456"
    )
    assert reference.gtin == GTIN
    assert reference.lot == "LOT123"
    assert reference.gs1_serial == "SER456"


def test_qualifiers_out_of_order_are_rejected():
    with pytest.raises(MalformedDigitalLinkError):
        parse_digital_link(f"https://id.bharosa.example/01/{GTIN}/21/SER456/10/LOT123")


def test_path_stem_before_the_primary_key_is_tolerated():
    reference = parse_digital_link(f"https://id.bharosa.example/some/stem/01/{GTIN}")
    assert reference.gtin == GTIN


def test_convenience_alphas_removed_in_digital_link_1_3_are_rejected():
    with pytest.raises(MalformedDigitalLinkError):
        parse_digital_link(f"https://id.bharosa.example/gtin/{GTIN}/ser/{SERIAL}")


def test_missing_primary_key_is_rejected():
    with pytest.raises(MalformedDigitalLinkError):
        parse_digital_link("https://id.bharosa.example/nothing/useful")


def test_non_http_scheme_is_rejected():
    with pytest.raises(MalformedDigitalLinkError):
        parse_digital_link(f"ftp://id.bharosa.example/01/{GTIN}")


def test_bharosa_serial_is_carried_in_a_non_numeric_extension_parameter():
    reference = parse_digital_link(f"https://id.bharosa.example/01/{GTIN}?bhs={SERIAL}")
    assert reference.bharosa_serial == SERIAL


def test_all_numeric_query_keys_are_treated_as_gs1_data_attributes_not_extensions():
    reference = parse_digital_link(
        f"https://id.bharosa.example/01/{GTIN}?17=180426&3103=000195&bhs={SERIAL}"
    )
    assert reference.bharosa_serial == SERIAL


def test_qualifier_longer_than_twenty_characters_is_rejected():
    with pytest.raises(MalformedDigitalLinkError):
        parse_digital_link(f"https://id.bharosa.example/01/{GTIN}/21/{'X' * 21}")


def test_build_digital_link_round_trips():
    uri = build_digital_link(
        host="id.bharosa.example", gtin=GTIN, bharosa_serial=SERIAL, lot="LOT123"
    )
    reference = parse_digital_link(uri)
    assert reference.gtin == GTIN
    assert reference.lot == "LOT123"
    assert reference.bharosa_serial == SERIAL


def test_build_digital_link_rejects_an_invalid_gtin():
    with pytest.raises(MalformedDigitalLinkError):
        build_digital_link(
            host="id.bharosa.example", gtin="09520123456789", bharosa_serial=SERIAL
        )


def test_bharosa_serial_exceeds_the_gs1_serial_component_limit():
    """The frozen 128-bit serial cannot live in AI 21, which caps at 20 characters.

    This is why the serial rides in an extension parameter instead. If this
    assertion ever fails, the serial has been shortened below the entropy floor
    the architecture freezes.
    """
    assert len(SERIAL) > 20
