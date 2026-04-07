from __future__ import annotations

from services.mail_service import build_parent_recipient_list


def test_build_parent_recipient_list_all_parents_filters_opt_in() -> None:
    recipients = build_parent_recipient_list(
        children=[
            {"id": "c1", "parent_email": "a@example.org", "group": "Rot"},
            {"id": "c2", "parent_email": "b@example.org", "group": "Blau"},
        ],
        parents=[
            {"email": "a@example.org", "notifications_opt_in": "true"},
            {"email": "b@example.org", "notifications_opt_in": "false"},
        ],
        audience="all_parents",
    )

    assert recipients == ["a@example.org"]


def test_build_parent_recipient_list_group_and_single_child() -> None:
    children = [
        {"id": "c1", "parent_email": "a@example.org", "group": "Rot"},
        {"id": "c2", "parent_email": "b@example.org", "group": "Blau"},
    ]
    parents = [
        {"email": "a@example.org", "notifications_opt_in": "true"},
        {"email": "b@example.org", "notifications_opt_in": "true"},
    ]

    recipients_group = build_parent_recipient_list(
        children=children,
        parents=parents,
        audience="group",
        selected_group="Rot",
    )
    recipients_child = build_parent_recipient_list(
        children=children,
        parents=parents,
        audience="single_child",
        selected_child_id="c2",
    )

    assert recipients_group == ["a@example.org"]
    assert recipients_child == ["b@example.org"]
