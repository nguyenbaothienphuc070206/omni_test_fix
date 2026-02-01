import bcrypt
import jwt
import datetime
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from models import User
from database import get_db

JWT_ACCESS_SECRET = 'your_access_secret'
JWT_REFRESH_SECRET = 'your_refresh_secret'

async def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12)).decode('utf-8')

async def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

async def create_access_token(data: dict, expires_delta: datetime.timedelta = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
    to_encode.update({'exp': expire})
    return jwt.encode(to_encode, JWT_ACCESS_SECRET, algorithm='HS256')

async def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(days=7)
    to_encode.update({'exp': expire})
    return jwt.encode(to_encode, JWT_REFRESH_SECRET, algorithm='HS256')

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )
    try:
        payload = jwt.decode(token, JWT_ACCESS_SECRET, algorithms=['HS256'])
        user = db.query(User).filter(User.id == payload['userId']).first()
    except jwt.PyJWTError:
        raise credentials_exception
    if user is None:
        raise credentials_exception
    return user

async def register_user(email: str, password: str, db: Session):
    hashed_password = await hash_password(password)
    new_user = User(email=email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

async def login_user(email: str, password: str, db: Session):
    user = db.query(User).filter(User.email == email).first()
    if not user or not await verify_password(password, user.hashed_password):
        raise HTTPException(status_code=400, detail='Incorrect email or password')
    access_token = await create_access_token(data={'userId': user.id, 'email': user.email})
    refresh_token = await create_refresh_token(data={'userId': user.id})
    return {'access_token': access_token, 'refresh_token': refresh_token}

async def refresh_access_token(refresh_token: str):
    credentials_exception = HTTPException(
        status_code=401,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )
    try:
        payload = jwt.decode(refresh_token, JWT_REFRESH_SECRET, algorithms=['HS256'])
        user_id = payload['userId']
    except jwt.PyJWTError:
        raise credentials_exception
    return await create_access_token(data={'userId': user_id})