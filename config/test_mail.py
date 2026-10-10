"""The readable console email backend."""

import io

from django.core.mail import EmailMessage

from config.mail import ReadableConsoleBackend

LINK = "http://127.0.0.1:8000/accounts/password-reset/MQ/" + "a1b2c3d4" * 8 + "/?x=1"


def write(body):
    stream = io.StringIO()
    message = EmailMessage(
        "Reset your password",
        body,
        "ThoughtTronix <no-reply@thoughttronix.example>",
        ["erik@example.com"],
    )
    ReadableConsoleBackend(stream=stream).send_messages([message])
    return stream.getvalue()


def test_prints_the_headers():
    output = write("Hello")

    assert "From: ThoughtTronix <no-reply@thoughttronix.example>\n" in output
    assert "To: erik@example.com\n" in output
    assert "Subject: Reset your password\n" in output


def test_prints_a_long_link_unbroken_and_unescaped():
    assert len(LINK) > 78  # long enough that Django would quoted-print it

    output = write(f"Open this link:\n{LINK}\n")

    assert LINK in output
    assert "=3D" not in output
