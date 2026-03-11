"""
Utility helpers used by the Skabelonmotor API.

This module contains functions responsible for:
1. Normalizing lightweight HTML formatting used in the template engine.
2. Rendering the final letter into PDF or DOCX formats.
3. Normalizing keys for reliable comparisons.
4. Replacing placeholders inside generated letter text.
"""

import re
import io

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from docx import Document
from docx.shared import RGBColor

from bs4 import BeautifulSoup


def normalize_html(text: str) -> str:
    """
    Normalize lightweight HTML formatting so it works with the rendering engines.

    The template system produces simple HTML-like formatting (span, strong, em),
    but ReportLab and python-docx support slightly different tag sets. This
    function converts unsupported tags into equivalents that both renderers
    understand.

    Args:
        text (str): HTML-like formatted text.

    Returns:
        str: Normalized HTML ready for rendering.
    """

    # ReportLab does not support <span style="color:..."> but does support <font>
    text = re.sub(
        r'<span style="color:#([0-9A-Fa-f]{6})">',
        r'<font color="#\1">',
        text
    )

    # Close converted color tags
    text = text.replace("</span>", "</font>")

    # ReportLab expects <b> and <i> rather than <strong> / <em>
    text = text.replace("<strong>", "<b>").replace("</strong>", "</b>")
    text = text.replace("<em>", "<i>").replace("</em>", "</i>")

    return text


def export_letter(text: str, filetype: str = "pdf") -> bytes:
    """
    Convert generated letter text into a file (PDF or DOCX).

    The function first normalizes HTML formatting and then dispatches
    the rendering to the appropriate engine depending on the requested
    output type.

    Args:
        text (str): Generated letter text.
        filetype (str): Output format ("pdf" or "docx").

    Returns:
        bytes: Binary file content ready for download.
    """

    # Normalize formatting before rendering
    text = normalize_html(text)

    # Dispatch rendering depending on requested file type
    if filetype == "pdf":
        return html_to_pdf_bytes(text)

    if filetype == "docx":
        return html_to_docx_bytes(text)

    # Fail early if unsupported type is requested
    raise ValueError("Unsupported file type")


def html_to_pdf_bytes(text: str) -> bytes:
    """
    Render HTML-like text into a PDF document using ReportLab.

    The text is split into paragraphs and rendered as ReportLab
    Paragraph objects. Double line breaks define paragraph boundaries
    while single line breaks are converted into HTML <br/> tags.

    Args:
        text (str): HTML-like formatted letter text.

    Returns:
        bytes: Generated PDF file content.
    """

    styles = getSampleStyleSheet()

    buffer = io.BytesIO()

    # Configure the PDF document layout
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=50,
        rightMargin=50,
        topMargin=50,
        bottomMargin=50,
    )

    story = []

    # Split text into logical paragraphs
    paragraphs = text.split("\n\n")

    for paragraph in paragraphs:

        # ReportLab Paragraph supports limited HTML formatting
        # Convert line breaks inside paragraphs into <br/>
        story.append(
            Paragraph(paragraph.replace("\n", "<br/>"), styles["Normal"])
        )

        # Add vertical spacing between paragraphs
        story.append(Spacer(1, 12))

    # Build the final PDF
    doc.build(story)

    return buffer.getvalue()


def html_to_docx_bytes(text: str) -> bytes:
    """
    Render HTML-like formatted text into a DOCX document.

    The function converts the lightweight HTML produced by the template
    system into a Word document using python-docx. The text is first split
    into paragraphs, after which each paragraph is parsed as HTML and
    traversed node-by-node.

    A nested helper function (`process_node`) is used to recursively walk
    the HTML tree and translate formatting tags into python-docx run
    formatting (bold, italic, underline, strike, color). This recursive
    traversal ensures that nested formatting is preserved correctly.

    Args:
        text (str): HTML-like formatted letter text.

    Returns:
        bytes: Generated DOCX file content.
    """

    soup = BeautifulSoup(text, "html.parser")

    doc = Document()

    def process_node(node, paragraph, formatting=None):
        """
        Recursively process HTML nodes and convert them into DOCX runs.

        This function walks the HTML DOM tree produced by BeautifulSoup.
        As it descends through the tree, it keeps track of the currently
        active formatting (bold, italic, color, etc.) so nested formatting
        is preserved when generating DOCX runs.

        The recursion works like this:

            HTML structure
                ↓
            process_node(node)
                ↓
            update formatting if node is a tag
                ↓
            call process_node(child) for each child

        Args:
            node: BeautifulSoup node (text or HTML element).
            paragraph: python-docx paragraph where runs are inserted.
            formatting (dict | None): Active formatting inherited from
                parent nodes.
        """

        if formatting is None:
            formatting = {}

        # ----------------------------------------
        # TEXT NODE
        # ----------------------------------------
        # If the node has no tag name, it represents plain text
        # inside the HTML structure.
        if node.name is None:

            content = str(node)

            # Skip empty or whitespace-only nodes to avoid
            # generating unnecessary DOCX runs.
            if not content.strip():
                return

            run = paragraph.add_run(content)

            # Apply inherited formatting to the run
            if formatting.get("bold"):
                run.bold = True

            if formatting.get("italic"):
                run.italic = True

            if formatting.get("underline"):
                run.underline = True

            if formatting.get("strike"):
                run.font.strike = True

            # Apply text color if present
            rgb = formatting.get("color")

            if isinstance(rgb, str) and len(rgb) == 6:
                run.font.color.rgb = RGBColor.from_string(rgb)

        else:

            # ----------------------------------------
            # ELEMENT NODE
            # ----------------------------------------
            # When encountering an HTML element (<b>, <span>, etc.)
            # we update the active formatting before processing children.
            # Child nodes inherit this updated formatting.
            new_format = formatting.copy()

            # Update formatting depending on the tag type
            if node.name in ["strong", "b"]:
                new_format["bold"] = True

            if node.name in ["em", "i"]:
                new_format["italic"] = True

            if node.name == "u":
                new_format["underline"] = True

            if node.name == "strike":
                new_format["strike"] = True

            # Extract color from span/font tags
            if node.name in ["span", "font"]:
                match = re.search(r"#([0-9A-Fa-f]{6})", str(node))
                if match:
                    new_format["color"] = match.group(1)

            # Recursively process child nodes so formatting cascades
            for child in node.children:
                process_node(child, paragraph, new_format)

    # ----------------------------------------
    # Build DOCX paragraphs
    # ----------------------------------------
    # Paragraphs in the template engine are separated by double line breaks.
    paragraphs = text.split("\n\n")

    for p in paragraphs:

        paragraph = doc.add_paragraph()

        # Parse paragraph HTML so formatting can be processed node-by-node
        soup = BeautifulSoup(p, "html.parser")

        # Each top-level node inside the paragraph is processed
        for child in soup.children:
            process_node(child, paragraph)

    buffer = io.BytesIO()
    doc.save(buffer)

    return buffer.getvalue()


def normalize_key(value: str) -> str:
    """
    Normalize strings for reliable key comparisons.

    The function removes whitespace, punctuation and converts Danish
    characters so template keys can be matched regardless of formatting
    differences between Excel, API data and placeholders.

    Args:
        value (str): Input string.

    Returns:
        str: Normalized key used for comparisons.
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
    """
    Replace placeholders in the form {key} with values from the data dictionary.

    The function also cleans malformed placeholders that may occur when Excel
    formatting wraps placeholders in HTML tags. Replaced values are wrapped in
    a blue span so inserted data is visually distinguishable in the output.

    Args:
        text (str): Letter text containing placeholders.
        data (dict): Data used to resolve placeholder values.

    Returns:
        str: Text with placeholders replaced.
    """

    # ----------------------------------------
    # Fix malformed placeholders
    # ----------------------------------------
    # Excel rich text formatting can sometimes produce placeholders like:
    # {<span>barnets_fornavn</span>}
    # This regex removes the HTML tags inside the placeholder.
    text = re.sub(
        r"\{<[^>]+>(.*?)</[^>]+>\}",
        r"{\1}",
        text
    )

    def repl(match):

        # Extract placeholder key and clean invisible characters
        key = match.group(1).replace("\u200b", "").strip()

        value = data.get(key)

        # If no value exists, keep the original placeholder
        if value is None:
            return match.group(0)

        # Wrap replacements in a blue color span so inserted values are visually distinguishable in the final document.
        return f'<span style="color:#0F9ED5">{value}</span>'

    # Replace all placeholders of the form {key}
    return re.sub(r"\{([^{}]+)\}", repl, text)
