from fastapi import APIRouter, Depends
from app.api.deps import verify_jwt

router = APIRouter(dependencies=[Depends(verify_jwt)])

# TODO: implement paper endpoints (see ARCHITECTURE.md Section 6)
