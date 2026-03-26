"""Module for general configurations of the process"""

import os

# SharePoint stuff
SHAREPOINT_KWARGS = {
    "tenant": os.getenv("TENANT"),
    "client_id": os.getenv("CLIENT_ID"),
    "thumbprint": os.getenv("APPREG_THUMBPRINT"),
    "cert_path": os.getenv("GRAPH_CERT_PEM"),
}
