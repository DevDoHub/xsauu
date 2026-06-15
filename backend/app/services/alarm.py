"""告警业务逻辑层."""

import base64
import datetime
from datetime import timedelta
from pathlib import Path
from typing import Any

from sqlmodel import Session, select, func, col

from app.models.alarm import Alarm, AlarmSource, ReviewStatus, AlarmAction
from app.models.device import Device
from app.schemas.alarm import (
    AlarmRespVO, AlarmListRespVO,
    DeleteAlarmDTO, BatchDeleteRecordItem,
    AlarmReviewItemVO, AlarmStreamItemVO, AlarmHistoryItemVO, AlarmHistorySearchVO,
)
from app.exceptions import NotFoundException, BadRequestException
from app.logger import logger

# 模块级变量：记录最近一次 reset_abnormal 的时间点
# reset 后，stream 接口只返回此时间之后的报警
_stream_cleared_at: str | None = None

# 复核操作常量
_REVIEWED_BY_ADMIN = "admin"
_REVIEWED_BY_MANUAL_CLEAR = "manual_clear"
_MANUAL_ALARM_TYPE2 = "手动报警"


class AlarmService:
    """告警 Service."""

    def __init__(self, session: Session):
        self.session = session

    def create_alarm(
        self,
        device_id: str,
        severity: str = "warning",
        confidence: float = 0.0,
        description: str = "",
        image_url: str | None = None,
        bbox: str | None = None,
        note: str = "",
        type: str = "",
        type2: str = "",
        # 设备/作业快照——告警写入时冻结，避免历史记录被后续 Device 配置变更污染。
        # 调用方未传时为空字符串，查询时会回退到 Device 表当前值（兼容老告警）。
        snapshot_device_name: str = "",
        snapshot_device_manager: str = "",
        snapshot_area_manager: str = "",
        snapshot_area_manager_phone: str = "",
        snapshot_ip_address: str = "",
        snapshot_workshop: str = "",
        snapshot_safety_permit_no: str = "",
        snapshot_work_content: str = "",
        snapshot_work_level: str = "",
        snapshot_work_type: str = "",
        snapshot_confined_space: str = "",
        snapshot_work_start_time: str = "",
        snapshot_work_end_time: str = "",
        snapshot_work_status: str = "",
    ) -> AlarmRespVO:
        """创建告警.

        Returns:
            告警响应 VO。
        """
        alarm = Alarm(
            device_id=device_id,
            severity=severity,
            confidence=confidence,
            description=description,
            image_url=image_url,
            bbox=bbox,
            note=note,
            type=type,
            type2=type2,
            snapshot_device_name=snapshot_device_name,
            snapshot_device_manager=snapshot_device_manager,
            snapshot_area_manager=snapshot_area_manager,
            snapshot_area_manager_phone=snapshot_area_manager_phone,
            snapshot_ip_address=snapshot_ip_address,
            snapshot_workshop=snapshot_workshop,
            snapshot_safety_permit_no=snapshot_safety_permit_no,
            snapshot_work_content=snapshot_work_content,
            snapshot_work_level=snapshot_work_level,
            snapshot_work_type=snapshot_work_type,
            snapshot_confined_space=snapshot_confined_space,
            snapshot_work_start_time=snapshot_work_start_time,
            snapshot_work_end_time=snapshot_work_end_time,
            snapshot_work_status=snapshot_work_status,
        )
        self.session.add(alarm)
        self.session.commit()
        self.session.refresh(alarm)
        return AlarmRespVO.model_validate(alarm)

    def save_alarm_image(self, base64_data: str, device_id: str) -> str:
        """将 Base64 图片保存到磁盘，返回相对路径.

        Args:
            base64_data: Base64 编码的图片数据（含 data:image 前缀）。
            device_id: 设备 ID。

        Returns:
            保存后的相对路径，失败返回空字符串。
        """
        if not base64_data or not base64_data.startswith("data:image"):
            return ""

        try:
            # 解析 base64 数据
            header, encoded = base64_data.split(",", 1)
            img_bytes = base64.b64decode(encoded)

            # 确定保存目录（backend/data/alarm_images/）
            save_dir = Path(__file__).resolve().parents[2] / "data" / "alarm_images"
            save_dir.mkdir(parents=True, exist_ok=True)

            # 生成文件名：设备ID_时间戳.jpg
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{device_id}_{ts}.jpg"
            filepath = save_dir / filename

            filepath.write_bytes(img_bytes)
            return f"alarm_images/{filename}"
        except Exception as e:
            logger.warning(f"保存报警截图失败: {e}")
            return ""

    def get_alarm(self, alarm_id: int) -> AlarmRespVO:
        """获取告警详情."""
        alarm = self.session.get(Alarm, alarm_id)
        if not alarm:
            raise NotFoundException(f"告警 {alarm_id} 不存在")
        return AlarmRespVO.model_validate(alarm)

    def list_alarms(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        device_id: str | None = None,
        severity: str | None = None,
        is_reviewed: bool | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> AlarmListRespVO:
        """分页查询告警."""
        skip = (page - 1) * page_size
        stmt = self._build_filter(
            device_id=device_id, severity=severity,
            is_reviewed=is_reviewed, start_time=start_time, end_time=end_time,
        )
        total_stmt = self._build_count(
            device_id=device_id, severity=severity,
            is_reviewed=is_reviewed, start_time=start_time, end_time=end_time,
        )

        alarms = list(
            self.session.exec(
                stmt.order_by(col(Alarm.alarm_time).desc()).offset(skip).limit(page_size)
            ).all()
        )
        total = self.session.exec(total_stmt).one()

        return AlarmListRespVO(
            total=total,
            items=[AlarmRespVO.model_validate(a) for a in alarms],
            page=page,
            page_size=page_size,
        )

    def get_type_stats(self, range_param: str = "today") -> list[dict[str, Any]]:
        """按时间范围统计报警类别数量."""
        now = datetime.datetime.now(datetime.timezone.utc)
        
        if range_param == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif range_param == "week":
            # 本周一
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        elif range_param == "month":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        stmt = (
            select(Alarm.type2, func.count().label("count"))
            .where(Alarm.alarm_time >= start)
            .where(Alarm.source == AlarmSource.FIRE)
            .group_by(Alarm.type2)
        )
        results = self.session.exec(stmt).all()

        return [
            {"name": row[0] or "未知", "value": row[1]}
            for row in results
        ]

    def get_trend_stats(self, days: int = 7) -> list[dict[str, Any]]:
        """获取报警趋势统计（按天）."""
        now = datetime.datetime.now(datetime.timezone.utc)
        start = now - timedelta(days=days)
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 按日期分组统计
        stmt = (
            select(
                func.date(Alarm.alarm_time).label("date"),
                func.count().label("count")
            )
            .where(Alarm.alarm_time >= start)
            .group_by(func.date(Alarm.alarm_time))
            .order_by(func.date(Alarm.alarm_time))
        )
        results = self.session.exec(stmt).all()
        
        return [
            {"date": str(row[0]), "count": row[1]}
            for row in results
        ]

    def get_today_reviews(self) -> list[AlarmRespVO]:
        """获取当天报警列表（用于报警复核）."""
        now = datetime.datetime.now(datetime.timezone.utc)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        stmt = (
            select(Alarm)
            .where(Alarm.alarm_time >= start)
            .order_by(col(Alarm.alarm_time).desc())
        )
        alarms = list(self.session.exec(stmt).all())
        return [AlarmRespVO.model_validate(a) for a in alarms]

    def _apply_common_filters(
        self,
        stmt: Any,
        *,
        device_id: str | None = None,
        severity: str | None = None,
        is_reviewed: bool | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> Any:
        """为查询语句添加通用过滤条件.

        Args:
            stmt: SQLAlchemy 查询语句。
            device_id: 设备 ID 过滤。
            severity: 严重级别过滤。
            is_reviewed: 审核状态过滤。
            start_time: 起始时间（ISO 格式）。
            end_time: 截止时间（ISO 格式）。

        Returns:
            添加过滤条件后的查询语句。
        """
        if device_id:
            stmt = stmt.where(Alarm.device_id == device_id)
        if severity:
            stmt = stmt.where(Alarm.severity == severity)
        if is_reviewed is not None:
            stmt = stmt.where(Alarm.is_reviewed == is_reviewed)
        if start_time:
            try:
                start_dt = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                stmt = stmt.where(Alarm.alarm_time >= start_dt)
            except ValueError:
                logger.warning(f"无法解析 start_time: {start_time}")
        if end_time:
            try:
                end_dt = datetime.datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                stmt = stmt.where(Alarm.alarm_time <= end_dt)
            except ValueError:
                logger.warning(f"无法解析 end_time: {end_time}")
        return stmt

    def _build_filter(
        self,
        *,
        device_id: str | None = None,
        severity: str | None = None,
        is_reviewed: bool | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> Any:
        """构建告警列表查询语句."""
        return self._apply_common_filters(
            select(Alarm),
            device_id=device_id, severity=severity,
            is_reviewed=is_reviewed, start_time=start_time, end_time=end_time,
        )

    def _build_count(
        self,
        *,
        device_id: str | None = None,
        severity: str | None = None,
        is_reviewed: bool | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> Any:
        """构建告警计数查询语句."""
        return self._apply_common_filters(
            select(func.count()).select_from(Alarm),
            device_id=device_id, severity=severity,
            is_reviewed=is_reviewed, start_time=start_time, end_time=end_time,
        )

    def export_csv(
        self,
        *,
        device_id: str | None = None,
        severity: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> str:
        """导出报警历史为 CSV 字符串."""
        import csv
        import io

        result = self.list_alarms(
            page=1,
            page_size=10000,
            device_id=device_id,
            severity=severity,
            start_time=start_time,
            end_time=end_time,
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "ID", "设备ID", "事件类型", "事件类别", "严重级别", "置信度",
            "描述", "是否已审核", "审核人", "报警时间",
        ])
        for alarm in result.items:
            writer.writerow([
                alarm.id,
                alarm.device_id,
                alarm.type,
                alarm.type2,
                alarm.severity,
                alarm.confidence,
                alarm.description,
                "是" if alarm.is_reviewed else "否",
                alarm.reviewed_by or "",
                alarm.alarm_time,
            ])
        output.seek(0)
        return output.getvalue()

    def search_history(
        self,
        *,
        page: int = 1,
        page_size: int = 12,
        device_id: str | None = None,
        type2: str | None = None,
        type: str | None = None,
        owner: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> AlarmHistorySearchVO:
        """搜索历史报警记录，兼容旧前端格式.

        Args:
            page: 页码。
            page_size: 每页数量。
            device_id: 设备 ID。
            type2: 安全类别。
            type: 报警描述。
            owner: 设备负责人。
            start_time: 起始时间。
            end_time: 截止时间。

        Returns:
            包含 items 和 total 的搜索响应 VO。
        """
        skip = (page - 1) * page_size

        # 构建查询
        stmt = select(Alarm)
        count_stmt = select(func.count()).select_from(Alarm)

        # 设备ID筛选
        if device_id:
            stmt = stmt.where(Alarm.device_id == device_id)
            count_stmt = count_stmt.where(Alarm.device_id == device_id)

        # 安全类别筛选（直接按 Alarm.type2 字段匹配）
        if type2:
            stmt = stmt.where(Alarm.type2 == type2)
            count_stmt = count_stmt.where(Alarm.type2 == type2)

        # 报警描述筛选（直接按 Alarm.type 字段匹配）
        if type:
            stmt = stmt.where(Alarm.type == type)
            count_stmt = count_stmt.where(Alarm.type == type)

        # 设备负责人筛选（关联 Device 表）
        if owner:
            try:
                device_ids_with_owner = list(self.session.exec(
                    select(Device.device_id).where(Device.responsible_person == owner)
                ).all())
                if device_ids_with_owner:
                    stmt = stmt.where(Alarm.device_id.in_(device_ids_with_owner))
                    count_stmt = count_stmt.where(Alarm.device_id.in_(device_ids_with_owner))
                else:
                    # 该负责人下无设备，返回空结果
                    return AlarmHistorySearchVO(items=[], total=0)
            except Exception as e:
                logger.warning(f"查询设备负责人失败: {e}")

        # 时间范围筛选
        if start_time:
            try:
                start_dt = datetime.datetime.fromisoformat(start_time.replace(' ', 'T'))
                stmt = stmt.where(Alarm.alarm_time >= start_dt)
                count_stmt = count_stmt.where(Alarm.alarm_time >= start_dt)
            except ValueError:
                logger.warning(f"search_history 无法解析 start_time: {start_time}")
        if end_time:
            try:
                end_dt = datetime.datetime.fromisoformat(end_time.replace(' ', 'T'))
                stmt = stmt.where(Alarm.alarm_time <= end_dt)
                count_stmt = count_stmt.where(Alarm.alarm_time <= end_dt)
            except ValueError:
                logger.warning(f"search_history 无法解析 end_time: {end_time}")

        # 获取总数
        total = self.session.exec(count_stmt).one()

        # 获取分页数据
        alarms = list(
            self.session.exec(
                stmt.order_by(col(Alarm.alarm_time).desc()).offset(skip).limit(page_size)
            ).all()
        )

        # 查设备负责人信息（批量，避免 N+1）
        device_ids = list({a.device_id for a in alarms})
        device_info_map: dict[str, Device] = {}
        if device_ids:
            try:
                devices = list(self.session.exec(
                    select(Device).where(Device.device_id.in_(device_ids))
                ).all())
                for d in devices:
                    device_info_map[d.device_id] = d
            except Exception as e:
                logger.warning(f"查询设备信息失败: {e}")

        # 转换为前端期望的格式
        items: list[AlarmHistoryItemVO] = []
        for alarm in alarms:
            dev = device_info_map.get(alarm.device_id)
            # 快照优先，没有时回退到 Device 表当前值（兼容历史告警）
            device_manager = alarm.snapshot_device_manager or (dev.responsible_person if dev else "")
            area_manager = alarm.snapshot_area_manager or (dev.area_manager if dev else "")
            area_manager_phone = alarm.snapshot_area_manager_phone or (dev.area_manager_phone if dev else "")
            items.append(AlarmHistoryItemVO(
                idx=alarm.device_id,
                note=alarm.note or "",
                type=alarm.type or "",
                type2=alarm.type2 or "",
                device_manager=device_manager,
                area_manager=area_manager,
                area_manager_phone=area_manager_phone,
                alarm_time=alarm.alarm_time.strftime("%Y-%m-%d %H:%M:%S") if alarm.alarm_time else "",
                image=alarm.image_url,
                img=alarm.image_url,
                review_status=alarm.review_status or 0,
                alarm_id=alarm.id,
                severity=alarm.severity,
                confidence=alarm.confidence,
            ))

        return AlarmHistorySearchVO(items=items, total=total)

    def get_filter_options(self) -> dict[str, Any]:
        """返回历史记录筛选下拉框的选项（仅包含数据库中实际存在的值）."""
        # 所有不重复的 device_id（摄像头序号）
        idx_rows = self.session.exec(
            select(Alarm.device_id).distinct().order_by(Alarm.device_id)
        ).all()
        idx_list = [r for r in idx_rows if r]

        # 所有不重复的 type2（安全类别）和 type（报警描述）
        # Alarm.type2 = event_category = "安全文明着装"、"火灾隐患"等
        # Alarm.type  = event_type    = "没有安全帽"、"发现火焰"等
        type2_rows = self.session.exec(
            select(Alarm.type2).distinct()
        ).all()
        categories = sorted([r for r in type2_rows if r])

        type_rows = self.session.exec(
            select(Alarm.type).distinct()
        ).all()
        descriptions = sorted([r for r in type_rows if r])

        # 负责人：从 Device 表联查
        try:
            owner_rows = self.session.exec(
                select(Device.responsible_person).distinct().order_by(Device.responsible_person)
            ).all()
            owners = [r for r in owner_rows if r]
        except Exception:
            owners = []

        return {
            "idx": idx_list,
            "categories": categories,
            "descriptions": descriptions,
            "owners": owners,
        }

    def delete_alarm(self, alarm_id: int) -> bool:
        """删除单条告警记录（含关联图片）.

        Args:
            alarm_id: 告警 ID。

        Returns:
            删除成功返回 True，记录不存在返回 False。
        """
        alarm = self.session.get(Alarm, alarm_id)
        if not alarm:
            return False
        self._delete_alarm_image(alarm)
        self.session.delete(alarm)
        self.session.commit()
        return True

    def find_alarm_by_device_and_time(self, device_id: str, alarm_time: str) -> Alarm | None:
        """按 device_id + alarm_time 精确查找告警（兼容旧前端 deleteAlarm(idx, time)）.

        Args:
            device_id: 设备 ID。
            alarm_time: 报警时间字符串，支持 "%Y-%m-%d %H:%M:%S" 和 ISO 格式。

        Returns:
            找到的 Alarm 对象，不存在返回 None。
        """
        try:
            # 尝试解析时间
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
                try:
                    dt = datetime.datetime.strptime(alarm_time, fmt)
                    break
                except ValueError:
                    continue
            else:
                # 最后尝试 fromisoformat
                dt = datetime.datetime.fromisoformat(alarm_time.replace('Z', '+00:00'))

            # 精确匹配：device_id + alarm_time（秒级精度）
            stmt = (
                select(Alarm)
                .where(Alarm.device_id == device_id)
                .where(func.strftime("%Y-%m-%d %H:%M:%S", Alarm.alarm_time) == dt.strftime("%Y-%m-%d %H:%M:%S"))
                .limit(1)
            )
            return self.session.exec(stmt).first()
        except Exception as e:
            logger.warning(f"find_alarm_by_device_and_time 解析失败: device_id={device_id}, alarm_time={alarm_time}, error={e}")
            return None

    def _delete_alarm_image(self, alarm: Alarm) -> None:
        """删除告警关联的图片文件."""
        if not alarm.image_url:
            return
        try:
            # image_url 可能是相对路径如 "alarm_images/xxx.jpg" 或 "/alarm_images/xxx.jpg"
            rel_path = alarm.image_url.lstrip("/")
            full_path = Path(__file__).resolve().parents[2] / "data" / rel_path
            if full_path.exists():
                full_path.unlink()
                logger.info(f"已删除报警图片: {full_path}")
        except Exception as e:
            logger.warning(f"删除报警图片失败: {e}")

    def batch_delete_alarms(self, alarm_ids: list[int]) -> int:
        """批量删除告警记录（含关联图片）.

        Args:
            alarm_ids: 告警 ID 列表。

        Returns:
            成功删除的数量。
        """
        deleted = 0
        for alarm_id in alarm_ids:
            alarm = self.session.get(Alarm, alarm_id)
            if alarm:
                self._delete_alarm_image(alarm)
                self.session.delete(alarm)
                deleted += 1
        self.session.commit()
        return deleted

    # ── 路由层下沉的业务逻辑 ──────────────────────────────────────────────

    def delete_history_record(self, dto: DeleteAlarmDTO) -> None:
        """删除单条历史记录（含关联图片）.

        支持两种定位方式（兼容新旧前端）：
        - alarm_id: 按主键删除
        - idx + time: 按 device_id + alarm_time 查找后删除

        Args:
            dto: DeleteAlarmDTO，含 alarm_id / idx / time / alarm_time。

        Raises:
            BadRequestException: 未提供有效的定位参数。
            NotFoundException: 找不到对应记录。
        """
        alarm_id = dto.alarm_id
        idx = dto.idx
        alarm_time = dto.time or dto.alarm_time

        # 优先用主键删除
        if alarm_id is not None:
            if self.delete_alarm(int(alarm_id)):
                return
            raise NotFoundException(f"告警记录 {alarm_id} 不存在")

        # 降级：按 device_id + alarm_time 查找
        if idx and alarm_time:
            alarm = self.find_alarm_by_device_and_time(str(idx), str(alarm_time))
            if alarm:
                self.delete_alarm(alarm.id)
                return
            raise NotFoundException(f"未找到设备 {idx} 在 {alarm_time} 的报警记录")

        raise BadRequestException("缺少 alarm_id 或 idx + time 参数")

    def batch_delete_history_records(self, records: list[BatchDeleteRecordItem]) -> int:
        """批量删除历史记录（含关联图片）.

        每条记录支持 alarm_id 或 idx + alarm_time 两种定位方式。

        Args:
            records: BatchDeleteRecordItem 列表。

        Returns:
            成功删除的数量。
        """
        alarm_ids: list[int] = []
        for record in records:
            if record.alarm_id is not None:
                try:
                    alarm_ids.append(int(record.alarm_id))
                    continue
                except (ValueError, TypeError):
                    # alarm_id 不是数字（如客户端传了字符串/None），
                    # 回退到 idx+time 双重定位分支
                    logger.debug(f"alarm_id 无效，回退到 idx+time: {record.alarm_id!r}")

            if record.idx and (record.alarm_time or record.time):
                alarm_time = record.alarm_time or record.time
                alarm = self.find_alarm_by_device_and_time(str(record.idx), str(alarm_time))
                if alarm:
                    alarm_ids.append(alarm.id)

        if not alarm_ids:
            raise BadRequestException("未找到任何可删除的记录")

        return self.batch_delete_alarms(alarm_ids)

    def control_alarm(self, action: AlarmAction, device_id: str, **kwargs) -> dict[str, Any]:
        """报警控制：清除或触发.

        Args:
            action: 操作类型，AlarmAction.CLEAR 或 AlarmAction.TRIGGER。
            device_id: 设备 ID。
            **kwargs: trigger 时可传 severity / description。

        Returns:
            操作结果字典。

        Raises:
            BadRequestException: 未知的 action。
        """
        if action == AlarmAction.CLEAR:
            cleared_count = self.clear_device_alarms(device_id)
            # 通过 SocketIO 通知边缘端清除报警
            self._push_alarm_command(device_id, "alarm_clear")
            return {"action": action.value, "device_id": device_id, "cleared_count": cleared_count}
        elif action == AlarmAction.TRIGGER:
            alarm = self.trigger_manual_alarm(
                device_id=device_id,
                severity=kwargs.get("severity", "high"),
                description=kwargs.get("description", "手动触发报警"),
            )
            # 通过 SocketIO 通知边缘端触发报警
            self._push_alarm_command(device_id, "alarm_trigger")
            return {"action": action.value, "device_id": device_id, "alarm_id": alarm.id}

        raise BadRequestException(f"未知操作: {action}")

    @staticmethod
    def _push_alarm_command(device_id: str, cmd_type: str) -> None:
        """通过 SocketIO 向边缘端推送报警指令.

        Args:
            device_id: 设备 ID。
            cmd_type: 指令类型，alarm_clear 或 alarm_trigger。
        """
        import asyncio
        from app.socketio_compat import is_device_online, push_command

        if not is_device_online(device_id):
            logger.warning(f"设备 {device_id} 不在线，跳过 SocketIO 推送: {cmd_type}")
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(push_command(device_id, cmd_type))
        except RuntimeError:
            asyncio.run(push_command(device_id, cmd_type))

    def update_review_status_by_key(self, review_key: str | int | None, review_status: int) -> AlarmRespVO:
        """按 review_key 更新报警复核状态（兼容前端多种字段名）.

        Args:
            review_key: 告警 ID（字符串或整数）。
            review_status: 复核状态，0=未处理，1=误报警，2=确定报警。

        Returns:
            更新后的告警信息。

        Raises:
            BadRequestException: 缺少 ID 或 ID 格式错误。
            NotFoundException: 告警不存在。
        """
        if review_key is None:
            raise BadRequestException("缺少告警 ID")
        try:
            alarm_id = int(review_key)
        except (ValueError, TypeError):
            raise BadRequestException(f"无效的告警 ID: {review_key}")

        alarm = self.update_review_status(alarm_id, review_status)
        if not alarm:
            raise NotFoundException(f"告警 {alarm_id} 不存在")
        return alarm

    def update_review_status(self, alarm_id: int, review_status: int) -> AlarmRespVO | None:
        """更新报警复核状态.

        Args:
            alarm_id: 告警 ID。
            review_status: 复核状态，0=未处理，1=误报警，2=确定报警。

        Returns:
            更新后的告警信息，不存在返回 None。
        """
        alarm = self.session.get(Alarm, alarm_id)
        if not alarm:
            return None
        alarm.review_status = review_status
        alarm.is_reviewed = (review_status == 2)
        alarm.reviewed_by = _REVIEWED_BY_ADMIN if review_status > 0 else None
        alarm.reviewed_at = datetime.datetime.now(datetime.timezone.utc) if review_status > 0 else None
        self.session.add(alarm)
        self.session.commit()
        self.session.refresh(alarm)
        return AlarmRespVO.model_validate(alarm)

    def get_alarm_status(self) -> dict[str, dict[str, Any]]:
        """返回每个设备的报警状态（最近1小时内未审核的报警）.

        Returns:
            {device_id: {"alarm_active": bool, "alarm_count": int}} 映射。
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        cutoff = now - timedelta(hours=1)
        stmt = (
            select(Alarm)
            .where(Alarm.alarm_time >= cutoff)
            .where(Alarm.is_reviewed.is_(False))
        )
        alarms = list(self.session.exec(stmt).all())

        result: dict[str, dict[str, Any]] = {}
        for alarm in alarms:
            device_id = str(alarm.device_id or "")
            if not device_id:
                continue
            if device_id not in result:
                result[device_id] = {"alarm_active": False, "alarm_count": 0}
            result[device_id]["alarm_active"] = True
            result[device_id]["alarm_count"] += 1
        return result

    def clear_device_alarms(self, device_id: str) -> int:
        """将设备最近1小时内的未审核报警标记为已复核（误报）.

        Args:
            device_id: 设备 ID。

        Returns:
            清除的报警数量。
        """
        cutoff = datetime.datetime.now(datetime.timezone.utc) - timedelta(hours=1)
        stmt = (
            select(Alarm)
            .where(Alarm.device_id == device_id)
            .where(Alarm.alarm_time >= cutoff)
            .where(Alarm.is_reviewed.is_(False))
        )
        alarms = list(self.session.exec(stmt).all())
        for alarm in alarms:
            alarm.is_reviewed = True
            alarm.review_status = ReviewStatus.MISSED
            alarm.reviewed_by = _REVIEWED_BY_MANUAL_CLEAR
            alarm.reviewed_at = datetime.datetime.now(datetime.timezone.utc)
            self.session.add(alarm)
        self.session.commit()
        return len(alarms)

    def trigger_manual_alarm(
        self,
        device_id: str,
        severity: str = "high",
        description: str = "手动触发报警",
    ) -> AlarmRespVO:
        """手动触发报警.

        根据 device_id 创建记录，severity/description 由前端传入，
        workshop/work_content 从设备表自动带出。

        Args:
            device_id: 设备 ID。
            severity: 严重级别。
            description: 报警描述。

        Returns:
            创建的告警信息。
        """
        device = self.session.exec(
            select(Device).where(Device.device_id == device_id)
        ).first()
        return self.create_alarm(
            device_id=device_id,
            severity=severity,
            description=description,
            note=device.workshop if device else "",
            type=device.work_content if device else "",
            type2=_MANUAL_ALARM_TYPE2,
        )

    def get_today_alarms(self) -> list[AlarmReviewItemVO]:
        """获取当天报警列表（用于报警复核页面）.

        Returns:
            前端期望格式的报警列表。
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = (
            select(Alarm)
            .where(Alarm.alarm_time >= start)
            .where(Alarm.source == AlarmSource.FIRE)
            .order_by(col(Alarm.alarm_time).desc())
        )
        alarms = list(self.session.exec(stmt).all())

        items: list[AlarmReviewItemVO] = []
        for a in alarms:
            alarm_time_str = a.alarm_time.strftime("%Y-%m-%d %H:%M:%S") if isinstance(a.alarm_time, datetime.datetime) else str(a.alarm_time)
            img_url = a.image_url or ""
            if img_url and not img_url.startswith("/"):
                img_url = "/" + img_url

            items.append(AlarmReviewItemVO(
                review_key=str(a.id),
                review_status=a.review_status or 0,
                image=img_url,
                type=a.type or "",
                type2=a.type2 or "",
                note=a.note or "",
                alarm_time=alarm_time_str,
                device_id=a.device_id,
                confidence=a.confidence,
            ))
        return items

    def get_alarm_stream_items(self, last_time: str = "", page_size: int = 20) -> list[AlarmStreamItemVO]:
        """获取报警事件增量列表（用于报警流轮询）.

        支持两种过滤机制：
        1. last_time：前端传入上次最新报警时间，返回该时间之后的报警
        2. _stream_cleared_at：reset_abnormal 后的全局时间点，只返回该点之后的报警

        Args:
            last_time: 上次最新报警的时间字符串（前端 fetchStream 传入）。
            page_size: 返回数量上限。

        Returns:
            前端期望格式的报警流列表（增量）。
        """
        global _stream_cleared_at
        stmt = select(Alarm).order_by(col(Alarm.alarm_time).desc())

        # 确定过滤时间点：取 last_time 和 _stream_cleared_at 中较新的那个
        effective_time = ""
        if last_time:
            effective_time = last_time
        if _stream_cleared_at:
            if not effective_time or _stream_cleared_at > effective_time:
                effective_time = _stream_cleared_at

        if effective_time:
            try:
                # 支持多种时间格式
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
                    try:
                        cutoff = datetime.datetime.strptime(effective_time, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    cutoff = None

                if cutoff:
                    stmt = stmt.where(Alarm.alarm_time > cutoff)
            except Exception as e:
                logger.warning(f"get_alarm_stream_items 时间解析失败: {e}")

        stmt = stmt.limit(page_size)
        alarms = list(self.session.exec(stmt).all())

        # 批量查询设备信息，填充负责人字段
        device_ids = list({a.device_id for a in alarms})
        device_map: dict[str, Device] = {}
        if device_ids:
            try:
                devices = list(self.session.exec(
                    select(Device).where(Device.device_id.in_(device_ids))
                ).all())
                for d in devices:
                    device_map[d.device_id] = d
            except Exception as e:
                logger.warning(f"get_alarm_stream_items 查询设备信息失败: {e}")

        return [
            AlarmStreamItemVO(
                idx=a.device_id or "",
                type=a.type or "",
                type2=a.type2 or "",
                note=a.note or "",
                alarm_time=str(a.alarm_time or ""),
                time=str(a.alarm_time or ""),
                image_url=a.image_url or "",
                img=a.image_url or "",
                # 快照优先，没有时回退到 Device 表当前值（兼容历史告警）
                device_manager=a.snapshot_device_manager or (dev.responsible_person if dev else "") or "",
                area_manager=a.snapshot_area_manager or (dev.area_manager if dev else "") or "",
                area_manager_phone=a.snapshot_area_manager_phone or (dev.area_manager_phone if dev else "") or "",
                owner=a.device_id or "",
                review_status=a.review_status or 0,
            )
            for a, dev in ((a, device_map.get(a.device_id)) for a in alarms)
        ]

    @staticmethod
    def reset_stream() -> None:
        """重置报警流：标记当前时间点，stream 只返回之后的新报警."""
        global _stream_cleared_at
        _stream_cleared_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def export_search_results_csv(self, records: list[dict]) -> str:
        """导出搜索结果为 CSV.

        Args:
            records: 搜索结果记录列表。

        Returns:
            CSV 内容字符串。
        """
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "相机序号", "报警区域", "安全类别", "报警描述",
            "设备负责人", "区域负责人", "时间", "复核状态"
        ])

        for item in records:
            writer.writerow([
                item.get("idx", ""),
                item.get("note", ""),
                item.get("type", ""),
                item.get("type2", ""),
                item.get("device_manager", ""),
                item.get("area_manager", ""),
                item.get("alarm_time", "") or item.get("time", ""),
                "已复核" if item.get("review_status") == 2 else "未复核",
            ])

        output.seek(0)
        return output.getvalue()
