
from sqlalchemy import Column as SAColumn, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Column(Base):
    __tablename__ = "columns"
    id = SAColumn(String, primary_key=True)
    asset_id = SAColumn(String, ForeignKey("assets.id"))
    name = SAColumn(String)
    data_type = SAColumn(String)
