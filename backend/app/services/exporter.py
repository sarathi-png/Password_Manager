"""CSV / Excel export of the vault (Chrome-compatible CSV)."""

import csv
import io

from openpyxl import Workbook

from ..crypto import decrypt
from ..models import PasswordEntry

CHROME_HEADERS = ["name", "url", "username", "password", "note"]


def _rows(entries: list[PasswordEntry]) -> list[list[str]]:
    return [
        [
            e.title,
            e.url,
            decrypt(e.username_cipher),
            decrypt(e.password_cipher),
            decrypt(e.notes_cipher),
        ]
        for e in entries
    ]


def export_csv(entries: list[PasswordEntry]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CHROME_HEADERS)
    writer.writerows(_rows(entries))
    return buffer.getvalue().encode("utf-8-sig")


def export_xlsx(entries: list[PasswordEntry]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Passwords"
    ws.append(CHROME_HEADERS)
    for row in _rows(entries):
        ws.append(row)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()