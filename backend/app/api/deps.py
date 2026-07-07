"""依赖注入"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def create_access_token(subject: str, expires_minutes: Optional[int] = None) -> str:
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": subject, "exp": expire}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(401, "无效凭证", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        raise credentials_exception
    return user


def require_role(*allowed: UserRole):
    """角色拦截：放行 allowed 列表中的角色；ADMIN 始终放行。"""
    allowed_set = {r for r in allowed}

    def _checker(current: User = Depends(get_current_user)) -> User:
        if current.role == UserRole.ADMIN or current.role in allowed_set:
            return current
        raise HTTPException(403, f"权限不足，需要角色：{', '.join(r.value for r in allowed)}")

    return _checker


def require_write(current: User = Depends(get_current_user)) -> User:
    """写操作（创建/修改）：ADMIN、采购员可写。"""
    if current.role in (UserRole.ADMIN, UserRole.PROCUREMENT):
        return current
    raise HTTPException(403, "权限不足，仅采购员或管理员可执行此操作")


def require_approver(current: User = Depends(get_current_user)) -> User:
    """审批操作：ADMIN、审批人可审。"""
    if current.role in (UserRole.ADMIN, UserRole.APPROVER):
        return current
    raise HTTPException(403, "权限不足，仅审批人或管理员可执行此操作")
