from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.abspath(os.path.join(BASE_DIR, "../..", "quantitative_trading.db"))

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    db_path = os.getenv("QUANT_DB_PATH") or DEFAULT_DB_PATH
    db_path = os.path.abspath(db_path)
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    print("获取数据库连接", SQLALCHEMY_DATABASE_URL)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """初始化数据库表"""
    from models.stock_data import DailyQuote, IndexDailyQuote, StockInfo, StockFundamental
    Base.metadata.create_all(bind=engine)
    print("数据库表初始化完成")
