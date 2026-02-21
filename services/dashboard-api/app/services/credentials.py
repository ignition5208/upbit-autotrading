from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import Credential
from app.security.crypto import encrypt_str

def list_credentials(db: Session):
    rows = db.execute(select(Credential).order_by(Credential.created_at.desc())).scalars().all()
    return [{"name": r.name, "created_at": r.created_at.isoformat()} for r in rows]

def create_credential(db: Session, name: str, access_key: str, secret_key: str):
    existing = db.get(Credential, name)
    if existing:
        existing.access_key_enc = encrypt_str(access_key)
        existing.secret_key_enc = encrypt_str(secret_key)
        db.add(existing)
        db.commit()
        return existing
    cred = Credential(name=name, access_key_enc=encrypt_str(access_key), secret_key_enc=encrypt_str(secret_key))
    db.add(cred)
    db.commit()
    return cred

def delete_credential(db: Session, name: str) -> bool:
    obj = db.get(Credential, name)
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True
