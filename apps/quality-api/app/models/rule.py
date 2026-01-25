
from sqlalchemy import Column, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class QualityRule(Base):
    __tablename__ = "quality_rules"
    id = Column(String, primary_key=True)
    asset_id = Column(String, index=True)
    name = Column(String)
    sql_expression = Column(Text)
    threshold = Column(String)
