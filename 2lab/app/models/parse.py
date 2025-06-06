from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime

class ParseHistory(Base):
    __tablename__ = "parse_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    url = Column(String, nullable=False)
    max_depth = Column(Integer, default=2)
    status = Column(String, default="PENDING")
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    result_path = Column(String, nullable=True)
    
    user = relationship("User", back_populates="parse_history")