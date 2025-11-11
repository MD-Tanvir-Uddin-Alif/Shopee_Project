#----------------------------------------
#  lybries
#----------------------------------------
from databse_config import Base, engine, get_db
from fastapi import FastAPI, Depends,HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, UTC
from zoneinfo import ZoneInfo
import time



#----------------------------------------
#  files imported
#----------------------------------------
from models import ProductChildCategoryModel, ProductMainCategoryModel, ProductModel, DeviceModel
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
@app.post('/scrape-categories-wise-product/')
def trigger_category_scrape(db: Session = Depends(get_db)):
    parents = db.query(ProductMainCategoryModel.category_id).all()
    parent_ids = [row[0] for row in parents]

    total_saved = 0
    
    for idx, parent_id in enumerate(parent_ids):
        data = db.query(ProductChildCategoryModel.parent_category_id, ProductChildCategoryModel.category_id).filter(ProductChildCategoryModel.parent_category_id == parent_id).all()
        result = [{"parent_catid": row[0], "catid": row[1]} for row in data]
        
        products = Product_Scrape_by_Category(result)
        
        for prod in products:
            db_product = ProductModel(**prod)
            db.add(db_product)
        db.commit()
        
        total_saved += len(products)
        
        parent = db.query(ProductMainCategoryModel).filter(ProductMainCategoryModel.category_id == parent_id).first()
        if parent:
            parent.scraped_at = datetime.now(ZoneInfo('UTC'))
            db.commit()
        
        if idx < len(parent_ids) - 1:
            time.sleep(180)
    return {'message': f"Saved {total_saved} products to database across all parents"}



#--------------------------------------------------
#  add info to Device Model
#--------------------------------------------------
@app.post('/add-info/{device_namae}/{email}/{password}/{cookies}')
def add_device_info():
    pass