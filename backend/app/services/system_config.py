"""系统配置业务逻辑层."""

import datetime
import json
from collections import defaultdict

from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.exceptions import NotFoundException
from app.models.system_config import SystemConfig
from app.schemas.system_config import (
    SystemConfigBatchUpdateDTO,
    SystemConfigGroupVO,
    SystemConfigRespVO,
    SystemConfigUpdateDTO,
)


class DefaultConfigItem(BaseModel):
    """单个默认配置项的定义."""
    key: str = Field(..., description="配置键名")
    value: str = Field(..., description="默认值（字符串形式）")
    value_type: str = Field(default="str", description="值类型: str/int/float/bool/json")
    group: str = Field(default="general", description="配置分组")
    label: str = Field(default="", description="配置项中文名称")
    description: str = Field(default="", description="配置项说明")


# 默认系统配置项（仅保留运行时可配置的业务参数）
DEFAULT_CONFIGS: list[DefaultConfigItem] = [
    DefaultConfigItem(
        key="device_offline_timeout",
        value="30",
        value_type="int",
        group="timeout",
        label="设备离线超时(秒)",
        description="设备心跳超时判定为离线的时间，单位秒",
    ),
    DefaultConfigItem(
        key="alarm_auto_review",
        value="false",
        value_type="bool",
        group="alarm",
        label="报警自动审核",
        description="是否自动审核低风险报警",
    ),
    DefaultConfigItem(
        key="alarm_confidence_threshold",
        value="0.5",
        value_type="float",
        group="alarm",
        label="报警置信度阈值",
        description="低于此置信度的报警不入库",
    ),
    DefaultConfigItem(
        key="max_video_streams",
        value="9",
        value_type="int",
        group="display",
        label="最大视频流数",
        description="视频墙最大同时显示的路数",
    ),
]


class SystemConfigService:
    """系统配置 Service."""

    def __init__(self, session: Session):
        self.session = session

    def init_defaults(self) -> int:
        """初始化默认配置项（仅插入不存在的键）.

        应用启动时调用，返回新插入的配置数。
        """
        inserted = 0
        for item in DEFAULT_CONFIGS:
            existing = self._get_by_key(item.key)
            if not existing:
                config = SystemConfig(**item.model_dump())
                self.session.add(config)
                inserted += 1
        if inserted:
            self.session.commit()
        return inserted

    def get_all(self) -> list[SystemConfigRespVO]:
        """获取所有配置项."""
        stmt = select(SystemConfig).order_by(SystemConfig.group, SystemConfig.key)
        items = list(self.session.exec(stmt).all())
        return [SystemConfigRespVO.model_validate(i) for i in items]

    def get_grouped(self) -> list[SystemConfigGroupVO]:
        """按分组返回配置项."""
        all_configs = self.get_all()
        groups: dict[str, list[SystemConfigRespVO]] = defaultdict(list)
        for cfg in all_configs:
            groups[cfg.group].append(cfg)
        return [
            SystemConfigGroupVO(group=group, items=items)
            for group, items in groups.items()
        ]

    def get_value(self, key: str) -> SystemConfigRespVO:
        """获取单个配置项."""
        config = self._get_by_key(key)
        if not config:
            raise NotFoundException(f"配置项 '{key}' 不存在")
        return SystemConfigRespVO.model_validate(config)

    def update_value(self, key: str, dto: SystemConfigUpdateDTO) -> SystemConfigRespVO:
        """更新单个配置项."""
        config = self._get_by_key(key)
        if not config:
            raise NotFoundException(f"配置项 '{key}' 不存在")

        # 类型校验
        self._validate_value(dto.value, config.value_type)

        config.value = dto.value
        config.updated_at = datetime.datetime.now(datetime.timezone.utc)
        self.session.commit()
        self.session.refresh(config)
        return SystemConfigRespVO.model_validate(config)

    def batch_update(self, dto: SystemConfigBatchUpdateDTO) -> list[SystemConfigRespVO]:
        """批量更新配置项（先全部校验，再统一写入）."""
        # 第一阶段：查找 + 校验，不修改任何值
        to_update: list[tuple[SystemConfig, str]] = []
        for key, value in dto.configs.items():
            config = self._get_by_key(key)
            if not config:
                continue  # 跳过不存在的键
            self._validate_value(value, config.value_type)
            to_update.append((config, value))
        # 第二阶段：全部校验通过后再修改
        now = datetime.datetime.now(datetime.timezone.utc)
        for config, value in to_update:
            config.value = value
            config.updated_at = now
        self.session.commit()
        return [SystemConfigRespVO.model_validate(c) for c, _ in to_update]

    def _get_by_key(self, key: str) -> SystemConfig | None:
        stmt = select(SystemConfig).where(SystemConfig.key == key)
        return self.session.exec(stmt).first()

    def get_typed_value(self, key: str, default=None):
        """获取配置项并自动转换为对应类型（供内部消费代码使用）.

        配置项不存在时返回 default，不抛异常。
        """
        config = self._get_by_key(key)
        if not config:
            return default
        return self._parse_value(config.value, config.value_type)

    @staticmethod
    def _parse_value(value: str, value_type: str):
        """将字符串值转换为对应类型."""
        if value_type == "int":
            return int(value)
        elif value_type == "float":
            return float(value)
        elif value_type == "bool":
            return value.lower() in ("true", "1", "yes")
        elif value_type == "json":
            return json.loads(value)
        return value

    @staticmethod
    def _validate_value(value: str, value_type: str) -> None:
        """校验值是否符合声明的类型."""
        try:
            if value_type == "int":
                int(value)
            elif value_type == "float":
                float(value)
            elif value_type == "bool":
                if value.lower() not in ("true", "false", "1", "0", "yes", "no"):
                    raise ValueError(f"'{value}' 不是有效的布尔值")
            elif value_type == "json":
                json.loads(value)
            # str 不校验
        except (ValueError, TypeError) as e:
            raise ValueError(f"值 '{value}' 不符合类型 '{value_type}': {e}")
