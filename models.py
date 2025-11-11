from sqlalchemy import Integer, String, Column, Boolean, DateTime, BigInteger, Float, JSON
from databse_config import Base
from datetime import datetime, UTC, timezone


#--------------------------------------------------
#  Child Category Model Schema
#--------------------------------------------------
class ProductChildCategoryModel(Base):
    
    __tablename__ = 'Product_Child_Categories'
    
    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer)
    name = Column(String)
    parent_category_id = Column(Integer)
    status = Column(Boolean, default=False)




#--------------------------------------------------
#  Parent Category Model Schema
#--------------------------------------------------
class ProductMainCategoryModel(Base):
    
    __tablename__ = 'Product_Main_Categories'
    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer)
    name = Column(String)
    scraped_at = Column(DateTime(timezone=True), default=datetime.now(UTC), onupdate=datetime.now(UTC))
    status = Column(Boolean, default=False)




#--------------------------------------------------
#  Product Model Schema
#--------------------------------------------------
class ProductModel(Base):
    
    __tablename__ = 'Products'
    
    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(BigInteger)
    shop_id = Column(BigInteger)
    parent_category_id = Column(Integer)
    child_category_id = Column(Integer)
    name = Column(String)
    image = Column(String)
    price = Column(Float)
    price_before_discount = Column(Float)
    raw_discount = Column(Integer)
    discount_percentage = Column(String)
    sold = Column(Integer)
    historical_sold = Column(Integer)
    shop_name = Column(String)
    rating_star = Column(Float)
    rating_count = Column(Integer)
    shop_location = Column(String)
    stock = Column(Integer)




#--------------------------------------------------
#  Device Model Schema
#--------------------------------------------------
class DeviceModel(Base):
    
    __tablename__ = 'Device'
    
    id = Column(Integer, primary_key=True, index=True)
    device_name = Column(String)
    email = Column(String)
    password = Column(String)
    cookies = Column(JSON)
    number_of_attemps = Column(Integer, default=0)
    is_faild = Column(Boolean, default=False)
    failed_time = Column(DateTime(timezone=True), default=datetime.now(UTC), onupdate=datetime.now(UTC))
    update_time = Column(DateTime(timezone=True), default=datetime.now(UTC), onupdate=datetime.now(UTC))
    status = Column(Boolean, default=False)