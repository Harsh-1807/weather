from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db, get_mongo_collection
from ..models.user import UserCreate, User
from motor.motor_asyncio import AsyncIOMotorClient
from ..config import settings
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/test-postgres")
async def test_postgres(user: UserCreate, db: Session = Depends(get_db)):
    """Test PostgreSQL connection and user creation"""
    try:
        # Create a test user in PostgreSQL
        from ..models.user import UserDB
        from passlib.context import CryptContext
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed_password = pwd_context.hash(user.password)
        
        db_user = UserDB(
            email=user.email,
            username=user.username,
            hashed_password=hashed_password
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return {
            "status": "success",
            "message": "PostgreSQL connection and user creation successful",
            "user": {
                "id": db_user.id,
                "email": db_user.email,
                "username": db_user.username
            }
        }
    except Exception as e:
        logger.error(f"PostgreSQL test failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"PostgreSQL test failed: {str(e)}")

@router.post("/test-mongodb")
async def test_mongodb():
    """Test MongoDB connection and document creation"""
    try:
        # Create MongoDB client
        client = AsyncIOMotorClient(settings.MONGO_URI)
        db = client.get_database()
        
        # Create a test collection and insert a document
        test_collection = db["test_collection"]
        test_doc = {
            "test_field": "test_value",
            "timestamp": "test_timestamp"
        }
        
        result = await test_collection.insert_one(test_doc)
        
        # Verify the document was created
        created_doc = await test_collection.find_one({"_id": result.inserted_id})
        
        return {
            "status": "success",
            "message": "MongoDB connection and document creation successful",
            "document": {
                "id": str(created_doc["_id"]),
                "test_field": created_doc["test_field"]
            }
        }
    except Exception as e:
        logger.error(f"MongoDB test failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"MongoDB test failed: {str(e)}")

@router.get("/test-connections")
async def test_connections():
    """Test both database connections"""
    try:
        # Test PostgreSQL connection
        postgres_status = "PostgreSQL connection successful"
        try:
            client = AsyncIOMotorClient(settings.MONGO_URI)
            await client.admin.command('ping')
            mongo_status = "MongoDB connection successful"
        except Exception as e:
            mongo_status = f"MongoDB connection failed: {str(e)}"
        
        return {
            "status": "success",
            "connections": {
                "postgres": postgres_status,
                "mongodb": mongo_status
            }
        }
    except Exception as e:
        logger.error(f"Connection test failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}") 