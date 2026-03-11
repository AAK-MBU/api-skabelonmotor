"""API endpoints for Befordring functionalities."""

from typing import Any

from fastapi import APIRouter
from fastapi.responses import Response

from pydantic import BaseModel

from app.utils import helper_functions

router = APIRouter(prefix="/skabelonmotor/api", tags=["Skabelonmotor"])


class LetterRequest(BaseModel):
    """
    Class docstring
    """

    data: dict[str, Any]

    block_data: list[dict[str, Any]]

    custom_key_overrides: dict[str, Any] | None = None

    file_type: str = "pdf"


@router.post("/create_text")
def create_letter_text(request: LetterRequest):
    """
    Build the letter text from block_data and replace placeholders.
    """

    data = request.data
    blocks = request.block_data
    overrides = request.custom_key_overrides or {}

    file_type = request.file_type.lower()

    letter_parts = []

    for block in blocks:
        block_id = block.get("block_id")
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

    # export
    file_bytes = helper_functions.export_letter(letter_text, filetype=file_type)

    if file_type == "docx":
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        file_name = "brev.docx"

    else:
        media_type = "application/pdf"
        file_name = "brev.pdf"

    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": f'inline; filename="{file_name}"'
        }
    )
