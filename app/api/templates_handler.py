"""API endpoints for letter creation functionalities."""

import json

from fastapi import APIRouter

from mbu_msoffice_integration.sharepoint_class import Sharepoint

from app import config
from app.utils import database, helper_functions

router = APIRouter(prefix="/templates_handler", tags=["Templates handler"])


@router.get("/update_template_data/{process}")
def update_template_data(process: str):
    """
    Build the letter text from block_data and replace placeholders.
    """

    if process == "afgoerelsesbreve":
        sharepoint = Sharepoint(
            site_url="https://aarhuskommune.sharepoint.com/",
            site_name="MBURPA",
            document_library="Delte dokumenter",
            **config.SHAREPOINT_KWARGS,
        )

        folder_name = "Egenbefordring/Afgørelsesbreve"

        template_binary_docx = sharepoint.fetch_file_using_open_binary(
            file_name="skabelon.docx",
            folder_name=folder_name
        )

        binary_excel = sharepoint.fetch_file_using_open_binary(
            file_name="Afgørelsesbreve.xlsm",
            folder_name=folder_name
        )

        json_data = helper_functions.parse_workbook_afgoerelsesbrev(binary_excel=binary_excel)

        query = """
            BEGIN TRANSACTION;

            UPDATE rpa.Templates
            SET
                word_template = :word_template,
                workbook_json = :workbook_json,
                last_updated = SYSDATETIME()
            WHERE process_name = :process_name;

            IF @@ROWCOUNT = 0
            BEGIN
                INSERT INTO rpa.Templates (
                    process_name,
                    word_template,
                    workbook_json
                )
                VALUES (
                    :process_name,
                    :word_template,
                    :workbook_json
                );
            END

            COMMIT;
        """

        params = {
            "process_name": process,
            "word_template": template_binary_docx,
            "workbook_json": json.dumps(json_data),
        }

        rows = database.execute_sql(
            query=query,
            params=params,
            conn_string=database.get_db_connection_string()
        )

        return {"Skabelondata blev succesfuldt opdateret."}

    return {"Der gik noget galt - skabelondata blev ikke opdateret!"}
