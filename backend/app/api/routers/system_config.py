"""系统配置路由."""

from fastapi import APIRouter

from app.db import SessionDep
from app.schemas.system_config import (
    SystemConfigBatchUpdateDTO,
    SystemConfigGroupVO,
    SystemConfigRespVO,
    SystemConfigUpdateDTO,
)
from app.services.system_config import SystemConfigService

router = APIRouter(prefix="", tags=["系统配置"])


@router.get("/system/config", summary="获取所有系统配置")
def get_all_configs(session: SessionDep) -> list[SystemConfigRespVO]:
    """返回所有系统配置项."""
    svc = SystemConfigService(session)
    return svc.get_all()


@router.get("/system/config/grouped", summary="按分组获取系统配置")
def get_grouped_configs(session: SessionDep) -> list[SystemConfigGroupVO]:
    """按分组返回系统配置项，便于前端分类展示."""
    svc = SystemConfigService(session)
    return svc.get_grouped()


@router.get("/system/config/{key}", summary="获取单个配置项")
def get_config(key: str, session: SessionDep):
    """获取指定配置项的详细信息."""
    svc = SystemConfigService(session)
    config = svc.get_value(key)
    return config


@router.put("/system/config/{key}", summary="更新单个配置项")
def update_config(key: str, payload: SystemConfigUpdateDTO, session: SessionDep):
    """更新指定配置项的值."""
    svc = SystemConfigService(session)
    config = svc.update_value(key, payload)
    return {"status": "ok", "config": config}


@router.put("/system/config", summary="批量更新配置项")
def batch_update_configs(payload: SystemConfigBatchUpdateDTO, session: SessionDep):
    """批量更新多个配置项.

    请求体: {"configs": {"key1": "value1", "key2": "value2"}}
    """
    svc = SystemConfigService(session)
    updated = svc.batch_update(payload)
    return {"status": "ok", "updated_count": len(updated), "configs": updated}


# ── 旧前端兼容路径 ──────────────────────────────────────────────────────────

@router.get("/system/config_legacy", summary="获取系统配置（旧前端兼容）")
def get_system_config_compat(session: SessionDep):
    """兼容旧前端的 /system_config GET 路径."""
    svc = SystemConfigService(session)
    return svc.get_grouped()


@router.post("/system/config_legacy", summary="更新系统配置（旧前端兼容）")
def update_system_config_compat(session: SessionDep, payload: dict):
    """兼容旧前端的 /system_config POST 路径."""
    svc = SystemConfigService(session)
    dto = SystemConfigBatchUpdateDTO.model_validate(payload)
    return svc.batch_update(dto)
