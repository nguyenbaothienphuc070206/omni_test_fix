from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, validator
import logging

from toolkit.crypto import hash_password

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class UserCreate(BaseModel):
    email: str
    password: str

    @validator('email')
    def email_sanity(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email')
        return v
    
    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

app = FastAPI()

@app.post('/users')
async def create_user(user: UserCreate):
    hashed_password = hash_password(user.password)
    logger.info(f'User created: {user.email}')
    return {'email': user.email, 'hashed_password': hashed_password}

@app.get('/users')
async def get_users():
    return {'users': []}