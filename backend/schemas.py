from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

# --- User ---
class UserBase(BaseModel):
    username: str
    role: Optional[str] = "cashier"

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class UserLogin(BaseModel):
    username: str
    password: str

# --- Instrument ---
class InstrumentBase(BaseModel):
    symbol: str
    name: str

class InstrumentCreate(InstrumentBase):
    pass

class InstrumentOut(InstrumentBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# --- Price ---
class PriceOut(BaseModel):
    symbol: str
    buy: Optional[float]
    sell: Optional[float]
    ts: datetime
    model_config = ConfigDict(from_attributes=True)

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
    model_config = ConfigDict(from_attributes=True)

# --- Product ---
class ProductBase(BaseModel):
    name: str
    category: str
    weight: float
    purity: float = 0.916 # Varsayılan 22 Ayar
    labor_cost: float = 0.0
    stock_qty: int = 1

class ProductCreate(ProductBase):
    pass


class ProductOut(ProductBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- Transaction ---
class TransactionBase(BaseModel):
    side: str  # 'buy' veya 'sell'
    qty: float
    unit_price: float
    total_price: Optional[float] = None
    symbol: Optional[str] = None
    customer_id: Optional[int] = None
    product_id: Optional[int] = None
    payment_type: Optional[str] = "Cash" # 'Cash' veya 'Debt'
    net_try: Optional[float] = 0.0 # İşlemden doğan net TL (Borç/Alacak için)


class TransactionCreate(TransactionBase):
    pass

class TransactionOut(TransactionBase):
    id: int
    ts: datetime
    model_config = ConfigDict(from_attributes=True)

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

class ActivationRequest(BaseModel):
    license_key: str