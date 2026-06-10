from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import bcrypt
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.db.database import get_db, DBUser
from app.models.user import User, UserLogin, Token, TokenData

router = APIRouter()

# OAuth2 Password Bearer token configuration
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> DBUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=payload.get("role"))
    except JWTError:
        raise credentials_exception
    
    result = await db.execute(select(DBUser).where(DBUser.username == token_data.username))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: DBUser = Depends(get_current_user)) -> DBUser:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def require_roles(*allowed_roles: str):
    if not settings.ENFORCE_RBAC:
        async def bypass_role_check():
            return None

        return bypass_role_check

    async def role_check(current_user: DBUser = Depends(get_current_active_user)) -> DBUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' is not allowed for this action",
            )
        return current_user

    return role_check


@router.post("/register", response_model=User)
async def register_user(user_in: UserLogin, email: str = "default@railmind.gov.in", role: str = "PASSENGER", zone: Optional[str] = "NR", db: AsyncSession = Depends(get_db)):
    # Check if user already exists
    result = await db.execute(select(DBUser).where(DBUser.username == user_in.username))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    password_hash = get_password_hash(user_in.password)
    db_user = DBUser(
        username=user_in.username,
        email=email,
        password_hash=password_hash,
        role=role,
        zone=zone,
        is_active=True
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    return User(
        id=str(db_user.id),
        username=db_user.username,
        email=db_user.email,
        role=db_user.role,
        zone=db_user.zone,
        is_active=db_user.is_active,
        created_at=db_user.created_at,
        updated_at=db_user.created_at
    )


@router.post("/login", response_model=Token)
async def login(user_in: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DBUser).where(DBUser.username == user_in.username))
    user = result.scalars().first()
    if not user or not verify_password(user_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": user.username})
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        zone=user.zone,
        refresh_token=refresh_token
    )


@router.get("/me", response_model=User)
async def read_users_me(current_user: DBUser = Depends(get_current_active_user)):
    return User(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        zone=current_user.zone,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        updated_at=current_user.created_at
    )


@router.get("/operator-performance")
async def get_operator_performance():
    return {
        "handled_alerts_count": 42,
        "variance_score": 98.4,
        "average_reaction_time_seconds": 12.8,
        "safety_compliance_rate": 100.0,
        "authority_status": "L3_SUPERVISOR_ACTIVE",
        "handled_overrides_count": 8,
        "active_duty_hours": 3.5,
        "system_cohesion_index": 95.8,
        "kavach_override_count": 1,
        "last_tamper_check": datetime.now(timezone.utc).isoformat()
    }


from pydantic import BaseModel

class RefreshTokenPayload(BaseModel):
    refresh_token: str

@router.post("/refresh", response_model=Token)
async def refresh_token(payload: RefreshTokenPayload, db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token_payload = jwt.decode(payload.refresh_token, settings.SECRET_KEY, algorithms=["HS256"])
        username: str = token_payload.get("sub")
        if username is None or token_payload.get("type") != "refresh":
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    result = await db.execute(select(DBUser).where(DBUser.username == username))
    user = result.scalars().first()
    if user is None or not user.is_active:
        raise credentials_exception
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    
    new_refresh_token = create_refresh_token(data={"sub": user.username})
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        zone=user.zone,
        refresh_token=new_refresh_token
    )

@router.post("/logout")
async def logout(current_user: DBUser = Depends(get_current_active_user)):
    return {"message": "Successfully logged out"}
