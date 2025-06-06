from sqlalchemy.orm import Session
from app.models.parse import ParseHistory
import datetime 


def create_parse_history(db: Session, user_id: int, url: str, max_depth: int):
    db_history = ParseHistory(
        user_id=user_id,
        url=url,
        max_depth=max_depth
    )
    db.add(db_history)
    db.commit()
    db.refresh(db_history)
    return db_history

def update_parse_history(
    db: Session, 
    history_id: int, 
    status: str, 
    result_path: str = None
):
    db_history = db.query(ParseHistory).filter(ParseHistory.id == history_id).first()
    if db_history:
        db_history.status = status
        if status == "COMPLETED":
            db_history.completed_at = datetime.utcnow()
        if result_path:
            db_history.result_path = result_path
        db.commit()
        db.refresh(db_history)
    return db_history

def get_parse_history_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(ParseHistory).filter(ParseHistory.user_id == user_id).offset(skip).limit(limit).all()