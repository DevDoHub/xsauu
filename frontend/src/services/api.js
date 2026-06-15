/**
 * API 服务层
 *
 * 统一通过 axios 实例 + 拦截器封装请求：
 * - **成功**：拦截器解包为 ``{ error: false, data: <response.data> }``
 * - **失败**：拦截器解包为 ``{ error: true, message, code }``，**不抛异常**
 *
 * 调用方因此可以一行直返：``return http.get('/devices/...')``，
 * 不必写 try/catch。所有方法返回值结构与历史一致，调用点无需改动。
 *
 * Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9
 */
import axios from 'axios';

/**
 * 动态获取 baseUrl
 * 开发环境走 Vite proxy（/api），生产环境走相对路径
 * @returns {string} API 基础 URL
 */
const getBaseUrl = () => '/api';

/**
 * 把 axios error 格式化为业务统一错误对象。
 * @param {Error} error
 * @returns {{error: true, message: string, code?: number}}
 */
const handleApiError = (error) => {
  console.error('API Error:', error);
  return {
    error: true,
    message:
      error.response?.data?.error ||
      error.response?.data?.message ||
      error.message ||
      'Unknown error',
    code: error.response?.status,
  };
};

// ── 共用 axios 实例 + 拦截器 ─────────────────────────────────────────
const http = axios.create({ baseURL: getBaseUrl() });

http.interceptors.response.use(
  (response) => ({ error: false, data: response.data }),
  (error) => Promise.resolve(handleApiError(error)),
);

// 调用方写法：
//   const res = await http.get('/devices/count')
//   if (!res.error) console.log(res.data)
// 不会再抛异常 —— 拦截器把失败也包装成 resolved 值。

// 极少数端点后端用 ``{ data: ... }`` 双层包装，调用方期望直接拿到内层。
const unwrapData = (res) =>
  res.error ? res : { ...res, data: res.data?.data };

// ── 设备 ─────────────────────────────────────────────────────────────
export const deviceApi = {
  /** 按负责人分组（后端返回 { data: { 负责人: [设备] } }） */
  searchDevices: () => unwrapData(http.get('/devices/grouped/by-person')),

  /** 按区域负责人分组（后端返回 { data: { 区域: { 设备名: 设备 } } }） */
  searchDevicesByArea: () => unwrapData(http.get('/devices/grouped/by-area')),

  /** 设备 IP 映射 */
  getDeviceIp: () => http.get('/devices/ip-map'),

  /** 视频流 URL（不发请求，直接拼字符串） */
  getVideoFeedUrl: (deviceNumber) => `${getBaseUrl()}/video_feed/${deviceNumber}`,

  /** 设备总数 + 在线数 */
  getDeviceCount: () => http.get('/devices/count'),

  /** 分页设备列表 */
  listDevices: (page = 1, pageSize = 100) =>
    http.get('/devices/', { params: { page, page_size: Math.min(pageSize, 100) } }),

  /** 更新设备信息（按主键） */
  updateDevice: (devicePk, payload) => http.put(`/devices/${devicePk}`, payload),
};

// ── 摄像头控制 ───────────────────────────────────────────────────────
export const cameraApi = {
  /** 摄像头方向控制 */
  control: (direction, deviceId) =>
    http.post(`/devices/${encodeURIComponent(String(deviceId))}/control/camera`, {
      direction,
    }),
};

// ── 设备配置 ─────────────────────────────────────────────────────────
export const configApi = {
  getConfig: (deviceId) =>
    http.get(`/devices/${encodeURIComponent(String(deviceId))}/config`),

  updateConfig: (deviceId, payload) =>
    http.put(`/devices/${encodeURIComponent(String(deviceId))}/config`, payload),
};

// ── 报警 ─────────────────────────────────────────────────────────────
export const alarmApi = {
  /** 所有设备报警状态 */
  getStatus: () => http.get('/alarms/status'),

  /** 控制报警（clear/trigger） */
  control: (deviceId, action) =>
    http.post('/alarms/control', { device_id: deviceId, action }),

  /** 报警流（增量获取） */
  getStream: (lastTime = '') =>
    http.get('/alarms/stream', { params: { last_time: lastTime } }),

  /** 删除单条历史记录 */
  deleteAlarm: (idx, time, img = '') =>
    http.post('/alarms/delete_history_record', { idx, time, img }),

  /** 重置异常计数并清空报警列表 */
  resetAbnormal: () => http.post('/alarms/reset_abnormal'),

  /** 获取历史异常数据 */
  getAbnormalData: () => http.get('/alarms/abnormal_data'),

  /** 带违规信息的手动触发报警 */
  triggerWithViolation: (
    deviceId,
    { severity, description, image, note, type, type2 },
  ) =>
    http.post('/alarms/trigger', {
      device_id: deviceId,
      severity: severity || 'medium',
      description: description || '手动报警',
      image: image || '',
      note: note || '',
      type: type || '',
      type2: type2 || '手动报警',
    }),
};

// ── 检测控制 ─────────────────────────────────────────────────────────
export const detectionApi = {
  /** 全局开始 */
  start: () => http.post('/detections/control/global', { action: 'start' }),

  /** 全局停止 */
  stop: () => http.post('/detections/control/global', { action: 'stop' }),

  /** 单设备控制 */
  controlDevice: (deviceId, action) =>
    http.post(`/devices/${deviceId}/control/detection`, { action }),

  /** 批量设备控制 */
  controlBatch: (deviceIds, action) =>
    http.post('/detections/control/batch', { device_ids: deviceIds, action }),

  /** 按负责人批量控制 */
  controlByPerson: (person, action) =>
    http.post('/detections/control/by-person', { person, action }),
};

// ── 气体 ─────────────────────────────────────────────────────────────
export const gasApi = {
  getRealtime: () => http.get('/detections/gas/latest'),

  getThreshold: () => http.get('/detections/gas/threshold'),

  /** 气体监控页专用：一次获取 realtime + threshold + registry */
  getMonitorData: () => http.get('/detections/gas_monitor_data'),
};

// ── 人员 ─────────────────────────────────────────────────────────────
export const personApi = {
  getAll: () => http.get('/devices/persons'),
};

// ── 报警复核 ─────────────────────────────────────────────────────────
export const alarmReviewApi = {
  /** 当天报警复核数据 */
  getToday: () => http.get('/alarms/today'),

  /**
   * 更新报警复核状态
   * @param {string} reviewKey - 记录定位键
   * @param {number} reviewStatus - 0=未确定, 1=误报警, 2=确定报警
   */
  updateStatus: (reviewKey, reviewStatus) =>
    http.post('/alarms/update_status', {
      review_key: reviewKey,
      review_status: reviewStatus,
    }),

  /** 报警类别统计 */
  getTypeStats: (range = 'today') =>
    http.get('/alarms/type_stats', { params: { range } }),

  getFilterOptions: () => http.get('/alarms/filter_options'),
};

// ── 系统配置（兼容旧端点） ───────────────────────────────────────────
const systemConfigApi = {
  getConfig: () => http.get('/system/config_legacy'),

  updateConfig: (payload) => http.post('/system/config_legacy', payload),
};

// 导出（保持与历史一致，避免调用点改动）
export { getBaseUrl, handleApiError, systemConfigApi };

export default {
  device: deviceApi,
  camera: cameraApi,
  config: configApi,
  alarm: alarmApi,
  alarmReview: alarmReviewApi,
  detection: detectionApi,
  gas: gasApi,
  person: personApi,
  systemConfig: systemConfigApi,
  getBaseUrl,
  handleApiError,
};
