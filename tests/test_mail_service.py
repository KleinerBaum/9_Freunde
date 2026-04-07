from __future__ import annotations

from email import message_from_bytes

import pytest

from services import mail_service
from services.mail_service import MailServiceError, build_parent_recipient_list


class _FakeSendCall:
    def __init__(self, *, should_fail: bool = False, message_id: str = "msg-1") -> None:
        self.should_fail = should_fail
        self.message_id = message_id
        self.last_body: dict[str, str] | None = None

    def execute(self) -> dict[str, str]:
        if self.should_fail:
            raise MailServiceError("send failed", cause="api_error")
        return {"id": self.message_id}


class _FakeMessagesResource:
    def __init__(self, *, should_fail: bool = False, message_id: str = "msg-1") -> None:
        self.should_fail = should_fail
        self.message_id = message_id
        self.last_body: dict[str, str] | None = None

    def send(self, *, userId: str, body: dict[str, str]) -> _FakeSendCall:  # noqa: N803
        assert userId == "me"
        self.last_body = body
        return _FakeSendCall(should_fail=self.should_fail, message_id=self.message_id)


class _FakeUsersResource:
    def __init__(self, messages: _FakeMessagesResource) -> None:
        self._messages = messages

    def messages(self) -> _FakeMessagesResource:
        return self._messages


class _FakeGmailClient:
    def __init__(self, messages: _FakeMessagesResource) -> None:
        self._messages = messages

    def users(self) -> _FakeUsersResource:
        return _FakeUsersResource(self._messages)


def _decode_raw_message(raw_value: str):
    import base64

    decoded = base64.urlsafe_b64decode(raw_value.encode("utf-8"))
    return message_from_bytes(decoded)


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


def test_send_message_normalizes_recipient_and_serializes_mime(monkeypatch) -> None:
    fake_messages = _FakeMessagesResource(message_id="gmail-42")
    monkeypatch.setattr(
        mail_service,
        "_get_gmail_client",
        lambda: _FakeGmailClient(fake_messages),
    )

    message_id = mail_service.send_message(
        recipient_email=" Parent@Example.org ",
        subject="  Elternbrief  ",
        body_text=" Hallo! ",
    )

    assert message_id == "gmail-42"
    assert fake_messages.last_body is not None
    parsed_message = _decode_raw_message(fake_messages.last_body["raw"])
    assert parsed_message["to"] == "parent@example.org"
    assert parsed_message["subject"] == "Elternbrief"


def test_send_bulk_message_counts_success_and_failure(monkeypatch) -> None:
    call_log: list[str] = []

    def _fake_send_message(
        *, recipient_email: str, subject: str, body_text: str
    ) -> str:
        del subject, body_text
        call_log.append(recipient_email)
        if recipient_email == "b@example.org":
            raise MailServiceError("failed", cause="api_error")
        return f"id-{recipient_email}"

    monkeypatch.setattr(mail_service, "send_message", _fake_send_message)

    result = mail_service.send_bulk_message(
        recipient_emails=["a@example.org", " b@example.org ", "a@example.org"],
        subject="Update",
        body_text="Text",
    )

    assert result == {"success_count": 1, "failure_count": 1}
    assert call_log == ["a@example.org", "b@example.org"]


def test_send_bulk_message_raises_when_everything_fails(monkeypatch) -> None:
    def _always_fail(*, recipient_email: str, subject: str, body_text: str) -> str:
        del recipient_email, subject, body_text
        raise MailServiceError("always fail", cause="api_error")

    monkeypatch.setattr(mail_service, "send_message", _always_fail)

    with pytest.raises(MailServiceError) as exc_info:
        mail_service.send_bulk_message(
            recipient_emails=["a@example.org"],
            subject="Update",
            body_text="Text",
        )

    assert exc_info.value.cause == "bulk_failed"
