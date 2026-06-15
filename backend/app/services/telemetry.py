"""遥测数据业务逻辑层."""

from collections import defaultdict

from sqlmodel import Session, select, func, col

from app.models.telemetry import Telemetry
from app.schemas.telemetry import TelemetryRespVO, TelemetryListRespVO


class TelemetryService:
    """遥测数据 Service."""

    def __init__(self, session: Session):
        self.session = session

    def save_telemetry(
        self,
        device_id: str,
        sensor_type: str,
        value: float,
        unit: str = "",
        is_overlimit: bool = False,
        threshold: float | None = None,
    ) -> Telemetry:
        """保存遥测数据."""
        telemetry = Telemetry(
            device_id=device_id,
            sensor_type=sensor_type,
            value=value,
            unit=unit,
            is_overlimit=is_overlimit,
            threshold=threshold,
        )
        self.session.add(telemetry)
        self.session.commit()
        self.session.refresh(telemetry)
        return telemetry

    def list_telemetry(
        self,
        *,
        page: int = 1,
        page_size: int = 100,
        device_id: str | None = None,
        sensor_type: str | None = None,
    ) -> TelemetryListRespVO:
        """分页查询遥测数据."""
        skip = (page - 1) * page_size
        stmt = select(Telemetry)
        total_stmt = select(func.count()).select_from(Telemetry)

        if device_id:
            stmt = stmt.where(Telemetry.device_id == device_id)
            total_stmt = total_stmt.where(Telemetry.device_id == device_id)
        if sensor_type:
            stmt = stmt.where(Telemetry.sensor_type == sensor_type)
            total_stmt = total_stmt.where(Telemetry.sensor_type == sensor_type)

        items = list(
            self.session.exec(
                stmt.order_by(col(Telemetry.created_at).desc()).offset(skip).limit(page_size)
            ).all()
        )
        total = self.session.exec(total_stmt).one()

        return TelemetryListRespVO(
            total=total,
            items=[TelemetryRespVO.model_validate(t) for t in items],
            page=page,
            page_size=page_size,
        )

    def get_realtime(self) -> dict:
        """获取所有设备的最新遥测数据（按设备分组）.

        返回格式：
        {
            "device_id_1": {
                "gas_co": {"value": 23.5, "unit": "ppm", "is_overlimit": false, "threshold": 50.0, "time": "..."},
                "temperature": {"value": 25.0, "unit": "℃", ...}
            }
        }
        """
        # 子查询：每个设备每个传感器类型的最大 ID（即最新记录）
        subq = (
            select(
                Telemetry.device_id,
                Telemetry.sensor_type,
                func.max(Telemetry.id).label("max_id"),
            )
            .group_by(Telemetry.device_id, Telemetry.sensor_type)
        ).subquery()

        stmt = (
            select(Telemetry)
            .join(subq, Telemetry.id == subq.c.max_id)
        )
        results = list(self.session.exec(stmt).all())

        grouped = defaultdict(dict)
        for t in results:
            grouped[t.device_id][t.sensor_type] = {
                "value": t.value,
                "unit": t.unit,
                "is_overlimit": t.is_overlimit,
                "threshold": t.threshold,
                "time": (t.created_at.replace(tzinfo=datetime.timezone.utc).isoformat() if t.created_at and t.created_at.tzinfo is None else (t.created_at.isoformat() if t.created_at else None)),
            }

        return dict(grouped)

    def get_history(
        self,
        device_id: str,
        sensor_type: str | None = None,
        hours: int = 24,
    ) -> list[TelemetryRespVO]:
        """获取设备遥测历史数据."""
        from datetime import datetime, timedelta, timezone
        
        start = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        stmt = (
            select(Telemetry)
            .where(Telemetry.device_id == device_id)
            .where(Telemetry.created_at >= start)
        )
        if sensor_type:
            stmt = stmt.where(Telemetry.sensor_type == sensor_type)
        
        stmt = stmt.order_by(col(Telemetry.created_at).asc())
        items = list(self.session.exec(stmt).all())
        return [TelemetryRespVO.model_validate(t) for t in items]
