"""用户路由."""

from fastapi import APIRouter, Query

from app.db import SessionDep
from app.schemas.user import LoginDTO, TokenRespVO, UserCreateDTO, UserRespVO
from app.services.user import UserService
from app.utils.security import UserIdDep

router = APIRouter(prefix="", tags=["用户管理"])


@router.post("/users/", response_model=UserRespVO, summary="创建用户")
def create_user(payload: UserCreateDTO, session: SessionDep):
    svc = UserService(session)
    return svc.create_user(payload)


@router.post("/users/login", response_model=TokenRespVO, summary="用户登录")
def login(payload: LoginDTO, session: SessionDep):
    svc = UserService(session)
    return svc.login(payload)


@router.get("/users/me", response_model=UserRespVO, summary="获取当前用户信息")
def get_me(user_id: UserIdDep, session: SessionDep):
    svc = UserService(session)
    return svc.get_user(user_id)


@router.get("/users/", summary="用户列表")
def list_users(
    session: SessionDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    svc = UserService(session)
    return svc.list_users(page=page, page_size=page_size)
