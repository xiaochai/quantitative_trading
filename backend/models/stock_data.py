from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, Text, UniqueConstraint
from backend.database.database import Base

class DailyQuote(Base):
    __tablename__ = "daily_quotes"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String, index=True, nullable=False)
    trade_date = Column(Date, nullable=False)
    
    # 添加唯一键约束，防止重复数据
    __table_args__ = (
        UniqueConstraint('stock_code', 'trade_date', name='uq_stock_trade_date'),
    )
    open = Column(Float)
    close = Column(Float)
    high = Column(Float)
    low = Column(Float)
    volume = Column(Integer)
    amount = Column(Float)
    change_pct = Column(Float)
    change_20d_pct = Column(Float)
    turnover_rate = Column(Float)
    market_cap = Column(Float)
    pe_ttm = Column(Float)
    ma5 = Column(Float)
    ma20 = Column(Float)
    ma60 = Column(Float)
    macd = Column(Float)
    macd_signal = Column(Float)
    macd_hist = Column(Float)
    rsi = Column(Float)
    boll_upper = Column(Float)
    boll_middle = Column(Float)
    boll_lower = Column(Float)

class StockFundamental(Base):
    __tablename__ = "stock_fundamentals"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String, index=True, nullable=False)
    report_date = Column(Date, nullable=False)
    
    # 添加唯一键约束，防止重复数据
    __table_args__ = (
        UniqueConstraint('stock_code', 'report_date', name='uq_stock_report_date'),
    )
    pb = Column(Float)
    roe = Column(Float)
    eps = Column(Float)
    eps_ttm = Column(Float)
    net_profit_growth = Column(Float)
    revenue_growth = Column(Float)
    dividend_yield = Column(Float)

class StockInfo(Base):
    __tablename__ = "stock_info"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String, index=True, nullable=False)
    stock_name = Column(String, nullable=False)
    industry_sw1 = Column(String)
    industry_sw2 = Column(String)
    is_st = Column(Boolean, default=False)
    is_star_st = Column(Boolean, default=False)
    is_delisted = Column(Boolean, default=False)
    delisted_date = Column(Date)
    listed_date = Column(Date)
    component_tags = Column(Text)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date)
    
    # 添加唯一键约束，防止重复数据
    __table_args__ = (
        UniqueConstraint('stock_code', 'effective_from', name='uq_stock_effective_from'),
    )