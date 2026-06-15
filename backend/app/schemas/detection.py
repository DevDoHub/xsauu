"""检测框数据 Schema 定义."""

from pydantic import BaseModel, Field

from app.schemas.device import DetectionAction


# ── 气体类型注册表常量 ──────────────────────────────────────────────────────

GAS_REGISTRY: list[dict] = [
    {"key": "C3H8", "name": "丙烷", "unit": "%LEL", "display": "丙烷", "has_threshold": True, "threshold_default": 9999},
    {"key": "C2H2", "name": "乙炔", "unit": "%LEL", "display": "乙炔", "has_threshold": True, "threshold_default": 9999},
    {"key": "CO2", "name": "二氧化碳", "unit": "ppm", "display": "二氧化碳", "has_threshold": True, "threshold_default": 9999},
    {"key": "HCN", "name": "氰化氢", "unit": "ppm", "display": "氰化氢", "has_threshold": True, "threshold_default": 9999},
    {"key": "O2", "name": "氧气", "unit": "%VOL", "display": "氧气", "has_threshold": True, "threshold_default": 9999},
    {"key": "AR", "name": "氩气", "unit": "ppm", "display": "氩气", "has_threshold": False, "threshold_default": None},
    {"key": "H2S", "name": "硫化氢", "unit": "ppm", "display": "硫化氢", "has_threshold": False, "threshold_default": None},
    {"key": "TEMP", "name": "温度", "unit": "℃", "display": "温度", "has_threshold": False, "threshold_default": None},
    {"key": "RH", "name": "相对湿度", "unit": "%", "display": "相对湿度", "has_threshold": False, "threshold_default": None},
]


# ── 请求 DTO ────────────────────────────────────────────────────────────────


class DetectionPushDTO(BaseModel):
    """边缘端推送检测框数据."""
    device_name: str = Field(..., max_length=64, description="设备名称")
    boxes: list[dict] = Field(default_factory=list, description="检测框列表")
    timestamp: float | str | None = Field(None, description="时间戳")

    model_config = {"extra": "allow"}


class DetectionControlDTO(BaseModel):
    """检测控制命令."""
    action: DetectionAction = Field(..., description="动作: start/stop")


class BatchDetectionControlDTO(BaseModel):
    """批量检测控制命令."""
    device_ids: list[str] = Field(..., description="设备ID列表")
    action: DetectionAction = Field(..., description="动作: start/stop")


class PersonDetectionControlDTO(BaseModel):
    """按负责人检测控制命令."""
    person: str = Field(..., description="负责人名称")
    action: DetectionAction = Field(..., description="动作: start/stop")


# ── 响应 VO ─────────────────────────────────────────────────────────────────


class DetectionPushRespVO(BaseModel):
    """检测框推送响应."""
    status: str = Field(..., description="处理状态")
    device: str = Field(..., description="映射后的设备名")


class DetectionControlRespVO(BaseModel):
    """检测控制命令响应."""
    status: str = Field(..., description="命令状态")
    action: DetectionAction = Field(..., description="执行的动作")


class GlobalDetectionControlRespVO(DetectionControlRespVO):
    """全局检测控制响应."""
    scope: str = Field(default="global", description="命令范围")
    command: dict = Field(default_factory=dict, description="命令详情")


class BatchDetectionControlRespVO(DetectionControlRespVO):
    """批量检测控制响应."""
    results: list[dict] = Field(default_factory=list, description="各设备执行结果")


class PersonDetectionControlRespVO(DetectionControlRespVO):
    """按负责人检测控制响应."""
    person: str = Field(default="", description="负责人名称")
    results: list[dict] = Field(default_factory=list, description="各设备执行结果")


class GasMonitorDataRespVO(BaseModel):
    """气体监控聚合数据响应（驾驶舱专用）."""
    realtime: dict = Field(default_factory=dict, description="实时气体数据 {device_id: {...}}")
    threshold: dict = Field(default_factory=dict, description="阈值数据 {device_id: {...}}")
    registry: list[dict] = Field(default_factory=list, description="气体类型注册表")


class GasThresholdRespVO(BaseModel):
    """气体阈值配置响应."""
    data: dict = Field(default_factory=dict, description="阈值数据 {device_id: {...}}")
