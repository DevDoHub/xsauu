/**
 * 检测框订阅 composable
 * 用于接收 SSE 推送的实时检测框数据
 */
import { ref, onMounted, onBeforeUnmount } from 'vue';

/**
 * 检测框订阅 hook
 * @param {Object} options 配置选项
 * @param {string} options.url SSE 端点地址
 * @param {Function} options.onDetection 收到检测框数据的回调
 * @param {boolean} options.autoConnect 是否自动连接
 * @returns {Object} { detections, connected, connect, disconnect }
 */
export function useDetectionStream(options = {}) {
  const {
    url = '/api/detections/events',
    onDetection = null,
    autoConnect = true,
  } = options;

  // 所有设备的最新检测框 { deviceName: payload }
  const detections = ref({});
  
  // 连接状态
  const connected = ref(false);
  
  // EventSource 实例
  let eventSource = null;

  /**
   * 连接 SSE 流
   */
  function connect() {
    if (eventSource) {
      disconnect();
    }

    eventSource = new EventSource(url);

    eventSource.onopen = () => {
      connected.value = true;
      console.log('[DetectionStream] SSE 连接已建立');
    };

    eventSource.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        const deviceName = payload.device_name;
        
        // 更新检测框状态
        detections.value = {
          ...detections.value,
          [deviceName]: payload,
        };

        // 调用回调
        if (onDetection) {
          onDetection(payload);
        }
      } catch (e) {
        console.error('[DetectionStream] 解析数据失败:', e);
      }
    };

    eventSource.onerror = (e) => {
      console.error('[DetectionStream] SSE 连接错误:', e);
      connected.value = false;
      
      // 自动重连（EventSource 内置重连机制）
      // 但如果是 403/404 等非网络错误，需要手动关闭
      if (eventSource.readyState === EventSource.CLOSED) {
        console.log('[DetectionStream] 连接已关闭，5秒后重连...');
        setTimeout(connect, 5000);
      }
    };
  }

  /**
   * 断开 SSE 连接
   */
  function disconnect() {
    if (eventSource) {
      eventSource.close();
      eventSource = null;
      connected.value = false;
      console.log('[DetectionStream] SSE 连接已断开');
    }
  }

  /**
   * 获取指定设备的检测框
   * @param {string} deviceName 设备名
   * @returns {Object|null} 检测框数据
   */
  function getDeviceDetections(deviceName) {
    return detections.value[deviceName] || null;
  }

  /**
   * 清除所有检测框
   */
  function clearDetections() {
    detections.value = {};
  }

  // 生命周期
  onMounted(() => {
    if (autoConnect) {
      connect();
    }
  });

  onBeforeUnmount(() => {
    disconnect();
  });

  return {
    detections,
    connected,
    connect,
    disconnect,
    getDeviceDetections,
    clearDetections,
  };
}
