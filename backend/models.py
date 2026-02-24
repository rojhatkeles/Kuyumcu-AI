from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(String, default="cashier")  # "admin" or "cashier"

class Margin(Base):
    __tablename__ = "margins"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True)
    buy_margin = Column(Float, default=0.0) # Alışta uygulanacak indirim
    sell_margin = Column(Float, default=0.0) # Satışta uygulanacak kâr

class Instrument(Base):
    __tablename__ = "instruments"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True)
    name = Column(String)

class Price(Base):
    __tablename__ = "prices"
    id = Column(Integer, primary_key=True, index=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"))
    price_type = Column(String)  # "buy" | "sell"
    price = Column(Float)
    ts = Column(DateTime(timezone=True), server_default=func.now())
    instrument = relationship("Instrument")

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    phone = Column(String, unique=True, index=True)
    email = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    balance_try = Column(Float, default=0.0) # Borç/Alacak durumu (TL)
    balance_gold = Column(Float, default=0.0) # Borç/Alacak durumu (Has Altın Gram)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    transactions = relationship("Transaction", back_populates="customer")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category = Column(String) # Künye, Yüzük, vb.
    weight = Column(Float) # Gram
    purity = Column(Float) # Ayar (0.916 - 22k, 0.585 - 14k vb.)
    labor_cost = Column(Float, default=0.0) # İşçilik maliyeti
    stock_qty = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Vault(Base):
    __tablename__ = "vault"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True) # "TRY", "USD", "EUR", "GA"
    balance = Column(Float, default=0.0)
    last_updated = Column(DateTime, onupdate=datetime.now, default=datetime.now)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    side = Column(String)  # "buy" | "sell" | "initial"
    symbol = Column(String, nullable=True) # "GA", "USD" vb.
    qty = Column(Float) # Miktar (Gram veya Adet)
    unit_price = Column(Float)
    total_price = Column(Float)
    payment_type = Column(String, default="Cash")  # Cash, Debt vb.
    net_try = Column(Float, default=0.0) # Borç/Alacak için yansıyan net TL
    ts = Column(DateTime, default=datetime.now)

    
    instrument = relationship("Instrument")
    customer = relationship("Customer", back_populates="transactions")
    product = relationship("Product")

class Config(Base):
    __tablename__ = "configs"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    value = Column(String)