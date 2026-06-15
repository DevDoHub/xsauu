"""告警路由."""

from fastapi import APIRouter, Query, BackgroundTasks
from fastapi.responses import StreamingResponse

from app.db import SessionDep
from app.schemas.alarm import (
    AlarmListRespVO, AlarmRespVO, AlarmTriggerDTO,
    DeleteAlarmDTO, BatchDeleteAlarmDTO, AlarmUpdateStatusDTO,
    AlarmControlDTO, ReportIssueDTO, ExportSearchDTO,
)
from app.services.alarm import AlarmService

router = APIRouter(prefix="", tags=["告警管理"])


@router.get("/alarms/", response_model=AlarmListRespVO, summary="告警列表")
# NOTE: 通用分页查询接口，供管理后台或第三方消费者使用；前端 HistorySearchPage 用的是 /search_history
def list_alarms(
    session: SessionDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    device_id: str | None = Query(None, description="按设备筛选"),
    severity: str | None = Query(None, description="按严重级别筛选"),
    is_reviewed: bool | None = Query(None, description="按审核状态筛选"),
    start_time: str | None = Query(None, description="开始时间"),
    end_time: str | None = Query(None, description="结束时间"),
):
    svc = AlarmService(session)
    return svc.list_alarms(
        page=page,
        page_size=page_size,
        device_id=device_id,
        severity=severity,
        is_reviewed=is_reviewed,
        start_time=start_time,
        end_time=end_time,
    )


@router.get("/alarms/type_stats", summary="按类别统计报警")
def get_type_stats(
    session: SessionDep,
    range: str = Query("today", description="时间范围: today/week/month"),
):
    """按时间范围统计报警类别数量，用于安全驾驶舱图表."""
    svc = AlarmService(session)
    data = svc.get_type_stats(range)
    return {"data": data, "range": range}


@router.get("/alarms/stats/trend", summary="报警趋势统计")
# NOTE: 新增接口，供新仪表盘预留；当前前端未调用
def get_trend_stats(
    session: SessionDep,
    days: int = Query(7, ge=1, le=90, description="统计天数"),
):
    """获取报警趋势统计（按天）."""
    svc = AlarmService(session)
    data = svc.get_trend_stats(days)
    return {"data": data}


@router.get("/alarms/history/export", summary="导出报警历史为CSV")
# NOTE: 按条件导出接口，供管理后台使用；前端 HistorySearchPage 用的是 POST /export_search_results_csv
def export_alarm_history(
    session: SessionDep,
    device_id: str | None = Query(None),
    severity: str | None = Query(None),
    start_time: str | None = Query(None),
    end_time: str | None = Query(None),
):
    """导出报警历史记录为 CSV 文件."""
    svc = AlarmService(session)
    csv_content = svc.export_csv(
        device_id=device_id,
        severity=severity,
        start_time=start_time,
        end_time=end_time,
    )
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=alarm_history.csv"},
    )


@router.get("/alarms/filter_options", summary="获取历史记录筛选下拉选项")
def get_filter_options(session: SessionDep):
    """返回数据库中实际存在的摄像头序号、安全类别、报警描述、设备负责人列表."""
    svc = AlarmService(session)
    return svc.get_filter_options()


@router.get("/alarms/search_history", summary="搜索历史记录（兼容旧前端）")
def search_history(
    session: SessionDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    idx: str | None = Query(None, description="摄像头序号"),
    type: str | None = Query(None, description="报警描述"),
    type2: str | None = Query(None, description="安全类别"),
    owner: str | None = Query(None, description="设备负责人"),
    start_time: str | None = Query(None, description="开始时间"),
    end_time: str | None = Query(None, description="结束时间"),
):
    """搜索历史报警记录，兼容旧前端接口格式.

    返回格式:
    {
        "data": [...],
        "count": 100,
        "page": 1,
        "page_size": 12
    }
    """
    svc = AlarmService(session)
    result = svc.search_history(
        page=page,
        page_size=page_size,
        device_id=idx,
        type2=type2,
        type=type,
        owner=owner,
        start_time=start_time,
        end_time=end_time,
    )
    return {
        "data": result.items,
        "count": result.total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/alarms/delete_history_record", summary="删除历史记录")
def delete_history_record(session: SessionDep, dto: DeleteAlarmDTO) -> dict:
    """删除单条历史记录（含关联图片）.

    兼容两种调用方式:
    - 新前端: { alarm_id: 123 }
    - 旧前端/store: { idx: "1", time: "2025-01-04 12:00:00" }
    """
    svc = AlarmService(session)
    svc.delete_history_record(dto)
    return {"status": "success", "message": "Record deleted successfully"}


@router.post("/alarms/batch_delete_history_records", summary="批量删除历史记录")
def batch_delete_history_records(session: SessionDep, dto: BatchDeleteAlarmDTO) -> dict:
    """批量删除历史记录（含关联图片）.

    每条 record 支持两种定位方式:
    - { alarm_id: 123 } — 按主键
    - { idx: "1", alarm_time: "..." } — 按设备ID+时间（兼容旧前端）
    """
    svc = AlarmService(session)
    deleted = svc.batch_delete_history_records(dto.records)
    return {"status": "success", "deleted": deleted, "images_deleted": deleted}


@router.post("/alarms/report_search_issue", summary="报告搜索问题")
def report_search_issue(dto: ReportIssueDTO) -> dict:
    """报告搜索问题（记录日志）."""
    from app.logger import logger
    logger.info(f"搜索问题报告: 记录={dto.record}, 原因={dto.reason}")
    return {"status": "success", "message": "问题已报告"}


@router.post("/alarms/export_search_results_csv", summary="导出搜索结果为CSV")
def export_search_results_csv(session: SessionDep, dto: ExportSearchDTO) -> StreamingResponse:
    """导出搜索结果为CSV."""
    if not dto.records:
        from app.exceptions import BadRequestException
        raise BadRequestException("没有数据可导出")
    svc = AlarmService(session)
    csv_content = svc.export_search_results_csv(dto.records)
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=search_results.csv"},
    )


# ── REST API 端点 ────────────────────────────────────────────────────────────


@router.get("/alarms/today", summary="当天报警列表")
def get_today(session: SessionDep):
    """获取当天报警列表，用于报警复核页面."""
    svc = AlarmService(session)
    items = svc.get_today_alarms()
    return {"data": items, "count": len(items)}


@router.post("/alarms/update_status", summary="更新报警复核状态")
def update_status(session: SessionDep, dto: AlarmUpdateStatusDTO) -> dict:
    """更新报警复核状态.

    前端发送格式: { review_key: "123", review_status: 0/1/2 }
    - 0: 未处理
    - 1: 误报警
    - 2: 确定报警
    """
    svc = AlarmService(session)
    alarm = svc.update_review_status_by_key(dto.get_effective_alarm_id(), dto.review_status)
    return {"error": False, "data": {"review_key": str(alarm.id), "review_status": alarm.review_status}}


@router.get("/alarms/status", summary="获取设备报警状态")
def get_alarm_status(session: SessionDep):
    """返回每个设备的报警状态（最近1小时内未审核的报警）."""
    svc = AlarmService(session)
    return svc.get_alarm_status()


@router.post("/alarms/control", summary="报警控制")
def alarm_control(session: SessionDep, dto: AlarmControlDTO) -> dict:
    """处理报警确认/清除操作.

    action='clear': 将该设备最近1小时内的报警标记为已复核（误报）
    action='trigger': 为该设备创建一条手动报警记录
    """
    svc = AlarmService(session)
    result = svc.control_alarm(
        action=dto.action,
        device_id=dto.device_id,
        severity=dto.severity,
        description=dto.description,
    )
    return {"status": "ok", **result}


@router.get("/alarms/stream", summary="最近报警事件列表")
def get_alarm_stream(session: SessionDep, last_time: str = Query("", description="上次最新报警时间，用于增量获取")):
    """增量获取报警事件列表，前端每 30 秒轮询。

    与旧版 /alarm/stream 完全兼容。
    - last_time 为空时返回最近的报警
    - last_time 非空时只返回该时间之后的新报警
    """
    svc = AlarmService(session)
    return svc.get_alarm_stream_items(last_time=last_time)


@router.post("/alarms/reset_abnormal", summary="重置报警流")
def reset_abnormal():
    """清空报警流列表，下次 stream 轮询只返回新报警。

    对应旧版 /command/reset_abnormal_num。
    通过 _stream_cleared_at 时间戳实现增量过滤。
    """
    AlarmService.reset_stream()
    return {"status": "ok"}


@router.get("/alarms/abnormal_data", summary="获取异常数据（已废弃）")
def get_abnormal_data():
    """获取异常数据 — 新版前端不再调用此接口，保留仅作向后兼容。"""
    return {"data": {}}


@router.post("/alarms/trigger", summary="触发带违章信息的报警")
async def alarm_trigger(session: SessionDep, dto: AlarmTriggerDTO, background_tasks: BackgroundTasks):
    """创建带违章信息的报警记录，支持附带截图。

    创建后通过 SSE 广播通知所有前端客户端实时更新。
    """
    svc = AlarmService(session)

    # 保存截图到磁盘
    image_url = svc.save_alarm_image(dto.image, dto.device_id) if dto.image else None

    alarm = svc.create_alarm(
        device_id=dto.device_id,
        severity=dto.severity,
        description=dto.description,
        image_url=image_url,
        note=dto.note,
        type=dto.type,
        type2=dto.type2,
    )

    # SSE 实时广播：通知所有前端客户端
    from app.services.detection import detection_service
    alarm_data = {
        "device_id": dto.device_id,
        "severity": dto.severity,
        "description": dto.description,
        "image_url": image_url or "",
        "note": dto.note or "",
        "type": dto.type or "",
        "type2": dto.type2 or "",
        "alarm_time": str(alarm.alarm_time),
    }
    background_tasks.add_task(detection_service.push_alarm, alarm_data)

    # SocketIO 推送：通知边缘端触发报警（对应旧系统 alarm_trigger_with_violation）
    from app.socketio_compat import is_device_online, push_command
    if is_device_online(dto.device_id):
        background_tasks.add_task(push_command, dto.device_id, "alarm_trigger")

    return {"status": "ok", "alarm_id": alarm.id, "image_url": image_url}


# ⚠️ {alarm_pk} 必须放在所有固定路径路由之后，否则会拦截 /alarms/search_history 等路径
@router.get("/alarms/{alarm_pk}", response_model=AlarmRespVO, summary="获取告警详情")
def get_alarm(alarm_pk: int, session: SessionDep):
    svc = AlarmService(session)
    return svc.get_alarm(alarm_pk)
