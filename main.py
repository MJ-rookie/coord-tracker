from fastapi import FastAPI, Request, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import uuid
import os

app = FastAPI()

# 準備資料夾
if not os.path.exists("uploads"):
    os.makedirs("uploads")

# 資料庫設定
DATABASE_URL = "sqlite:///./database.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Location(Base):
    __tablename__ = "locations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    lat = Column(Float)
    lng = Column(Float)
    image_url = Column(String)

Base.metadata.create_all(bind=engine)

# 掛載靜態檔案與模板
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
templates = Jinja2Templates(directory="templates")

# --- 路由開始 ---

@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    # 修正：明確指定參數名稱，避免 unhashable dict 錯誤
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/records")
async def get_records():
    db = SessionLocal()
    try:
        records = db.query(Location).all()
        # 修正：手動轉成字典，避免 SQLAlchemy 物件序列化失敗
        return [{"id": r.id, "name": r.name, "lat": r.lat, "lng": r.lng, "image_url": r.image_url} for r in records]
    finally:
        db.close()

@app.post("/api/save")
async def save_record(
    name: str = Form(...),
    lat: float = Form(...),
    lng: float = Form(...),
    file: UploadFile = File(None)
):
    image_path = ""
    if file and file.filename:
        file_ext = file.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{file_ext}"
        image_path = f"/uploads/{filename}"
        with open(f"uploads/{filename}", "wb") as f:
            content = await file.read()
            f.write(content)

    db = SessionLocal()
    try:
        new_loc = Location(name=name, lat=lat, lng=lng, image_url=image_path)
        db.add(new_loc)
        db.commit()
        return {"status": "success"}
    finally:
        db.close()

@app.delete("/api/delete/{item_id}")
async def delete_record(item_id: int):
    db = SessionLocal()
    try:
        item = db.query(Location).filter(Location.id == item_id).first()
        if item:
            db.delete(item)
            db.commit()
            return {"status": "deleted"}
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)