"""Helper functions"""

import re

import io
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from docx import Document
from docx.shared import RGBColor

from bs4 import BeautifulSoup


def normalize_html(text: str) -> str:

    text = re.sub(
        r'<span style="color:#([0-9A-Fa-f]{6})">',
        r'<font color="#\1">',
        text
    )

    text = text.replace("</span>", "</font>")
    text = text.replace("<strong>", "<b>").replace("</strong>", "</b>")
    text = text.replace("<em>", "<i>").replace("</em>", "</i>")

    return text


def export_letter(text: str, filetype: str = "pdf") -> bytes:

    text = normalize_html(text)

    if filetype == "pdf":
        return html_to_pdf_bytes(text)

    if filetype == "docx":
        return html_to_docx_bytes(text)

    raise ValueError("Unsupported file type")


def html_to_pdf_bytes(text: str) -> bytes:

    styles = getSampleStyleSheet()

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=50,
        rightMargin=50,
        topMargin=50,
        bottomMargin=50,
    )

    story = []

    paragraphs = text.split("\n\n")

    for paragraph in paragraphs:

        story.append(
            Paragraph(paragraph.replace("\n", "<br/>"), styles["Normal"])
        )

        story.append(Spacer(1, 12))

    doc.build(story)

    return buffer.getvalue()


def html_to_docx_bytes(text: str) -> bytes:

    soup = BeautifulSoup(text, "html.parser")

    doc = Document()

    def process_node(node, paragraph, formatting=None):

        if formatting is None:
            formatting = {}

        if node.name is None:

            content = str(node)

            if not content.strip():
                return

            run = paragraph.add_run(content)

            if formatting.get("bold"):
                run.bold = True

            if formatting.get("italic"):
                run.italic = True

            if formatting.get("underline"):
                run.underline = True

            if formatting.get("strike"):
                run.font.strike = True

            rgb = formatting.get("color")

            if isinstance(rgb, str) and len(rgb) == 6:
                run.font.color.rgb = RGBColor.from_string(rgb)

        else:

            new_format = formatting.copy()

            if node.name in ["strong", "b"]:
                new_format["bold"] = True

            if node.name in ["em", "i"]:
                new_format["italic"] = True

            if node.name == "u":
                new_format["underline"] = True

            if node.name == "strike":
                new_format["strike"] = True

            if node.name in ["span", "font"]:
                match = re.search(r"#([0-9A-Fa-f]{6})", str(node))
                if match:
                    new_format["color"] = match.group(1)

            for child in node.children:
                process_node(child, paragraph, new_format)

    # split paragraphs like your PDF logic
    paragraphs = text.split("\n\n")

    for p in paragraphs:

        paragraph = doc.add_paragraph()

        soup = BeautifulSoup(p, "html.parser")

        for child in soup.children:
            process_node(child, paragraph)

    buffer = io.BytesIO()
    doc.save(buffer)

    return buffer.getvalue()


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
    """Replace {placeholders} in text and color replacements blue."""

    # Fix placeholders like {<span>barnets_fornavn</span>}
    text = re.sub(
        r"\{<[^>]+>(.*?)</[^>]+>\}",
        r"{\1}",
        text
    )

    def repl(match):

        key = match.group(1).replace("\u200b", "").strip()

        value = data.get(key)

        if value is None:
            return match.group(0)

        # wrap replacement in blue span
        return f'<span style="color:#0F9ED5">{value}</span>'

    return re.sub(r"\{([^{}]+)\}", repl, text)
