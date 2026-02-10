from __future__ import annotations

from services import sheets_repo
import stammdaten


def test_sync_child_parent_email_uses_parent1_email() -> None:
    payload = {"parent_email": "old@example.com", "parent1__email": "new@example.com"}

    sheets_repo._sync_child_parent_email(payload)

    assert payload["parent_email"] == "new@example.com"


def test_derive_download_consent_prioritizes_denied() -> None:
    payload = {
        "download_consent": "unpixelated",
        "consent__photo_download_pixelated": "true",
        "consent__photo_download_unpixelated": "true",
        "consent__photo_download_denied": "true",
    }

    assert sheets_repo._derive_download_consent(payload) == "denied"


def test_derive_download_consent_uses_unpixelated_before_pixelated() -> None:
    payload = {
        "download_consent": "pixelated",
        "consent__photo_download_pixelated": "true",
        "consent__photo_download_unpixelated": "true",
        "consent__photo_download_denied": "false",
    }

    assert sheets_repo._derive_download_consent(payload) == "unpixelated"


def test_normalize_download_consent_accepts_denied() -> None:
    child = {"child_id": "abc", "download_consent": "DENIED"}

    normalized = stammdaten._normalize_child_record(child)

    assert normalized["download_consent"] == "denied"


def test_map_schema_v1_payload_to_tab_records_maps_children_and_parents() -> None:
    payload = {
        "meta__record_id": "child-42",
        "child__name": "Lina",
        "child__birthdate": "2021-03-01",
        "child__status": "active",
        "parent_email": "fallback@example.com",
        "parent1__email": "p1@example.com",
        "parent1__name": "Parent One",
        "parent1__notifications_opt_in": "ja",
        "parent2__email": "p2@example.com",
        "parent2__name": "Parent Two",
        "parent2__notifications_opt_in": "0",
        "consent__photo_download_pixelated": "true",
    }

    mapped = sheets_repo.map_schema_v1_payload_to_tab_records(payload)

    assert mapped["children"]["child_id"] == "child-42"
    assert mapped["children"]["name"] == "Lina"
    assert mapped["children"]["parent_email"] == "p1@example.com"
    assert mapped["children"]["download_consent"] == "pixelated"

    assert mapped["parents"][0]["email"] == "p1@example.com"
    assert mapped["parents"][0]["notifications_opt_in"] == "true"
    assert mapped["parents"][1]["email"] == "p2@example.com"
    assert mapped["parents"][1]["notifications_opt_in"] == "false"


def test_map_schema_v1_payload_to_tab_records_uses_child_id_argument_as_fallback() -> (
    None
):
    mapped = sheets_repo.map_schema_v1_payload_to_tab_records(
        {"child__name": "No Meta"},
        child_id="fallback-id",
    )

    assert mapped["children"]["child_id"] == "fallback-id"


def test_map_schema_v1_payload_to_tab_records_serializes_pa1_to_pa4_in_order() -> None:
    payload = {
        "meta__record_id": "child-99",
        "pa1__name": "Grandma",
        "pa1__relationship": "grandparent",
        "pa1__active": "",
        "pa2__name": "Neighbor",
        "pa2__phone": "12345",
        "pa2__active": "false",
        "pa4__name": "Uncle",
        "pa4__created_by": "admin@example.com",
        "pa4__active": "x",
    }

    mapped = sheets_repo.map_schema_v1_payload_to_tab_records(payload)

    pickup = mapped["pickup_authorizations"]
    assert [entry["name"] for entry in pickup] == ["Grandma", "Neighbor", "Uncle"]
    assert pickup[0]["child_id"] == "child-99"
    assert pickup[0]["active"] == "true"
    assert pickup[1]["active"] == "true"
    assert pickup[2]["active"] == "true"


def test_map_schema_v1_payload_to_tab_records_maps_consents_sign_and_meta() -> None:
    payload = {
        "meta__record_id": "child-7",
        "consent__privacy_notice_ack": "yes",
        "consent__excursions": "no",
        "consent__emergency_treatment": "1",
        "consent__whatsapp_group": "0",
        "sign__parent1_name": "Signer One",
        "sign__parent2_date": "2025-01-15",
        "meta__updated_at": "2025-01-16T10:15:00Z",
    }

    mapped = sheets_repo.map_schema_v1_payload_to_tab_records(payload)

    records = {
        record["consent_type"]: record["status"] for record in mapped["consents"]
    }
    assert records["consent__privacy_notice_ack"] == "true"
    assert records["consent__excursions"] == "no"
    assert records["consent__emergency_treatment"] == "true"
    assert records["consent__whatsapp_group"] == "0"
    assert records["sign__parent1_name"] == "Signer One"
    assert records["sign__parent2_date"] == "2025-01-15"
    assert records["meta__updated_at"] == "2025-01-16T10:15:00Z"
    assert all(record["child_id"] == "child-7" for record in mapped["consents"])
