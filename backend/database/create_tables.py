from backend.database.database import engine, Base
from backend.models.stock_data import DailyQuote, StockFundamental, StockInfo

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("数据库表创建成功")