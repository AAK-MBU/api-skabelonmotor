"""Helper functions"""

import re

from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


def normalize_key(value: str) -> str:
    """
    Docstring for normalize_key

    :param value: Description
    :type value: str
    :return: Description
    :rtype: str
    """

    return (
        value.strip()
        .lower()
        .replace(" ", "")
        .replace(".", "")
        .replace("ø", "oe")
        .replace("å", "aa")
        .replace("æ", "ae")
        .replace("?", "")
        .replace("-", "")
        .replace("_", "")
    )


def replace_placeholders(text: str, data: dict) -> str:
    """Replace {placeholders} in text."""

    placeholders = re.findall(r"\{(.*?)\}", text)

    for key in placeholders:
        value = data.get(key)

        if value is not None:
            text = text.replace(f"{{{key}}}", str(value))

    return text


def text_to_pdf_bytes(text: str) -> bytes:
    """
    Convert text to a properly formatted PDF with wrapping.
    """

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=50,
        rightMargin=50,
        topMargin=50,
        bottomMargin=50,
    )

    styles = getSampleStyleSheet()

    elements = []

    paragraphs = text.split("\n\n")

    for paragraph in paragraphs:

        elements.append(
            Paragraph(paragraph.replace("\n", "<br/>"), styles["Normal"])
        )

        elements.append(Spacer(1, 12))

    doc.build(elements)

    buffer.seek(0)

    return buffer.read()
