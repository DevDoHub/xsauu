/**
 * 检测状态管理模块
 * 管理检测状态、置信度阈值和气体数据
 * Requirements: 8.4, 8.5, 8.6, 8.7, 8.8
 */
import { detectionApi, gasApi } from '@/services/api';
// NOTE: confidence 相关功能已迁移到 /api/config/<device_id> 接口

export default {
  namespaced: true,

  state: () => ({
    // 检测运行状态
    isDetecting: false,
    // 单设备检测状态 { deviceId: boolean }
    deviceDetectionStatus: {},
    // 实时气体数据
    realtimeGasData: {},
    // 气体报警阈值
    gasThreshold: {},
    // 加载状态
    loading: false,
    // 错误信息
    error: null,
  }),

  mutations: {
    /**
     * 设置检测状态
     */
    SET_DETECTING(state, value) {
      state.isDetecting = value;
    },

    /**
     * 设置单设备检测状态
     */
    SET_DEVICE_DETECTING(state, { deviceId, isDetecting }) {
      state.deviceDetectionStatus = {
        ...state.deviceDetectionStatus,
        [deviceId]: isDetecting,
      };
    },

    /**
     * 设置实时气体数据
     */
    SET_GAS_DATA(state, data) {
      state.realtimeGasData = data;
    },

    /**
     * 设置气体报警阈值
     */
    SET_GAS_THRESHOLD(state, threshold) {
      state.gasThreshold = threshold;
    },

    /**
     * 增量更新气体数据（SocketIO 推送）
     * @param {Object} patch - { device_id: { ... gas fields } }
     */
    PATCH_GAS_DATA(state, patch) {
      state.realtimeGasData = { ...state.realtimeGasData, ...patch };
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
     * 开始检测（全局）
     */
    async startDetection({ commit }) {
      commit('SET_LOADING', true);
      commit('SET_ERROR', null);

      const result = await detectionApi.start();

      if (!result.error) {
        commit('SET_DETECTING', true);
      } else {
        commit('SET_ERROR', result.message);
      }

      commit('SET_LOADING', false);
      return result;
    },

    /**
     * 停止检测（全局）
     */
    async stopDetection({ commit }) {
      commit('SET_LOADING', true);
      commit('SET_ERROR', null);

      const result = await detectionApi.stop();

      if (!result.error) {
        commit('SET_DETECTING', false);
      } else {
        commit('SET_ERROR', result.message);
      }

      commit('SET_LOADING', false);
      return result;
    },

    /**
     * 控制单个设备检测
     * @param {string} deviceId - 设备ID
     * @param {string} action - 动作: start/stop
     */
    async controlDeviceDetection({ commit }, { deviceId, action }) {
      commit('SET_LOADING', true);
      commit('SET_ERROR', null);

      const result = await detectionApi.controlDevice(deviceId, action);

      if (!result.error) {
        commit('SET_DEVICE_DETECTING', {
          deviceId,
          isDetecting: action === 'start',
        });
      } else {
        commit('SET_ERROR', result.message);
      }

      commit('SET_LOADING', false);
      return result;
    },

    /**
     * 批量控制设备检测
     * @param {string[]} deviceIds - 设备ID列表
     * @param {string} action - 动作: start/stop
     */
    async controlBatchDetection({ commit }, { deviceIds, action }) {
      commit('SET_LOADING', true);
      commit('SET_ERROR', null);

      const result = await detectionApi.controlBatch(deviceIds, action);

      if (!result.error) {
        // 更新所有设备的检测状态
        deviceIds.forEach((deviceId) => {
          commit('SET_DEVICE_DETECTING', {
            deviceId,
            isDetecting: action === 'start',
          });
        });
      } else {
        commit('SET_ERROR', result.message);
      }

      commit('SET_LOADING', false);
      return result;
    },

    /**
     * 获取实时气体数据
     */
    async fetchRealtimeGas({ commit }) {
      const result = await gasApi.getRealtime();

      if (!result.error && result.data) {
        commit('SET_GAS_DATA', result.data);
      }

      return result;
    },

    /**
     * 应用推送的气体数据增量更新
     */
    applyGasPush({ commit }, payload) {
      if (!payload || payload.schema_version !== 1) {
        console.warn('[detection] unknown schema_version, ignoring push', payload);
        return;
      }
      commit('PATCH_GAS_DATA', payload.data);
    },

    /**
     * 获取气体报警阈值
     */
    async fetchGasThreshold({ commit }) {
      const result = await gasApi.getThreshold();

      if (!result.error && result.data) {
        // gas/threshold 返回 { data: { deviceId: {...} } }，需要提取内层
        const threshold = result.data.data || result.data;
        commit('SET_GAS_THRESHOLD', threshold);
      }

      return result;
    },
  },

  getters: {
    /**
     * 检查是否正在检测
     */
    isRunning: (state) => state.isDetecting,

    /**
     * 获取气体数据摘要
     */
    gasSummary: (state) => {
      const data = state.realtimeGasData;
      if (!data || !data.data) return null;

      return {
        ip: data.IP,
        CH4: data.data.CH4,
        CO: data.data.CO,
        H2S: data.data.H2S,
        O2: data.data.O2,
        temperature: `${data.data.temp_int}.${data.data.temp_dec}`,
        humidity: `${data.data.humi_int}.${data.data.humi_dec}`,
      };
    },

    /**
     * 检查气体是否超过阈值
     */
    gasAlerts: (state) => {
      const alerts = [];
      const data = state.realtimeGasData?.data;
      const threshold = state.gasThreshold;

      if (!data || !threshold) return alerts;

      const gasTypes = ['CH4', 'CO', 'H2S', 'O2'];
      gasTypes.forEach((gas) => {
        if (data[gas] !== undefined && threshold[gas] !== undefined) {
          if (gas === 'O2') {
            // 氧气低于阈值报警
            if (data[gas] < threshold[gas]) {
              alerts.push({ type: gas, value: data[gas], threshold: threshold[gas], status: 'low' });
            }
          } else {
            // 其他气体高于阈值报警
            if (data[gas] > threshold[gas]) {
              alerts.push({ type: gas, value: data[gas], threshold: threshold[gas], status: 'high' });
            }
          }
        }
      });

      return alerts;
    },
  },
};
