from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

# PostgreSQL Configuration
POSTGRES_URL = settings.POSTGRES_URL
engine = create_engine(POSTGRES_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# MongoDB Configuration
MONGO_URI = settings.MONGO_URI
mongo_client = AsyncIOMotorClient(MONGO_URI)
mongo_db = mongo_client.get_database()

# Dependency to get PostgreSQL DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency to get MongoDB collection
def get_mongo_collection(collection_name: str):
    return mongo_db[collection_name] 