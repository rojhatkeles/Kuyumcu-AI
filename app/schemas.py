from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# --- Instrument ---
class InstrumentBase(BaseModel):
    symbol: str
    name: str

class InstrumentCreate(InstrumentBase):
    pass

class InstrumentOut(InstrumentBase):
    id: int
    class Config:
        from_attributes = True

# --- Price ---
class PriceOut(BaseModel):
    symbol: str
    buy: Optional[float]
    sell: Optional[float]
    ts: datetime
    class Config:
        from_attributes = True

# --- Customer ---
class CustomerBase(BaseModel):
    full_name: str
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None

class CustomerCreate(CustomerBase):
    pass

class CustomerOut(CustomerBase):
    id: int
    balance_try: float
    balance_gold: float
    created_at: datetime
    class Config:
        from_attributes = True

# --- Product ---
class ProductBase(BaseModel):
    name: str
    category: str
    weight: float
    purity: float
    labor_cost: float = 0.0
    stock_qty: int = 1

class ProductCreate(ProductBase):
    pass

class ProductOut(ProductBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

# --- Transaction ---
class TransactionBase(BaseModel):
    side: str  # 'buy' veya 'sell'
    qty: float
    unit_price: float
    total_price: Optional[float] = None
    symbol: Optional[str] = None
    customer_id: Optional[int] = None
    product_id: Optional[int] = None

class TransactionCreate(TransactionBase):
    pass

class TransactionOut(TransactionBase):
    id: int
    ts: datetime
    class Config:
        from_attributes = True

# --- Conversion ---
class ConvertRequest(BaseModel):
    symbol: str
    amount: float
    side: str

class ConvertResponse(BaseModel):
    symbol: str
    amount: float
    side: str
    result: float
    currency: str = "TRY"