/**
 * 报警状态管理模块
 * 管理报警状态、报警列表和消息队列
 * Requirements: 8.2, 8.6, 8.7, 8.8
 */
import { alarmApi } from '@/services/api';

export default {
  namespaced: true,

  state: () => ({
    // 所有设备的报警状态 { [deviceId]: { alarm_active: boolean, last_alarm_time?: string } }
    alarmStatus: {},
    // 报警事件列表
    alarmList: [],
    // 消息队列（用于弹窗显示）
    messageQueue: [],
    // 上次获取的最新时间（用于增量获取）
    lastTime: '',
    // 加载状态
    loading: false,
    // 错误信息
    error: null,
  }),

  mutations: {
    /**
     * 设置所有设备的报警状态
     */
    SET_ALARM_STATUS(state, status) {
      state.alarmStatus = status;
    },

    /**
     * 增量更新报警状态（SocketIO 推送）
     * @param {Object} patch - { cam_id: { alarm_active, last_update } }
     */
    PATCH_ALARM_STATUS(state, patch) {
      state.alarmStatus = { ...state.alarmStatus, ...patch };
    },

    /**
     * 添加新报警到列表顶部
     */
    ADD_ALARM(state, alarm) {
      state.alarmList.unshift(alarm);
    },

    /**
     * 批量添加报警
     */
    ADD_ALARMS(state, alarms) {
      alarms.forEach((alarm) => {
        state.alarmList.unshift(alarm);
      });
    },

    /**
     * 清空报警列表
     */
    CLEAR_ALARMS(state) {
      state.alarmList = [];
    },

    /**
     * 从列表中移除指定报警
     */
    REMOVE_ALARM(state, { index, time }) {
      state.alarmList = state.alarmList.filter(
        (item) => !(item.index === index && item.time === time)
      );
    },

    /**
     * 添加消息到队列
     */
    ADD_TO_QUEUE(state, message) {
      state.messageQueue.push(message);
    },

    /**
     * 从队列中移除第一条消息
     */
    SHIFT_QUEUE(state) {
      state.messageQueue.shift();
    },

    /**
     * 清空消息队列
     */
    CLEAR_QUEUE(state) {
      state.messageQueue = [];
    },

    /**
     * 更新上次获取时间
     */
    SET_LAST_TIME(state, time) {
      state.lastTime = time;
    },

    /**
     * 设置加载状态
     */
    SET_LOADING(state, loading) {
      state.loading = loading;
    },

    /**
     * 设置错误信息
     */
    SET_ERROR(state, error) {
      state.error = error;
    },
  },

  actions: {
    /**
     * 获取所有设备的报警状态
     */
    async fetchAlarmStatus({ commit }) {
      const result = await alarmApi.getStatus();

      if (!result.error && result.data) {
        commit('SET_ALARM_STATUS', result.data);
      }

      return result;
    },

    /**
     * 清除指定设备的报警
     */
    async clearAlarm({ dispatch }, deviceId) {
      const result = await alarmApi.control(deviceId, 'clear');

      if (!result.error) {
        // 立即刷新报警状态
        await dispatch('fetchAlarmStatus');
      }

      return result;
    },

    /**
     * 触发指定设备的报警
     */
    async triggerAlarm({ dispatch }, deviceId) {
      const result = await alarmApi.control(deviceId, 'trigger');

      if (!result.error) {
        // 立即刷新报警状态
        await dispatch('fetchAlarmStatus');
        // 立即刷新报警流列表
        await dispatch('fetchStream');
      }

      return result;
    },

    /**
     * 带违规信息的报警触发
     *
     * ⚠️ 不再在此处本地 push 报警条目：
     * 后端创建报警后会通过 SSE 广播（applyAlarmStreamPush 是唯一事实来源），
     * 在这里再用客户端本地时间临时 push 一条，会因 time 字段不一致而无法和
     * SSE 推送的同一条记录去重，导致"最新报警事件"列表出现两条重复项。
     *
     * @param {Object} payload - 包含 deviceId, alarmType, alarmTypeLabel, severity, description, image, note, type, type2
     */
    async triggerAlarmWithViolation({ dispatch }, { deviceId, alarmType, alarmTypeLabel, severity, description, image, note, type, type2 }) {
      const result = await alarmApi.triggerWithViolation(deviceId, { alarmType, severity, description, image, note, type, type2 });

      if (!result.error) {
        // 仅刷新报警状态（红色闪烁/小红点等），列表条目由 SSE 推送统一负责
        await dispatch('fetchAlarmStatus');
      }

      return result;
    },

    /**
     * 获取报警流数据（增量获取）
     * 兼容新后端 JSON 数组格式和旧后端文本格式
     */
    async fetchStream({ commit, state }) {
      const result = await alarmApi.getStream(state.lastTime);

      if (result.error || !result.data) {
        return result;
      }

      const newAlarms = [];

      // ---- 新后端：JSON 数组格式 ----
      if (Array.isArray(result.data)) {
        result.data.forEach((item) => {
          const index = String(item.idx ?? '');
          const time = String(item.alarm_time || (item.time ?? ''));
          const exists = state.alarmList.some(
            (alarm) => alarm.index === index && alarm.time === time
          );
          if (!exists && index) {
            newAlarms.push({
              image: item.image_url || item.img || '',
              index,
              note: item.note || '',
              type2: item.type2 || '',
              type: item.type || '',
              deviceManager: item.device_manager || '',
              areaManager: item.area_manager || '',
              areaManagerPhone: item.area_manager_phone || '',
              time,
            });
            if (time && time > state.lastTime) {
              commit('SET_LAST_TIME', time);
            }
          }
        });
      } else if (typeof result.data === 'string' && result.data.trim() !== '') {
        // ---- 旧后端：文本格式（兼容） ----
        const imageDataList = result.data.split('\n\n').filter((item) => item.trim() !== '');

        imageDataList.forEach((item) => {
          const lines = item.split('\n');

          // 至少需要6行数据
          if (lines.length >= 6) {
            let image, index, note, type2, type, deviceManager, areaManager, areaManagerPhone, time;

            const firstLine = lines[0].trim();
            if (firstLine.startsWith('data:image')) {
              // 有图片数据
              image = firstLine;
              index = lines[1].split('idx:')[1];
              note = lines[2].split('note:')[1];
              type2 = lines[3].split('type2:')[1];
              type = lines[4].split('type:')[1];
              deviceManager = lines[5]?.split('device_manager:')[1] || '';
              areaManager = lines[6]?.split('area_manager:')[1] || '';
              areaManagerPhone = lines[7]?.split('area_manager_phone:')[1] || '';
              time = lines[8]?.split('time:')[1];
            } else if (firstLine === '' || !firstLine.startsWith('idx:')) {
            // 第一行为空或不是idx开头
            image = '';
            if (lines[1] && lines[1].includes('idx:')) {
              index = lines[1].split('idx:')[1];
              note = lines[2].split('note:')[1];
              type2 = lines[3].split('type2:')[1];
              type = lines[4].split('type:')[1];
              deviceManager = lines[5]?.split('device_manager:')[1] || '';
              areaManager = lines[6]?.split('area_manager:')[1] || '';
              areaManagerPhone = lines[7]?.split('area_manager_phone:')[1] || '';
              time = lines[8]?.split('time:')[1];
            } else {
              index = lines[0].split('idx:')[1];
              note = lines[1].split('note:')[1];
              type2 = lines[2].split('type2:')[1];
              type = lines[3].split('type:')[1];
              deviceManager = lines[4]?.split('device_manager:')[1] || '';
              areaManager = lines[5]?.split('area_manager:')[1] || '';
              areaManagerPhone = lines[6]?.split('area_manager_phone:')[1] || '';
              time = lines[7]?.split('time:')[1];
            }
          } else {
            // 无image字段，直接从idx开始
            image = '';
            index = lines[0].split('idx:')[1];
            note = lines[1].split('note:')[1];
            type2 = lines[2].split('type2:')[1];
            type = lines[3].split('type:')[1];
            deviceManager = lines[4]?.split('device_manager:')[1] || '';
            areaManager = lines[5]?.split('area_manager:')[1] || '';
            areaManagerPhone = lines[6]?.split('area_manager_phone:')[1] || '';
            time = lines[7]?.split('time:')[1];
          }


          // 检查是否已存在
          const exists = state.alarmList.some(
            (alarm) => alarm.index === index && alarm.time === time
          );

          if (!exists) {
            const newAlarm = {
              image,
              index,
              note,
              type2,
              type,
              deviceManager,
              areaManager,
              areaManagerPhone,
              time
            };

            newAlarms.push(newAlarm);

            // 更新 lastTime
            if (time && time > state.lastTime) {
              commit('SET_LAST_TIME', time);
            }
          }
        }
      });
      }

      // 批量添加新报警
      if (newAlarms.length > 0) {
        commit('ADD_ALARMS', newAlarms);
        // 同时添加到消息队列
        newAlarms.forEach((alarm) => {
          commit('ADD_TO_QUEUE', alarm);
        });
      }

      return { error: false, data: newAlarms };
    },

    /**
     * 删除指定报警记录
     */
    async deleteAlarm({ commit }, { index, time }) {
      const result = await alarmApi.deleteAlarm(index, time);

      if (!result.error && result.data?.status === 'success') {
        commit('REMOVE_ALARM', { index, time });
      }

      return result;
    },

    /**
     * 应用推送的报警状态增量更新
     */
    applyAlarmPush({ commit }, payload) {
      if (!payload || payload.schema_version !== 1) {
        console.warn('[alarms] unknown schema_version, ignoring push', payload);
        return;
      }
      commit('PATCH_ALARM_STATUS', payload.data);
    },

    /**
     * 应用推送的报警流更新
     */
    applyAlarmStreamPush({ commit, state }, payload) {
      if (!payload || payload.schema_version !== 1) {
        console.warn('[alarms] unknown schema_version for stream, ignoring', payload);
        return;
      }
      // 兼容单条对象和数组
      const records = Array.isArray(payload.data) ? payload.data : [payload.data];
      const newAlarms = [];
      records.forEach((record) => {
        if (!record) return;
        const alarm = {
          image: record.image_url || record.image || '',
          index: String(record.device_id || record.idx || ''),
          note: String(record.note || ''),
          type2: String(record.type2 || ''),
          type: String(record.type || ''),
          deviceManager: String(record.device_manager || ''),
          areaManager: String(record.area_manager || ''),
          areaManagerPhone: String(record.area_manager_phone || ''),
          time: String(record.alarm_time || record.time || '')
        };
        const exists = state.alarmList.some(
          (a) => a.index === alarm.index && a.time === alarm.time
        );
        if (!exists) {
          newAlarms.push(alarm);
          if (alarm.time && alarm.time > state.lastTime) {
            commit('SET_LAST_TIME', alarm.time);
          }
        }
      });
      if (newAlarms.length > 0) {
        commit('ADD_ALARMS', newAlarms);
        newAlarms.forEach((alarm) => commit('ADD_TO_QUEUE', alarm));
      }
    },

    /**
     * 重置异常计数并清空报警列表
     */
    async resetAbnormal({ commit }) {
      const result = await alarmApi.resetAbnormal();

      // 无论成功与否都清空列表
      commit('CLEAR_ALARMS');
      commit('CLEAR_QUEUE');
      commit('SET_LAST_TIME', '');

      return result;
    },

    /**
     * 确认当前消息（从队列中移除）
     */
    confirmMessage({ commit }) {
      commit('SHIFT_QUEUE');
    },

    /**
     * 删除并确认当前消息
     */
    async deleteAndConfirm({ commit, dispatch, state }) {
      if (state.messageQueue.length > 0) {
        const current = state.messageQueue[0];
        await dispatch('deleteAlarm', { index: current.index, time: current.time });
        commit('SHIFT_QUEUE');
      }
    },
  },

  getters: {
    /**
     * 检查指定设备是否正在报警
     */
    isDeviceAlarming: (state) => (deviceId) => {
      // 使用严格比较，避免设备ID为0时被错误判断为falsy
      if (!state.alarmStatus || deviceId === null || deviceId === undefined) {
        return false;
      }
      const status = state.alarmStatus[String(deviceId)];
      return status ? status.alarm_active : false;
    },

    /**
     * 获取当前队列中的第一条消息
     */
    currentMessage: (state) => {
      return state.messageQueue.length > 0 ? state.messageQueue[0] : null;
    },

    /**
     * 检查是否有待处理的消息
     */
    hasMessages: (state) => {
      return state.messageQueue.length > 0;
    },

    /**
     * 获取报警列表长度
     */
    alarmCount: (state) => {
      return state.alarmList.length;
    },

    /**
     * 获取正在报警的设备ID列表
     */
    alarmingDevices: (state) => {
      const devices = [];
      for (const deviceId in state.alarmStatus) {
        if (state.alarmStatus[deviceId]?.alarm_active) {
          devices.push(deviceId);
        }
      }
      return devices;
    },
  },
};
