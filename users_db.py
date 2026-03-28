from sqlalchemy import create_engine, Column, Integer, String, Enum
from sqlalchemy.orm import declarative_base

mysql_url = "mysql+pymysql://root:Proys2110%40@localhost:3306/users"

engine = create_engine(mysql_url, echo=True)

Base = declarative_base()


class user_details(Base):
    __tablename__ = 'user_details'

    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    email = Column(String(50))
    password = Column(String(50))
    role = Column(Enum('Client','Admin','Financial Analyst','Auditor'), nullable=False)
    role_id = Column(String(20))

Base.metadata.create_all(engine)


