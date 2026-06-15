"""Pydantic Schema - 告警相关请求/响应."""

import datetime
from typing import Any
from pydantic import BaseModel, Field, field_validator
from app.schemas.common import PaginatedResponse
from app.models.alarm import AlarmSource, AlarmAction


class AlarmReviewDTO(BaseModel):
    """审核告警."""
    is_reviewed: bool = Field(True, description="是否确认为有效告警")
    reviewed_by: str = Field(..., description="审核人")


class AlarmTriggerDTO(BaseModel):
    """触发带违章信息的报警请求."""
    device_id: str = Field(..., description="设备ID")
    severity: str = Field("medium", description="严重级别: info/warning/critical")
    description: str = Field("手动报警", description="报警描述")
    image: str = Field("", description="Base64 编码的图片数据（含 data:image 前缀）")
    note: str = Field("", description="备注/报警区域")
    type: str = Field("", description="事件类型，如'没有安全帽'")
    type2: str = Field("", description="事件类别，如'安全文明着装'")


# ── 新增 DTO（路由层入参校验）─────────────────────────────────────────────────


class DeleteAlarmDTO(BaseModel):
    """删除单条历史记录请求.

    支持两种定位方式（兼容新旧前端）：
    - alarm_id: 按主键删除（新前端）
    - idx + time: 按 device_id + alarm_time 删除（旧前端/store）
    """
    alarm_id: int | None = Field(None, description="告警主键 ID")
    idx: str | None = Field(None, description="摄像头序号（device_id）")
    time: str | None = Field(None, description="报警时间字符串")
    alarm_time: str | None = Field(None, description="报警时间字符串（别名）")


class BatchDeleteRecordItem(BaseModel):
    """批量删除中的单条记录."""
    alarm_id: int | None = Field(None, description="告警主键 ID")
    idx: str | None = Field(None, description="摄像头序号（device_id）")
    alarm_time: str | None = Field(None, description="报警时间字符串")
    time: str | None = Field(None, description="报警时间字符串（别名）")


class BatchDeleteAlarmDTO(BaseModel):
    """批量删除历史记录请求."""
    records: list[BatchDeleteRecordItem] = Field(..., description="待删除记录列表")


class AlarmUpdateStatusDTO(BaseModel):
    """更新报警复核状态请求.

    兼容前端多种字段名：review_key / id / alarm_id。
    """
    review_key: str | None = Field(None, description="告警 ID（字符串，前端主用）")
    id: int | None = Field(None, description="告警 ID（整数）")
    alarm_id: int | None = Field(None, description="告警 ID（整数，别名）")
    review_status: int = Field(0, description="复核状态：0=未处理，1=误报警，2=确定报警")

    def get_effective_alarm_id(self) -> int | None:
        """返回有效的告警 ID，优先级: review_key > id > alarm_id."""
        for val in (self.review_key, self.id, self.alarm_id):
            if val is not None:
                try:
                    return int(val)
                except (ValueError, TypeError):
                    continue
        return None


class AlarmControlDTO(BaseModel):
    """报警控制请求."""
    action: AlarmAction = Field(..., description="操作类型: clear / trigger")
    device_id: str = Field(..., description="设备 ID")
    severity: str = Field("high", description="严重级别（仅 trigger 有效）")
    description: str = Field("手动触发报警", description="报警描述（仅 trigger 有效）")


class ReportIssueDTO(BaseModel):
    """报告搜索问题请求."""
    record: dict = Field(default_factory=dict, description="问题记录")
    reason: str = Field("", description="问题原因")


class ExportSearchDTO(BaseModel):
    """导出搜索结果请求."""
    records: list[dict] = Field(..., description="待导出的记录列表")


class AlarmRespVO(BaseModel):
    """告警信息响应."""
    id: int
    source: AlarmSource = AlarmSource.FIRE
    device_id: str
    severity: str
    confidence: float
    type: str = ""
    type2: str = ""
    note: str = ""
    image_url: str | None
    bbox: str | None
    is_reviewed: bool
    review_status: int = 0
    reviewed_by: str | None
    reviewed_at: str | None
    alarm_time: str


    model_config = {"from_attributes": True}

    @field_validator("alarm_time", "reviewed_at", mode="before")
    @classmethod
    def datetime_to_str(cls, v: Any) -> str | None:
        if v is None:
            return None
        if isinstance(v, datetime.datetime):
            return v.strftime("%Y-%m-%d %H:%M:%S")
        return str(v)


class AlarmListRespVO(PaginatedResponse[AlarmRespVO]):
    """告警列表分页响应."""
    pass


class AlarmReviewItemVO(BaseModel):
    """报警复核页面列表项（前端 AlarmReviewPage 专用）."""
    review_key: str = Field("", description="告警主键（字符串形式，前端复核用）")
    review_status: int = Field(0, description="复核状态: 0=未处理, 1=误报警, 2=确定报警")
    image: str = Field("", description="告警截图路径")
    type: str = Field("", description="事件类型，如'没有安全帽'")
    type2: str = Field("", description="事件类别，如'安全文明着装'")
    note: str = Field("", description="报警区域")
    alarm_time: str = Field("", description="报警时间")
    device_id: str = Field("", description="设备 ID")
    confidence: float = Field(0.0, description="AI 置信度 0-1")


class AlarmStreamItemVO(BaseModel):
    """报警流轮询列表项（前端 fetchStream 专用）."""
    idx: str = Field("", description="摄像头序号（device_id）")
    type: str = Field("", description="事件类型")
    type2: str = Field("", description="事件类别")
    note: str = Field("", description="报警区域")
    alarm_time: str = Field("", description="报警时间")
    time: str = Field("", description="报警时间（兼容前端 fetchStream）")
    image_url: str = Field("", description="告警截图路径")
    img: str = Field("", description="告警截图路径（兼容旧前端）")
    device_manager: str = Field("", description="设备负责人")
    area_manager: str = Field("", description="区域负责人")
    area_manager_phone: str = Field("", description="区域负责人电话")
    owner: str = Field("", description="设备负责人（兼容旧字段）")
    review_status: int = Field(0, description="复核状态")


class AlarmHistoryItemVO(BaseModel):
    """历史记录搜索列表项（前端 HistorySearchPage 专用）."""
    idx: str = Field("", description="摄像头序号（device_id）")
    note: str = Field("", description="报警区域")
    type: str = Field("", description="事件类型")
    type2: str = Field("", description="事件类别")
    device_manager: str = Field("", description="设备负责人")
    area_manager: str = Field("", description="区域负责人")
    area_manager_phone: str = Field("", description="区域负责人电话")
    alarm_time: str = Field("", description="报警时间")
    image: str | None = Field(None, description="告警截图路径")
    img: str | None = Field(None, description="告警截图路径（兼容旧前端）")
    review_status: int = Field(0, description="复核状态")
    alarm_id: int | None = Field(None, description="告警主键 ID")
    severity: str = Field("", description="严重级别")
    confidence: float = Field(0.0, description="AI 置信度 0-1")


class AlarmHistorySearchVO(BaseModel):
    """历史记录搜索响应."""
    items: list[AlarmHistoryItemVO] = Field(default_factory=list, description="搜索结果列表")
    total: int = Field(0, description="匹配总数")
