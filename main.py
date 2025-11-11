#----------------------------------------
#  lybries
#----------------------------------------
from databse_config import Base, engine, get_db
from fastapi import FastAPI, Depends, status, Body, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, UTC
from zoneinfo import ZoneInfo
import logging
import random
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='device_used.log',
    filemode='a'
)


UTC = ZoneInfo('UTC')
#----------------------------------------
#  files imported
#----------------------------------------
from models import ProductChildCategoryModel, ProductMainCategoryModel, ProductModel, DeviceModel
from schema import DeviceUpdate
from scrape_all_category import Category_Scraper
from category_base_product_scrape import Product_Scrape_by_Category


Base.metadata.create_all(bind=engine)

app = FastAPI()


#----------------------------------------
#  Scraping Category from shopee
#----------------------------------------
@app.post('/scrape-category')
def Category_Scrapa_and_save(db: Session = Depends(get_db)):
    categories = Category_Scraper()
    
    for cat in categories:
        new_cat = ProductChildCategoryModel(
            category_id=cat['catid'],
            name=cat['category_name'],
            parent_category_id=cat['parent_catid']
        )
        db.add(new_cat)
    
    db.commit()
    return {"message": f"Saved {len(categories)} categories to DB!"}



#----------------------------------------
#  get all the parent category 
#----------------------------------------
@app.get('/all/parent-category/')
def get_all_main_category(db: Session=Depends(get_db)):
    categories = db.query(ProductChildCategoryModel).filter(ProductChildCategoryModel.parent_category_id==0).all()
    if not categories:
        return JSONResponse( status_code=status.HTTP_404_NOT_FOUND, content="something went wrong" )
    
    for cat in categories:
        # Check if this category already exists
        existing_parent = db.query(ProductMainCategoryModel).filter(
            ProductMainCategoryModel.category_id == cat.parent_category_id
        ).first()

        if existing_parent:
            # Update the timestamp if already exists
            existing_parent.scraped_at = datetime.now(UTC)
        else:
            # Insert new record
            new_parent = ProductMainCategoryModel(
                category_id=cat.category_id,
                name=cat.name,
                scraped_at=datetime.now(UTC)
            )
            db.add(new_parent)

    db.commit()
    return {"saved parent categories"}



#--------------------------------------------------
#  scrape all data base on parent category
#--------------------------------------------------
# @app.post('/scrape-categories-wise-product/')
# def trigger_category_scrape(db: Session = Depends(get_db)):
#     parents = db.query(ProductMainCategoryModel.category_id).all()
#     parent_ids = [row[0] for row in parents]

#     total_saved = 0
    
#     for idx, parent_id in enumerate(parent_ids):
#         data = db.query(ProductChildCategoryModel.parent_category_id, ProductChildCategoryModel.category_id).filter(ProductChildCategoryModel.parent_category_id == parent_id).all()
#         result = [{"parent_catid": row[0], "catid": row[1]} for row in data]
        
#         products = Product_Scrape_by_Category(result)
        
#         for prod in products:
#             db_product = ProductModel(**prod)
#             db.add(db_product)
#         db.commit()
        
#         total_saved += len(products)
        
#         parent = db.query(ProductMainCategoryModel).filter(ProductMainCategoryModel.category_id == parent_id).first()
#         if parent:
#             parent.scraped_at = datetime.now(ZoneInfo('UTC'))
#             db.commit()
        
#         if idx < len(parent_ids) - 1:
#             time.sleep(180)
#     return {'message': f"Saved {total_saved} products to database across all parents"}



@app.post('/scrape-categories-wise-product/')
def trigger_category_scrape(db: Session = Depends(get_db)):
    parents = db.query(ProductMainCategoryModel.category_id).all()
    parent_ids = [row[0] for row in parents]
    total_saved = 0
   
    for idx, parent_id in enumerate(parent_ids):
        devices = db.query(DeviceModel).filter(
            DeviceModel.is_faild == False
        ).order_by(DeviceModel.status.desc(), DeviceModel.update_time.asc()).all()
        
        if not devices:
            logging.warning(f"No available devices for parent_id {parent_id}. Skipping.")
            continue  
        
        device = devices[0]  # Pick the top one based on ordering
        logging.info(f"Using device {device.id} for parent_id {parent_id}")
        
        data = db.query(ProductChildCategoryModel.parent_category_id, ProductChildCategoryModel.category_id).filter(
            ProductChildCategoryModel.parent_category_id == parent_id
        ).all()
        result = [{"parent_catid": row[0], "catid": row[1]} for row in data]
        num_children = len(result)
        
        try:
            products, success = Product_Scrape_by_Category(result, device.cookies)
            
            for prod in products:
                db_product = ProductModel(**prod)
                db.add(db_product)
            db.commit()
            
            total_saved += len(products)
            
            parent = db.query(ProductMainCategoryModel).filter(
                ProductMainCategoryModel.category_id == parent_id
            ).first()
            if parent:
                parent.scraped_at = datetime.now(UTC)
                db.commit()
            
            if success:
                device.number_of_attemps += (num_children * 2)
                device.status = True
                db.commit()  
            else:
                device.status = False
                device.is_faild = True
                device.failed_time = datetime.now(UTC)
                db.commit()  
            
        except Exception as e:
            logging.error(f"Error scraping parent_id {parent_id} with device {device.id}: {e}")
            device.is_faild = True
            device.status = False
            device.failed_time = datetime.now(UTC)
            db.commit()  
            continue
        
        if idx < len(parent_ids) - 1:
            time.sleep(180)
    
    return {'message': f"Saved {total_saved} products to database across all parents"}


#------------------------------------
# Manually reset a single device
#-------------------------------------
@app.post('/reset-device/{device_id}')
def reset_single_device(device_id: int, db: Session = Depends(get_db)):
    
    device = db.query(DeviceModel).filter(DeviceModel.id == device_id).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    device.is_faild = False
    device.status = False
    device.update_time = datetime.now(UTC)
    db.commit()
    
    return {
        'message': f'Device {device.device_name} reset successfully',
        'device_id': device_id
    }


#---------------------------------------------
# Check device status
#---------------------------------------------
@app.get('/device-status/')
def get_device_status(db: Session = Depends(get_db)):
    """
    Check status of all devices
    """
    devices = db.query(DeviceModel).all()
    
    device_info = []
    for device in devices:
        device_info.append({
            'id': device.id,
            'device_name': device.device_name,
            'email': device.email,
            'attempts': device.number_of_attemps,
            'is_failed': device.is_faild,
            'status': 'In Use' if device.status else 'Available',
            'failed_time': device.failed_time.isoformat() if device.failed_time else None,
            'last_update': device.update_time.isoformat() if device.update_time else None,
        })
    
    available = sum(1 for d in devices if not d.is_faild and not d.status)
    in_use = sum(1 for d in devices if d.status)
    failed = sum(1 for d in devices if d.is_faild)
    
    return {
        'total_devices': len(devices),
        'available': available,
        'in_use': in_use,
        'failed': failed,
        'devices': device_info
    }





#--------------------------------------------------
#  add info to Device Model
#--------------------------------------------------
@app.post('/add-device-info/{device_namae}/')
def add_device_info(device_name: str , email: str, password: str, cookies: dict | list = Body(...), db: Session=Depends(get_db)):
    new_device = DeviceModel(
        device_name=device_name,
        cookies=cookies,
        email=email,
        password=password
    )
    
    db.add(new_device)
    db.commit()
    db.refresh(new_device)
    return {'message':"new device added", 'data':new_device}





#------------------------------------
# Update a single device info
#-------------------------------------
@app.put('/update-device-info/{device_id}/')
def update_device_info(
    device_id: int,
    device_update: DeviceUpdate,  
    db: Session = Depends(get_db)
):
    existing_device = db.query(DeviceModel).filter(DeviceModel.id == device_id).first()
    
    if not existing_device:
        return {'message': "Device not found"}

    for key, value in device_update.dict(exclude_unset=True).items():
        setattr(existing_device, key, value)

    db.commit()
    db.refresh(existing_device)
    
    return {'message': "Updated device info", 'data': existing_device}
