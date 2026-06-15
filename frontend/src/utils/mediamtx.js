/**
 * mediamtx 相关配置
 * 用于 WebRTC 视频播放
 */

/**
 * 获取 mediamtx WebRTC 基地址
 *
 * WHEP 协议必须**直连** mediamtx，不能走 Vite proxy（涉及 ICE/UDP）。
 * 所以这里用「当前页面的 hostname + 8889」拼地址：
 *   - 电脑本机访问 http://localhost:5173 → http://localhost:8889
 *   - 手机/局域网访问 http://192.168.x.x:5173 → http://192.168.x.x:8889
 * 这样无需为每台终端单独配 .env。
 *
 * 也允许用 VITE_MEDIAMTX_URL 显式覆盖（如部署到带域名的环境）。
 *
 * @returns {string} mediamtx WebRTC 服务基地址（不含末尾斜杠）
 */
export function getMediamtxBaseUrl() {
  if (import.meta.env.VITE_MEDIAMTX_URL) {
    return import.meta.env.VITE_MEDIAMTX_URL;
  }
  // 浏览器环境下用当前页面的 hostname，避免硬编码 localhost
  if (typeof window !== 'undefined' && window.location?.hostname) {
    const { protocol, hostname } = window.location;
    // mediamtx WHEP 默认 HTTP(8889) / HTTPS(8889 也可，按部署而定）
    return `${protocol}//${hostname}:8889`;
  }
  return 'http://localhost:8889';
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
