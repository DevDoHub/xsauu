"""SQLModel 数据模型 - 设备（边缘端 Jetson）."""

import datetime

from sqlmodel import Field, SQLModel


class Device(SQLModel, table=True):
    """设备表，记录每台 Jetson 边缘端."""

    __tablename__ = "device"

    id: int | None = Field(default=None, primary_key=True)
    device_id: str = Field(max_length=64, unique=True, index=True, description="设备唯一标识")
    name: str = Field(max_length=100, description="设备名称，如 '1号摄像头'")
    location: str = Field(default="", max_length=200, description="安装位置描述")
    ip_address: str = Field(default="", max_length=45, description="设备 IP")
    camera_url: str = Field(default="", max_length=500, description="摄像头 RTSP 地址")
    mediamtx_path: str = Field(default="", max_length=100, description="MediaMTX 视频路径名（默认=device_id）")
    is_online: bool = Field(default=False, description="是否在线")
    online_since: datetime.datetime | None = Field(default=None, description="本次上线时间")
    accumulated_runtime: int = Field(default=0, description="累计在线秒数（不含当前在线段）")
    last_heartbeat: datetime.datetime | None = Field(default=None, description="最后心跳时间")
    status: str = Field(default="active", max_length=20, description="状态: active/disabled/maintenance")
    
    # 作业信息（迁移自旧系统）
    responsible_person: str = Field(default="", max_length=50, description="设备负责人")
    area_manager: str = Field(default="", max_length=50, description="区域负责人")
    area_manager_phone: str = Field(default="", max_length=20, description="区域负责人电话")
    workshop: str = Field(default="", max_length=100, description="车间/工作区域")
    safety_permit_no: str = Field(default="", max_length=50, description="安全许可证号")
    work_content: str = Field(default="", max_length=200, description="作业内容")
    work_level: str = Field(default="", max_length=50, description="作业等级")
    work_type: str = Field(default="", max_length=50, description="作业类型")
    confined_space: str = Field(default="", max_length=10, description="是否受限空间")
    work_start_time: str = Field(default="", max_length=30, description="作业开始时间")
    work_end_time: str = Field(default="", max_length=30, description="作业结束时间")
    work_status: str = Field(default="", max_length=20, description="作业状态")
    
    # 视频方向配置
    camera_rotation: int = Field(default=0, description="摄像头旋转角度（0=正常, 180=倒装）")
    
    # 设备配置（JSON 格式存储）
    config_json: str | None = Field(default=None, description="设备检测配置 JSON")
    
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
