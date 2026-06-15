/**
 * 常量定义文件
 * 集中管理应用中使用的常量
 * Requirements: 10.5
 */

/**
 * 默认图片路径
 * 用于未连接或无视频源的摄像头显示
 */
export const DEFAULT_IMAGE = new URL('@/assets/img/5.jpg', import.meta.url).href;

/**
 * @deprecated 动态槽位已在 Phase 3 实现，images 数组长度 = 在线设备数。
 * 保留仅为向后兼容，新代码不应引用此常量。
 */
export const TOTAL_CAMERA_SLOTS = 36;

/**
 * 显示模式枚举
 */
export const DISPLAY_MODES = {
  ONE: 'one',
  FOUR: 'four',
  NINE: 'nine',
  SIXTEEN: 'sixteen',
};

/**
 * 显示模式对应的单元格数量
 */
export const DISPLAY_MODE_CELLS = {
  [DISPLAY_MODES.ONE]: 1,
  [DISPLAY_MODES.FOUR]: 4,
  [DISPLAY_MODES.NINE]: 9,
  [DISPLAY_MODES.SIXTEEN]: 16,
};

/**
 * 设备连接状态
 */
export const DEVICE_STATUS = {
  DISCONNECTED: 0,
  CONNECTING: 1,
  CONNECTED: 2,
};

/**
 * 摄像头控制方向
 */
export const CAMERA_DIRECTIONS = {
  UP: 'up',
  DOWN: 'down',
  LEFT: 'left',
  RIGHT: 'right',
  AUTO: 'auto',
  STOP: 'stop',
  ZOOM_IN: 'zoom_in',
  ZOOM_OUT: 'zoom_out',
  RECONNECT: 'reconnect',
  DISCONNECT: 'disconnect',
};

/**
 * 报警控制操作
 */
export const ALARM_ACTIONS = {
  CLEAR: 'clear',
  TRIGGER: 'trigger',
};

/**
 * 置信度调整步长
 */
export const CONFIDENCE_STEP = 0.05;

/**
 * 置信度范围
 */
export const CONFIDENCE_RANGE = {
  MIN: 0.0,
  MAX: 1.0,
};

/**
 * 轮询间隔（毫秒）
 */
export const POLLING_INTERVALS = {
  DEVICE: 3000,        // 设备状态轮询
  ALARM_STATUS: 500,   // 报警状态轮询
  GAS_DATA: 1000,      // 气体数据轮询
  GAS_THRESHOLD: 5000, // 气体阈值轮询
  STREAM: 1000,        // 报警流轮询
  DEVICE_IP: 10000,    // 设备IP轮询
  VIDEO_STREAM: 1000,  // 视频流更新
};

/**
 * 气体类型
 */
export const GAS_TYPES = {
  CH4: 'CH4',
  CO: 'CO',
  H2S: 'H2S',
  O2: 'O2',
};

/**
 * 格式化气体数据显示
 * @param {Object} data - 气体数据对象
 * @returns {string} 格式化后的字符串
 */
export const formatGasData = (data) => {
  if (!data || typeof data !== 'object') {
    return 'null';
  }

  if (!data.data) {
    return JSON.stringify(data, null, 2);
  }

  const temperature = `${data.data.temp_int}.${data.data.temp_dec}`;
  const humidity = `${data.data.humi_int}.${data.data.humi_dec}`;

  const ip = `IP: ${data.IP}`;
  const gasConcentration = `CH4: ${data.data.CH4}, CO: ${data.data.CO}\nH2S: ${data.data.H2S}, O2: ${data.data.O2}`;
  const environmentalData = `温度：${temperature}，湿度：${humidity}`;

  return `${ip}\n${gasConcentration}\n${environmentalData}`;
};

export default {
  DEFAULT_IMAGE,
  TOTAL_CAMERA_SLOTS,
  DISPLAY_MODES,
  DISPLAY_MODE_CELLS,
  DEVICE_STATUS,
  CAMERA_DIRECTIONS,
  ALARM_ACTIONS,
  CONFIDENCE_STEP,
  CONFIDENCE_RANGE,
  POLLING_INTERVALS,
  GAS_TYPES,
  formatGasData,
};
