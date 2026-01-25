
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class QualityResult(Base):
    __tablename__ = "quality_results"
    id = Column(String, primary_key=True)
    asset_id = Column(String)
    score = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
