from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.db import get_db
from app.services.credentials import (
    create_credential,
    list_credentials,
    delete_credential,
    decrypt_credential,
)

router = APIRouter()

class CredentialCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    access_key: str = Field(..., min_length=5)
    secret_key: str = Field(..., min_length=5)

@router.get("/credentials")
def get_credentials(db: Session = Depends(get_db)):
    return {"items": list_credentials(db)}

@router.post("/credentials")
def post_credentials(req: CredentialCreate, db: Session = Depends(get_db)):
    try:
        cred = create_credential(db, name=req.name, access_key=req.access_key, secret_key=req.secret_key)
        return {"created": True, "name": cred.name}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/credentials/{name}")
def del_credential(name: str, db: Session = Depends(get_db)):
    ok = delete_credential(db, name)
    return {"deleted": ok}


@router.get("/credentials/{name}/decrypt")
def get_credential_decrypt(name: str, db: Session = Depends(get_db)):
    try:
        cred = decrypt_credential(db, name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="credential decrypt failed")
    if not cred:
        raise HTTPException(status_code=404, detail="credential not found")
    return cred
