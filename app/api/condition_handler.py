"""API endpoints for Befordring functionalities."""

from fastapi import APIRouter


router = APIRouter(prefix="/skabelonmotor/api/", tags=["Skabelonmotor"])


@router.get("/check_condition")
def check_condition():
    """
    Retrieve a child's distance to school based on their CPR number.
    Distance return is in kilometers.
    """

    return
