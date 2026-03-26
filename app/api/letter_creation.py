"""API endpoints for letter creation functionalities."""

from fastapi import APIRouter
from fastapi.responses import Response

from pydantic import BaseModel

from app.utils import helper_functions

router = APIRouter(prefix="/letter_creation", tags=["Letter creation"])


class LetterRequest(BaseModel):
    """
    Class for the letter request - by using a class we can properly assign values from the API requests
    """

    block_data: list
    custom_key_overrides: dict | None = None
    data: dict
    file_type: str
    template_b64: str | None = None


@router.post("/create_letter")
def create_letter(request: LetterRequest):
    """
    Build the letter text from block_data and replace placeholders.
    """

    data = request.data
    blocks = request.block_data
    overrides = request.custom_key_overrides or {}

    file_type = request.file_type.lower()

    template_b64 = request.template_b64

    letter_parts = []

    for block in blocks:
        mapping = block.get("mapping")
        condition = block.get("condition")
        entries = block.get("entries", {})

        # -----------------------------
        # CONDITION: all
        # -----------------------------
        if condition == "all":

            for text in entries.values():

                letter_parts.append(text)

        # -----------------------------
        # CONDITION: has_value
        # -----------------------------
        elif condition == "has_value":

            if mapping and data.get(helper_functions.normalize_key(mapping)):

                text = next(iter(entries.values()), None)

                if text:
                    letter_parts.append(text)

        # -----------------------------
        # CONDITION: custom
        # -----------------------------
        elif condition == "custom":

            if mapping:

                text = entries.get(mapping)

                if text:
                    letter_parts.append(text)

        # -----------------------------
        # CONDITION: equals
        # -----------------------------
        elif condition == "equals":

            normalized_mapping = helper_functions.normalize_key(mapping)

            # 1️⃣ check override first
            key = overrides.get(normalized_mapping)

            # 2️⃣ fallback to data
            if key is None:
                key = data.get(normalized_mapping)

            if key:
                normalized_entries = {
                    helper_functions.normalize_key(k): v
                    for k, v in entries.items()
                }

                # ---------------------------------
                # CASE: multiple keys
                # ---------------------------------
                if isinstance(key, list):

                    for item in key:

                        normalized_item = helper_functions.normalize_key(item)

                        text = normalized_entries.get(normalized_item)

                        if text:
                            letter_parts.append(text)

                # ---------------------------------
                # CASE: single key
                # ---------------------------------
                else:

                    normalized_item = helper_functions.normalize_key(key)

                    text = normalized_entries.get(normalized_item)

                    if text:
                        letter_parts.append(text)

    # ---------------------------------
    # Combine blocks and replace placeholders
    # ---------------------------------
    letter_text = "\n\n".join(letter_parts)
    letter_text = helper_functions.replace_placeholders(letter_text, data)

    text = helper_functions.normalize_html(text=letter_text)

    # Here we check if the request included a docx template
    # If it did, we simply insert the letter_text into that template - if not, we must create the docx from scratch
    if template_b64:
        docx_bytes = helper_functions.insert_letter_into_template(template_b64=template_b64, letter_text=text)

    else:
        docx_bytes = helper_functions.html_to_docx_bytes(text=letter_text)

    file_bytes = None
    media_type = "None"
    file_name = ""

    if file_type == "docx":
        file_bytes = docx_bytes

        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        file_name = "test_letter.docx"

    elif file_type == "pdf":

        file_bytes = helper_functions.convert_docx_to_pdf(docx_bytes)

        media_type = "application/pdf"

        file_name = "test_letter.pdf"

    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": f'inline; filename="{file_name}"'
        }
    )
