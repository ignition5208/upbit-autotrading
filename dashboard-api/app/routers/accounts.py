from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..db import get_db
from ..models import Account
from ..crypto_keys import encrypt_keypair, decrypt_keypair
from ..upbit_accounts import test_upbit_keys
from ..events import log_event

router = APIRouter()

class AccountCreateReq(BaseModel):
    name: str
    access_key: str
    secret_key: str
    is_shared: bool = True

@router.get("/accounts")
def list_accounts(db: Session = Depends(get_db)):
    items = db.query(Account).order_by(Account.id.asc()).all()
    return [{"id": a.id, "name": a.name, "is_shared": bool(a.is_shared)} for a in items]

@router.post("/accounts")
def create_account(req: AccountCreateReq, db: Session = Depends(get_db)):
    enc_access, enc_secret = encrypt_keypair(req.access_key, req.secret_key)
    a = Account(name=req.name, access_key=enc_access, secret_key=enc_secret, is_shared=1 if req.is_shared else 0)
    db.add(a); db.commit()
    log_event(db, "INFO", "ACCOUNT_CREATED", f"Account created: {a.name}", None, {"account_id": a.id})
    return {"ok": True, "id": a.id}

@router.post("/accounts/{account_id}/test")
def test_account(account_id: int, db: Session = Depends(get_db)):
    a = db.query(Account).filter(Account.id == account_id).first()
    if not a:
        raise HTTPException(404, "not found")
    access, secret = decrypt_keypair(a.access_key, a.secret_key)
    ok, detail = test_upbit_keys(access, secret)
    if not ok:
        raise HTTPException(400, f"test failed: {detail}")
    return {"ok": True, "detail": detail}
