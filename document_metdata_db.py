from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone

mysql_url = "mysql+pymysql://root:Proys2110%40@localhost:3306/users"

engine = create_engine(mysql_url, echo=True)

Base = declarative_base()

class document_metadata(Base):
    __tablename__ = 'document_details'
    id = Column(Integer, primary_key=True)
    title = Column(String(255))
    company_name = Column(String(255))
    document_type = Column(String(255))
    uploaded_by = Column(String(255))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

Base.metadata.create_all(engine)




