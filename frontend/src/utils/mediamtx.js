/**
 * mediamtx 相关配置
 * 用于 WebRTC 视频播放
 */

/**
 * 获取 mediamtx WebRTC 基地址
 * 开发环境通过代理，生产环境根据实际部署配置
 */
export function getMediamtxBaseUrl() {
  // 直接访问 mediamtx 的 WebRTC 端口（8889）
  // WHEP 协议需要直接连接，不能通过代理
  return import.meta.env.VITE_MEDIAMTX_URL || 'http://localhost:8889';
}

/**
 * 设备ID到 mediamtx 路径的映射规则
 *
 * 设计：path = device_id = device_name (单一身份源)
 *   - 边缘端 system_config.json 的 device.device_name 是唯一来源
 *   - 后端 register_device 时把 device_id 同时作为 mediamtx path 名注册
 *   - 前端 WHEP 拉流路径 = device_id
 *
 * 如果某些设备的 mediamtx_path 与 device_id 不同（历史遗留），
 * 优先使用后端 Device 模型返回的 mediamtx_path 字段，而不是这里的派生函数。
 */
export function deviceIdToPath(deviceId) {
  return deviceId;
}

/**
 * 从后端 API 获取在线路径列表
 * 后端会代理 mediamtx API，避免 CORS 问题
 * @returns {Promise<Array>} 路径列表
 */
export async function fetchOnlinePaths() {
  try {
    // 使用后端代理接口
    const res = await fetch('/api/mediamtx/paths');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data.items || [];
  } catch (e) {
    console.error('无法获取 mediamtx 路径列表:', e);
    return [];
  }
}

/**
 * 获取 mediamtx 配置信息
 * @returns {Promise<Object>} 配置信息
 */
export async function fetchMediamtxConfig() {
  try {
    const res = await fetch('/api/mediamtx/config');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    console.error('无法获取 mediamtx 配置:', e);
    return null;
  }
}
