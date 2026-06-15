"""MQTT 订阅模块.

负责连接 MQTT Broker，订阅边缘端上报的告警、遥测、心跳消息。
"""

import json
import threading

import paho.mqtt.client as mqtt
from loguru import logger

from app.settings import settings


class MQTTSubscriber:
    """MQTT 订阅管理器.

    在 FastAPI lifespan 中启停，独立线程运行。
    消息通过回调分发给 handler 模块处理。
    """

    def __init__(self):
        self.client: mqtt.Client | None = None
        self._thread: threading.Thread | None = None
        self._handlers: dict[str, callable] = {}

    def on_message(self, topic: str, payload: dict) -> None:
        """消息分发入口，由 handler 模块注册回调."""
        for pattern, handler in self._handlers.items():
            if mqtt.topic_matches_sub(pattern, topic):
                try:
                    handler(topic, payload)
                except Exception as e:
                    logger.error(f"MQTT 消息处理异常 [{topic}]: {e}")

    def register_handler(self, topic_pattern: str, handler) -> None:
        """注册消息处理器."""
        self._handlers[topic_pattern] = handler

    def publish(self, topic: str, payload: dict, qos: int = 1) -> None:
        """发布 MQTT 消息.

        用于向边缘端发送控制命令。
        """
        if not self.client:
            logger.error("MQTT 客户端未初始化，无法发布消息")
            return
        try:
            payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            result = self.client.publish(topic, payload_bytes, qos=qos)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"MQTT 发布 [{topic}]: {payload}")
            else:
                logger.error(f"MQTT 发布失败 [{topic}]: rc={result.rc}")
        except Exception as e:
            logger.error(f"MQTT 发布异常 [{topic}]: {e}")

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            logger.info("MQTT 连接成功")
            # 订阅所有配置的 topic
            topics = [
                (settings.MQTT_TOPIC_ALARM, 1),
                (settings.MQTT_TOPIC_TELEMETRY, 1),
                (settings.MQTT_TOPIC_HEARTBEAT, 0),
            ]
            client.subscribe(topics)
            for topic, qos in topics:
                logger.info(f"MQTT 已订阅: {topic} (QoS {qos})")
        else:
            logger.error(f"MQTT 连接失败，返回码: {rc}")

    def _on_disconnect(self, client, userdata, rc, properties=None):
        logger.warning(f"MQTT 断开连接 (rc={rc})，将自动重连...")

    def _on_message(self, client, userdata, msg: mqtt.MQTTMessage):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = {"raw": msg.payload.decode("utf-8", errors="replace")}

        logger.debug(f"MQTT 收到 [{msg.topic}]: {payload}")
        self.on_message(msg.topic, payload)

    def start(self) -> bool:
        """启动 MQTT 客户端（在独立线程中运行）.

        Returns:
            ``True`` 表示连接成功并已启动后台线程；``False`` 表示
            初次连接失败（paho 内部仍会自动重连）。
        """
        self.client = mqtt.Client(
            client_id=settings.MQTT_CLIENT_ID,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )

        if settings.MQTT_USERNAME:
            self.client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        # 自动重连
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)

        try:
            self.client.connect(settings.MQTT_BROKER_HOST, settings.MQTT_BROKER_PORT, keepalive=60)
            self._thread = threading.Thread(target=self.client.loop_forever, daemon=True)
            self._thread.start()
            return True
        except Exception as e:
            logger.warning(f"MQTT 连接失败（将自动重连）: {e}")
            return False

    def stop(self) -> None:
        """停止 MQTT 客户端."""
        if self.client:
            self.client.disconnect()
            self.client.loop_stop()
            logger.info("MQTT 客户端已停止")


# 全局单例
mqtt_subscriber = MQTTSubscriber()
