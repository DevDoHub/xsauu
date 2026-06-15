"""用户业务逻辑层."""

import datetime

from sqlmodel import Session, select, func

from app.models.user import User
from app.schemas.user import UserCreateDTO, UserUpdateDTO, LoginDTO, TokenRespVO, UserRespVO
from app.utils.security import hash_password, verify_password, create_access_token
from app.exceptions import NotFoundException, BadRequestException, UnauthorizedException


class UserService:
    """用户 Service."""

    def __init__(self, session: Session):
        self.session = session

    def create_user(self, dto: UserCreateDTO) -> UserRespVO:
        """创建用户."""
        if self._get_by_username(dto.username):
            raise BadRequestException(f"用户名 '{dto.username}' 已存在")

        user = User(
            username=dto.username,
            hashed_password=hash_password(dto.password),
            nickname=dto.nickname,
            role=dto.role,
        )
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return UserRespVO.model_validate(user)

    def login(self, dto: LoginDTO) -> TokenRespVO:
        """用户登录，返回 JWT token."""
        user = self._get_by_username(dto.username)
        if not user or not verify_password(dto.password, user.hashed_password):
            raise UnauthorizedException("用户名或密码错误")
        if not user.is_active:
            raise UnauthorizedException("账号已禁用")

        token = create_access_token(data={"sub": str(user.id)})
        return TokenRespVO(
            access_token=token,
            user=UserRespVO.model_validate(user),
        )

    def get_user(self, user_id: int) -> UserRespVO:
        """获取单个用户."""
        user = self.session.get(User, user_id)
        if not user:
            raise NotFoundException(f"用户 {user_id} 不存在")
        return UserRespVO.model_validate(user)

    def list_users(self, *, page: int = 1, page_size: int = 20) -> dict:
        """分页查询用户."""
        skip = (page - 1) * page_size
        stmt = select(User).offset(skip).limit(page_size)
        users = list(self.session.exec(stmt).all())
        total = self.session.exec(select(func.count()).select_from(User)).one()
        return {
            "total": total,
            "items": [UserRespVO.model_validate(u) for u in users],
            "page": page,
            "page_size": page_size,
        }

    def _get_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username)
        return self.session.exec(stmt).first()
