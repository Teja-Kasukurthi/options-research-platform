from fastapi import APIRouter, Depends
from app.api.deps import verify_jwt

router = APIRouter(dependencies=[Depends(verify_jwt)])

# TODO: implement signals endpoints (see ARCHITECTURE.md Section 6)
