from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import UserDB
from ..config import settings

router = APIRouter()

@router.get("/postgres")
async def test_postgres(db: Session = Depends(get_db)):
    """Test PostgreSQL connection"""
    try:
        # Try to create a test user
        test_user = UserDB(
            username="test_user",
            email="test@example.com",
            hashed_password="test_password"
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        
        # Clean up
        db.delete(test_user)
        db.commit()
        
        return {
            "status": "success",
            "message": "PostgreSQL connection and operations working correctly",
            "database_url": settings.POSTGRES_URL
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"PostgreSQL test failed: {str(e)}"
        ) 