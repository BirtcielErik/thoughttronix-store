"""A console email backend that prints mail the way a reader would see it."""

from django.core.mail.backends.console import EmailBackend


class ReadableConsoleBackend(EmailBackend):
    """Django's console backend, printing headers and the body as written.

    The stock backend prints the raw MIME message. Django encodes any body
    with a line over 78 characters as quoted-printable, which breaks long
    lines with a trailing "=" and turns "=" into "=3D", so a reset or
    confirmation link copied from the terminal would not work. Mail still
    goes only to the terminal.
    """

    def write_message(self, message):
        self.stream.write(f"From: {message.from_email}\n")
        self.stream.write(f"To: {', '.join(message.to)}\n")
        self.stream.write(f"Subject: {message.subject}\n\n")
        self.stream.write(f"{message.body}\n")
        self.stream.write("-" * 79)
        self.stream.write("\n")
