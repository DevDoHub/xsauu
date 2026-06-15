/**
 * 设备订阅 composable
 *
 * 根据当前显示模式和翻页索引计算可见设备 ID，
 * 然后通过 SocketIO 发送 subscribe_devices 事件，
 * 使后端仅为当前可见设备维护 MJPEG 帧队列。
 */
import { DISPLAY_MODE_CELLS } from '@/utils/constants'

export function useDeviceSubscription(socketRef) {
  /**
   * 向后端发送当前可见设备订阅
   * @param {string[]} visibleCamIds - 当前可见的 cam_id 列表
   */
  function subscribe(visibleCamIds) {
    if (socketRef.value && socketRef.value.connected) {
      socketRef.value.emit('subscribe_devices', { cam_ids: visibleCamIds })
    }
  }

  /**
   * 根据显示模式、翻页索引和映射表，计算当前可见的 cam_id 列表
   * @param {string} mode - 显示模式 ('one'/'four'/'nine')
   * @param {number} startIndex - 当前页起始索引
   * @param {Object} displayIndexToDeviceId - 索引→设备ID映射
   * @returns {string[]} 可见的 cam_id 列表
   */
  function computeVisible(mode, startIndex, displayIndexToDeviceId) {
    const cellCount = DISPLAY_MODE_CELLS[mode] || 9
    const ids = []
    for (let i = startIndex; i < startIndex + cellCount; i++) {
      const id = displayIndexToDeviceId[i]
      if (id !== undefined && id !== null) {
        ids.push(String(id))
      }
    }
    return ids
  }

  return { subscribe, computeVisible }
}
