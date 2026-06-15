"""Pydantic Schema - 设备相关请求/响应."""

from enum import StrEnum

from pydantic import BaseModel, Field
from typing import Optional

from app.schemas.common import PaginatedResponse


# ── 枚举 ──────────────────────────────────────────────────────────────────────


class DeviceStatus(StrEnum):
    """设备状态枚举."""
    ACTIVE = "active"
    DISABLED = "disabled"
    MAINTENANCE = "maintenance"


class CameraDirection(StrEnum):
    """摄像头方向控制枚举."""
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    STOP = "stop"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    AUTO = "auto"
    RECONNECT = "reconnect"
    DISCONNECT = "disconnect"


class DetectionAction(StrEnum):
    """检测控制动作枚举."""
    START = "start"
    STOP = "stop"


# ── 请求 DTO ─────────────────────────────────────────────────────────────────


class DeviceCreateDTO(BaseModel):
    """注册设备."""
    device_id: str = Field(..., max_length=64, description="设备唯一标识")
    name: str = Field(..., max_length=100, description="设备名称")
    location: str = Field(default="", max_length=200, description="安装位置")
    ip_address: str = Field(default="", max_length=45, description="设备 IP 地址")
    camera_url: str = Field(default="", max_length=500, description="RTSP 地址")
    mediamtx_path: str = Field(default="", max_length=100, description="MediaMTX 视频路径名（为空时自动使用 device_id）")
    camera_rotation: int = Field(default=0, description="摄像头旋转角度（0=正常, 180=倒装）")
    responsible_person: str = Field(default="", max_length=50, description="设备负责人")
    area_manager: str = Field(default="", max_length=50, description="区域负责人")
    area_manager_phone: str = Field(default="", max_length=20, description="区域负责人电话")
    workshop: str = Field(default="", max_length=100, description="车间")


class DeviceUpdateDTO(BaseModel):
    """更新设备."""
    name: str | None = Field(default=None, description="设备名称")
    location: str | None = Field(default=None, description="安装位置")
    ip_address: str | None = Field(default=None, description="设备 IP 地址")
    camera_url: str | None = Field(default=None, description="RTSP 地址")
    mediamtx_path: str | None = Field(default=None, description="MediaMTX 视频路径名")
    camera_rotation: int | None = Field(default=None, description="摄像头旋转角度")
    status: DeviceStatus | None = Field(default=None, description="设备状态")
    responsible_person: str | None = Field(default=None, description="设备负责人")
    area_manager: str | None = Field(default=None, description="区域负责人")
    area_manager_phone: str | None = Field(default=None, description="区域负责人电话")
    workshop: str | None = Field(default=None, description="车间")
    safety_permit_no: str | None = Field(default=None, description="安全许可证号")
    work_content: str | None = Field(default=None, description="作业内容")
    work_level: str | None = Field(default=None, description="作业等级")
    work_type: str | None = Field(default=None, description="作业类型")
    confined_space: str | None = Field(default=None, description="是否受限空间")
    work_start_time: str | None = Field(default=None, description="作业开始时间")
    work_end_time: str | None = Field(default=None, description="作业结束时间")
    work_status: str | None = Field(default=None, description="作业状态")


class CameraControlDTO(BaseModel):
    """摄像头控制命令."""
    direction: CameraDirection = Field(..., description="方向: up/down/left/right/stop/zoom_in/zoom_out/auto/reconnect/disconnect")


class DetectionControlDTO(BaseModel):
    """检测控制命令."""
    action: DetectionAction = Field(..., description="动作: start/stop")


class DeviceRespVO(BaseModel):
    """设备信息响应."""
    id: int
    device_id: str
    deviceNumber: str = Field(default="", description="设备编号（兼容旧前端，等于 device_id）")
    name: str
    location: str
    ip_address: str
    camera_url: str
    mediamtx_path: str
    camera_rotation: int = Field(default=0, description="摄像头旋转角度")
    is_online: bool
    online_since: str | None = Field(default=None, description="本次上线时间（ISO 8601）")
    total_runtime_seconds: int = Field(default=0, description="累计在线秒数")
    last_heartbeat: str | None = Field(default=None, description="最后心跳时间（ISO 8601）")
    status: str
    responsible_person: str
    area_manager: str
    area_manager_phone: str
    workshop: str
    safety_permit_no: str = Field(default="", description="安全许可证号")
    work_content: str = Field(default="", description="作业内容")
    work_level: str = Field(default="", description="作业等级")
    work_type: str = Field(default="", description="作业类型")
    confined_space: str = Field(default="", description="是否受限空间")
    work_start_time: str = Field(default="", description="作业开始时间")
    work_end_time: str = Field(default="", description="作业结束时间")
    work_status: str = Field(default="", description="作业状态")
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class DeviceListRespVO(PaginatedResponse[DeviceRespVO]):
    """设备列表分页响应."""
    pass


class DeviceGroupedByPersonVO(BaseModel):
    """按负责人分组的设备响应."""
    data: dict[str, list[DeviceRespVO]] = Field(description="负责人→设备列表映射")


class DeviceGroupedByAreaVO(BaseModel):
    """按区域负责人二级分组的设备响应.

    兼容旧前端 /search_device_by_device_manager 的二级结构：
    { "区域负责人": { "设备名": DeviceRespVO } }
    """
    data: dict[str, dict[str, DeviceRespVO]] = Field(description="区域负责人→设备名→设备信息映射")


class DeviceCountRespVO(BaseModel):
    """设备统计响应."""
    total: int = Field(description="设备总数")
    online: int = Field(description="在线设备数")


class DeviceConfigDTO(BaseModel):
    """设备配置更新请求."""
    confidence_values: Optional[dict[str, float]] = Field(default=None, description="检测置信度配置")
    gas_values: Optional[dict[str, float]] = Field(default=None, description="气体阈值配置")
    passage_values: Optional[dict[str, float]] = Field(default=None, description="通道配置")
    disabled_categories: Optional[list[str]] = Field(default=None, description="禁用的检测类别")
    special_detection_rules: Optional[dict] = Field(default=None, description="特殊检测规则")


class DeviceConfigRespVO(BaseModel):
    """设备配置响应."""
    device_id: str = Field(description="设备唯一标识")
    config: dict = Field(description="设备检测配置")


class DeviceIpMapRespVO(BaseModel):
    """设备 IP 映射响应."""
    devices: dict[str, dict[str, str]] = Field(description="device_id→{ip, name} 映射")


class SocketIOStatusRespVO(BaseModel):
    """SocketIO 兼容层状态响应."""
    enabled: bool = Field(description="SocketIO 兼容层是否启用")
    online_devices: list[str] = Field(description="在线设备列表")
    online_count: int = Field(description="在线设备数量")
    threshold_cache: dict = Field(default={}, description="阈值缓存")


class ControlCommandRespVO(BaseModel):
    """控制命令响应."""
    status: str = Field(description="命令状态")
    device_id: str = Field(description="目标设备 ID")
    command: dict = Field(description="发送的命令内容")
