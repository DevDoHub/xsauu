/**
 * SSE (Server-Sent Events) 订阅 composable
 * 提供设备状态和气体数据的实时推送订阅
 */

import { ref, onUnmounted } from 'vue';
import { getBaseUrl } from '@/services/api';

/**
 * 创建 SSE 连接管理器
 * @param {string} endpoint - SSE 端点路径
 * @param {Object} options - 配置选项
 * @returns {Object} SSE 连接管理器
 */
function createSSEManager(endpoint, options = {}) {
  const {
    autoReconnect = true,
    reconnectInterval = 5000,
    maxReconnectAttempts = 10,
    onMessage = null,
    onError = null,
    onOpen = null,
    onClose = null,
  } = options;

  const data = ref(null);
  const isConnected = ref(false);
  const error = ref(null);
  const reconnectAttempts = ref(0);

  let eventSource = null;
  let reconnectTimer = null;

  /**
   * 建立 SSE 连接
   */
  function connect() {
    if (eventSource) {
      disconnect();
    }

    const baseUrl = getBaseUrl();
    const url = `${baseUrl}${endpoint}`;

    try {
      eventSource = new EventSource(url);

      eventSource.onopen = () => {
        isConnected.value = true;
        error.value = null;
        reconnectAttempts.value = 0;
        console.log(`SSE 连接已建立: ${endpoint}`);
        onOpen?.();
      };

      eventSource.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          data.value = parsed;
          onMessage?.(parsed);
        } catch (e) {
          console.error('SSE 消息解析失败:', e);
        }
      };

      eventSource.onerror = (event) => {
        isConnected.value = false;
        error.value = 'SSE 连接错误';
        console.error(`SSE 连接错误: ${endpoint}`, event);
        onError?.(event);

        // 自动重连
        if (autoReconnect && reconnectAttempts.value < maxReconnectAttempts) {
          reconnectAttempts.value++;
          console.log(`SSE 重连尝试 ${reconnectAttempts.value}/${maxReconnectAttempts}...`);
          reconnectTimer = setTimeout(() => {
            connect();
          }, reconnectInterval);
        }
      };
    } catch (e) {
      error.value = e.message;
      console.error('SSE 连接创建失败:', e);
    }
  }

  /**
   * 断开 SSE 连接
   */
  function disconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }

    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }

    isConnected.value = false;
    onClose?.();
  }

  /**
   * 重新连接
   */
  function reconnect() {
    disconnect();
    reconnectAttempts.value = 0;
    connect();
  }

  return {
    data,
    isConnected,
    error,
    reconnectAttempts,
    connect,
    disconnect,
    reconnect,
  };
}

/**
 * 设备状态 SSE 订阅
 * @param {Object} options - 配置选项
 * @returns {Object} 设备状态订阅管理器
 */
export function useDeviceStatusSSE(options = {}) {
  const deviceStatuses = ref({});
  const latestUpdate = ref(null);

  const manager = createSSEManager('/detections/device-status/events', {
    ...options,
    onMessage: (data) => {
      latestUpdate.value = data;
      if (data.device_id) {
        deviceStatuses.value = {
          ...deviceStatuses.value,
          [data.device_id]: data,
        };
      }
      options.onMessage?.(data);
    },
  });

  /**
   * 获取指定设备状态
   * @param {string} deviceId - 设备ID
   * @returns {Object|null} 设备状态
   */
  function getDeviceStatus(deviceId) {
    return deviceStatuses.value[deviceId] || null;
  }

  /**
   * 获取所有在线设备
   * @returns {string[]} 在线设备ID列表
   */
  function getOnlineDevices() {
    return Object.entries(deviceStatuses.value)
      .filter(([, status]) => status.is_online)
      .map(([deviceId]) => deviceId);
  }

  return {
    ...manager,
    deviceStatuses,
    latestUpdate,
    getDeviceStatus,
    getOnlineDevices,
  };
}

/**
 * 气体数据 SSE 订阅
 * @param {Object} options - 配置选项
 * @returns {Object} 气体数据订阅管理器
 */
export function useGasDataSSE(options = {}) {
  const gasDataMap = ref({});
  const latestUpdate = ref(null);

  const manager = createSSEManager('/detections/gas/events', {
    ...options,
    onMessage: (data) => {
      latestUpdate.value = data;
      if (data.device_id) {
        gasDataMap.value = {
          ...gasDataMap.value,
          [data.device_id]: data,
        };
      }
      options.onMessage?.(data);
    },
  });

  /**
   * 获取指定设备气体数据
   * @param {string} deviceId - 设备ID
   * @returns {Object|null} 气体数据
   */
  function getDeviceGasData(deviceId) {
    return gasDataMap.value[deviceId] || null;
  }

  /**
   * 获取所有设备气体数据
   * @returns {Object} 气体数据映射
   */
  function getAllGasData() {
    return { ...gasDataMap.value };
  }

  return {
    ...manager,
    gasDataMap,
    latestUpdate,
    getDeviceGasData,
    getAllGasData,
  };
}

/**
 * 检测框数据 SSE 订阅
 * @param {Object} options - 配置选项
 * @returns {Object} 检测框数据订阅管理器
 */
export function useDetectionSSE(options = {}) {
  const detectionsMap = ref({});
  const latestUpdate = ref(null);

  const manager = createSSEManager('/detections/events', {
    ...options,
    onMessage: (data) => {
      latestUpdate.value = data;
      if (data.device_name) {
        detectionsMap.value = {
          ...detectionsMap.value,
          [data.device_name]: data,
        };
      }
      options.onMessage?.(data);
    },
  });

  /**
   * 获取指定设备检测框数据
   * @param {string} deviceName - 设备名称
   * @returns {Object|null} 检测框数据
   */
  function getDeviceDetection(deviceName) {
    return detectionsMap.value[deviceName] || null;
  }

  return {
    ...manager,
    detectionsMap,
    latestUpdate,
    getDeviceDetection,
  };
}

/**
 * 告警数据 SSE 订阅
 * @param {Object} options - 配置选项
 * @returns {Object} 告警数据订阅管理器
 */
export function useAlarmSSE(options = {}) {
  const alarms = ref([]);
  const latestAlarm = ref(null);

  const manager = createSSEManager('/detections/alarm/events', {
    ...options,
    onMessage: (data) => {
      latestAlarm.value = data;
      // 添加到告警列表（最新的在前面）
      alarms.value = [data, ...alarms.value].slice(0, 100); // 最多保留100条
      options.onMessage?.(data);
    },
  });

  /**
   * 获取告警列表
   * @param {number} limit - 返回数量限制
   * @returns {Array} 告警列表
   */
  function getAlarms(limit = 50) {
    return alarms.value.slice(0, limit);
  }

  /**
   * 按设备ID筛选告警
   * @param {string} deviceId - 设备ID
   * @returns {Array} 该设备的告警列表
   */
  function getAlarmsByDevice(deviceId) {
    return alarms.value.filter(a => a.device_id === deviceId);
  }

  /**
   * 清除告警历史
   */
  function clearAlarms() {
    alarms.value = [];
  }

  return {
    ...manager,
    alarms,
    latestAlarm,
    getAlarms,
    getAlarmsByDevice,
    clearAlarms,
  };
}

export default {
  useDeviceStatusSSE,
  useGasDataSSE,
  useDetectionSSE,
  useAlarmSSE,
};
