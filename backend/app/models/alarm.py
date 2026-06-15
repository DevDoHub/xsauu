"""SQLModel 数据模型 - 告警."""

import datetime
from typing import Optional
from enum import IntEnum, StrEnum

from sqlmodel import SQLModel, Field


class AlarmSource(StrEnum):
    """告警来源常量，兼容旧项目 alarm_data.db 的 source 列。"""
    FIRE = "fire"   # 视觉告警（火焰 / 烟雾 / 行为等）
    GAS  = "gas"    # 气体浓度告警


class ReviewStatus(IntEnum):
    """复核状态常量。"""
    PENDING = 0    # 未处理
    MISSED = 1     # 误报警
    CONFIRMED = 2  # 确定报警


class AlarmAction(StrEnum):
    """报警控制操作类型。"""
    CLEAR = "clear"
    TRIGGER = "trigger"


class Alarm(SQLModel, table=True):
    """告警表，记录边缘端上报的安全事件."""

    __tablename__ = "alarm"

    id: Optional[int] = Field(default=None, primary_key=True)
    source: AlarmSource = Field(default=AlarmSource.FIRE, index=True, description="告警来源: fire/gas")
    device_id: str = Field(max_length=64, index=True, description="来源设备 ID")
    severity: str = Field(default="warning", max_length=20, description="严重级别: info/warning/critical")
    confidence: float = Field(default=0.0, description="AI 置信度 0-1")
    description: str = Field(default="", max_length=500, description="告警描述（兼容旧数据）")
    note: str = Field(default="", max_length=200, description="报警区域，如: 白龙外场车间")
    type: str = Field(default="", max_length=100, description="事件类型（中文），如: 没有安全帽")
    type2: str = Field(default="", max_length=100, description="事件类别，如: 安全文明着装")
    image_url: Optional[str] = Field(default=None, max_length=500, description="告警截图路径")
    bbox: Optional[str] = Field(default=None, max_length=200, description="检测框坐标 JSON")
    is_reviewed: bool = Field(default=False, description="是否已审核")
    review_status: int = Field(default=0, description="复核状态: 0=未处理, 1=误报警, 2=确定报警")
    reviewed_by: Optional[str] = Field(default=None, max_length=50, description="审核人")
    reviewed_at: Optional[datetime.datetime] = Field(default=None, description="审核时间")
    # 设备/作业快照（写入告警时一次性冻结）
    # ─────────────────────────────────────────────
    # 告警是历史事件，必须保留事发时的完整设备配置；不能因后续 Device
    # 表被"信息编辑"修改而被污染。前端展示历史告警时优先读这些字段，
    # 为空时（迁移前的旧告警）才回退读 Device 表当前值。
    snapshot_device_name: str = Field(
        default="", max_length=100, description="设备名称快照"
    )
    snapshot_device_manager: str = Field(
        default="", max_length=50, description="设备负责人快照"
    )
    snapshot_area_manager: str = Field(
        default="", max_length=50, description="区域负责人快照"
    )
    snapshot_area_manager_phone: str = Field(
        default="", max_length=20, description="区域负责人电话快照"
    )
    snapshot_ip_address: str = Field(
        default="", max_length=45, description="设备 IP 快照"
    )
    snapshot_workshop: str = Field(
        default="", max_length=100, description="车间/作业地点快照"
    )
    snapshot_safety_permit_no: str = Field(
        default="", max_length=50, description="安全许可证号快照"
    )
    snapshot_work_content: str = Field(
        default="", max_length=200, description="作业内容快照"
    )
    snapshot_work_level: str = Field(
        default="", max_length=50, description="作业级别快照"
    )
    snapshot_work_type: str = Field(
        default="", max_length=50, description="作业类型快照"
    )
    snapshot_confined_space: str = Field(
        default="", max_length=10, description="是否受限空间快照"
    )
    snapshot_work_start_time: str = Field(
        default="", max_length=30, description="作业开始时间快照"
    )
    snapshot_work_end_time: str = Field(
        default="", max_length=30, description="作业结束时间快照"
    )
    snapshot_work_status: str = Field(
        default="", max_length=20, description="作业状态快照"
    )
    alarm_time: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))),
        description="报警时间（北京时间）",
    )
