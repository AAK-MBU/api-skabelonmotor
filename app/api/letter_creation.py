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

    # block_data is the list of blocks from the template text data
    block_data: list

    # Dictionary of custom key overrides - when looping and replacing template data, placeholders will prioritize this instead of the request data, if present
    custom_key_overrides: dict | None = None

    # Dictionary containing the data that should be used to determine text snippets, placeholders, etc.
    data: dict

    # It's possible to specify the file_type that the skabelonmotor should return - currently only pdf and docx is supported
    file_type: str

    # This attribute allows for including a word template to be used in the letter
    template_b64: str | None = None


@router.post("/create_letter")
def create_letter(request: LetterRequest):
    """
    Build the letter text from block_data and replace placeholders.
    """

    # Retrieve values from the API request
    blocks = request.block_data
    data = request.data
    overrides = request.custom_key_overrides or {}
    file_type = request.file_type.lower()
    template_b64 = request.template_b64

    # Initialize an empty list to contain each formatted and updated text part
    letter_parts = []

    for block in blocks:
        mapping = block.get("mapping")
        condition = block.get("condition")
        entries = block.get("entries", {})

        # -----------------------------
        # CONDITION: all
        # If it's an all condition, we append all the entries for the block
        # -----------------------------
        if condition == "all":
            for text in entries.values():
                letter_parts.append(text)

        # -----------------------------
        # CONDITION: has_value
        # has_value condition simply looks up the mapping_key and sees if there is a value - if there is, we append the single entry for the block
        # -----------------------------
        elif condition == "has_value":
            if mapping and data.get(helper_functions.normalize_key(mapping)):
                text = next(iter(entries.values()), None)

                if text:
                    letter_parts.append(text)

        # -----------------------------
        # CONDITION: custom
        # If it's a custom key, we look for the specified mapping inside the entry keys. We do not lookup the key in the data, but instead use the mapping to look for a key in the entries that matches
        # -----------------------------
        elif condition == "custom":
            if mapping:
                text = entries.get(mapping)

                if text:
                    letter_parts.append(text)

        # -----------------------------
        # CONDITION: equals
        # equals condition is the default - we look for a key that matches in the provided data. Afterwards we use the value from the matched key, to look through the entry keys, for a key that matches the found value 
        # -----------------------------
        elif condition == "equals":
            normalized_mapping = helper_functions.normalize_key(mapping)

            # 1️⃣ check overrides first
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
                # It is possible that the key retrieved through the mapping is a list - if so we loop each value inside the key and append the relevant text entries
                # ---------------------------------
                if isinstance(key, list):
                    for item in key:
                        normalized_item = helper_functions.normalize_key(item)

                        text = normalized_entries.get(normalized_item)

                        if text:
                            letter_parts.append(text)

                # ---------------------------------
                # CASE: single key
                # If the key is a simple value, we look for the matched key insided the block entries and append the entry text if found
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
        # Because we always, by default, create the letter as a Word docx, we must convert it to pdf if necessary
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
