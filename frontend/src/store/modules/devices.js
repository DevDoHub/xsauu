/**
 * 设备状态管理模块
 * 管理设备列表、视频源URL和设备IP信息
 */
import { deviceApi, personApi } from '@/services/api';

export default {
  namespaced: true,

  state: () => ({
    // 按人员分组的设备列表
    areaDevices: {},
    // 所有人员列表
    persons: [],
    // 在线设备列表（动态数组，按连接顺序）
    // 格式: [{ deviceId: 1, url: '...', deviceInfo: {...} }, ...]
    onlineDevices: [],
    // 视频源URL数组（动态长度 = 在线设备数）
    images: [],
    // 显示位置到设备ID的映射（关键！用于点击时获取真实设备ID）
    // 格式: { 0: 100, 1: 5, 2: 23, ... } 表示第0格显示设备100，第1格显示设备5...
    displayIndexToDeviceId: {},
    // 主服务器IP地址
    deviceIp: '',
    // 加载状态
    loading: false,
    // 错误信息
    error: null,
  }),

  mutations: {
    /**
     * 设置按区域负责人分组的设备数据
     */
    SET_AREA_DEVICES(state, data) {
      state.areaDevices = data;
    },

    /**
     * 设置在线设备列表，同时更新images数组和映射表
     */
    SET_ONLINE_DEVICES(state, devices) {
      state.onlineDevices = devices;

      const newMapping = {};
      const newImages = [];

      // 在线设备按 cam_id 字典序排列（稳定排序，避免页面跳位）
      const sorted = [...devices].sort((a, b) =>
        String(a.deviceId).localeCompare(String(b.deviceId))
      );

      // 建立旧的 deviceId → index 反查表，用于保留已有帧
      const oldDeviceIndex = {};
      for (const [idx, id] of Object.entries(state.displayIndexToDeviceId)) {
        oldDeviceIndex[String(id)] = Number(idx);
      }

      sorted.forEach((device, index) => {
        newMapping[index] = device.deviceId;
        // 如果该设备在旧 images 中已有帧数据，保留它
        const oldIdx = oldDeviceIndex[String(device.deviceId)];
        const existingFrame = (oldIdx !== undefined) ? state.images[oldIdx] : null;
        newImages.push(existingFrame || device.url);
      });

      state.displayIndexToDeviceId = newMapping;

      // 仅在内容实际变化时触发响应式更新
      const same = newImages.length === state.images.length &&
        newImages.every((url, i) => url === state.images[i]);
      if (!same) {
        state.images = newImages;
      }
    },

    /**
     * 更新指定设备的视频帧（由 Socket.IO video_frame 事件触发）
     */
    UPDATE_DEVICE_FRAME(state, { camId, dataUrl }) {
        for (const [index, id] of Object.entries(state.displayIndexToDeviceId)) {
            if (String(id) === String(camId)) {
                const old = state.images[Number(index)];
                if (old && old.startsWith('blob:')) {
                    URL.revokeObjectURL(old);
                }
                state.images.splice(Number(index), 1, dataUrl);
                break;
            }
        }
    },

    /**
     * 增量更新设备状态/元信息（SSE 推送）
     *
     * 支持任意字段 merge——后端 `register_device` 兼容层会把边缘端
     * "信息编辑"上报的 workshop / work_type / confined_space / 等字段
     * 一并广播过来，前端无需刷新即可看到变化。
     *
     * 注意：顶层分组键是"设备负责人"(responsible_person)。设备负责人
     * 改名时不会自动重排分组，需要刷新页面或下次 fetchDevices 才生效。
     *
     * @param {Object} patch - { device_id: { ...任意 device 字段 } }
     */
    PATCH_DEVICE_STATUS(state, patch) {
      // 不参与字段 merge 的元字段（避免污染 device 对象）
      const META_KEYS = new Set(['type', 'device_id', 'timestamp']);
      let dirty = false;
      // areaDevices 结构: { 设备负责人: { 设备名: 设备对象 } }
      for (const areaName in state.areaDevices) {
        const devicesMap = state.areaDevices[areaName] || {};
        for (const deviceName in devicesMap) {
          const device = devicesMap[deviceName];
          const camId = String(device.device_id ?? '');
          const update = patch[camId];
          if (!update) continue;

          // 收集真正发生变化的字段
          const merged = { ...device };
          let changedHere = false;
          for (const key in update) {
            if (META_KEYS.has(key)) continue;
            if (update[key] === undefined) continue;
            if (merged[key] !== update[key]) {
              merged[key] = update[key];
              changedHere = true;
            }
          }
          if (changedHere) {
            // 整体替换 device 引用，确保 Vue 2 响应式触发
            // （device 上原本不存在的字段直接赋值不会响应）
            devicesMap[deviceName] = merged;
            dirty = true;
          }
        }
      }
      // 整体替换 areaDevices 引用，触发依赖它的 computed 重算
      if (dirty) {
        state.areaDevices = { ...state.areaDevices };
      }
    },

    /**
     * 设置人员列表
     */
    SET_PERSONS(state, persons) {
      state.persons = persons;
    },

    /**
     * 设置设备IP
     */
    SET_DEVICE_IP(state, ip) {
      state.deviceIp = ip;
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
     * 获取所有设备（按设备负责人分组）
     * 同时更新在线设备列表（动态顺序显示）
     */
    async fetchDevices({ commit }) {
      commit('SET_LOADING', true);
      commit('SET_ERROR', null);

      // 调用按设备负责人分组 API
      const result = await deviceApi.searchDevicesByArea();

      if (result.error) {
        commit('SET_ERROR', result.message);
        commit('SET_LOADING', false);
        return result;
      }

      commit('SET_AREA_DEVICES', result.data);

      // 构建在线设备列表（按遍历顺序，谁在线谁显示）
      // 数据结构: { 区域负责人: { 设备名: 设备对象 } }
      const onlineList = [];

      for (const area in result.data) {
        const devicesMap = result.data[area] || {};
        for (const deviceName in devicesMap) {
          const device = devicesMap[deviceName];
          if (device && device.is_online) {
            onlineList.push({
              deviceId: device.device_id,
              url: null,
              deviceInfo: {
                ...device,
                areaManager: area,
              }
            });
          }
        }
      }

      commit('SET_ONLINE_DEVICES', onlineList);
      commit('SET_LOADING', false);
      return result;
    },

    /**
     * 获取所有人员列表
     */
    async fetchPersons({ commit }) {
      const result = await personApi.getAll();

      if (!result.error) {
        commit('SET_PERSONS', result.data);
      }

      return result;
    },

    /**
     * 获取设备IP映射
     */
    async fetchDeviceIp({ commit }) {
      const result = await deviceApi.getDeviceIp();

      if (!result.error && result.data) {
        // 后端返回 DeviceIpMapRespVO: { devices: { device_id: {ip, name} } }
        // 保留完整映射供组件使用，同时兼容旧代码取 ip_address 的场景
        commit('SET_DEVICE_IP', result.data);
      }

      return result;
    },

    /**
     * 应用推送的设备状态增量更新
     */
    applyPushUpdate({ commit }, payload) {
      // payload 格式: { [device_id]: { is_online, online_since, last_heartbeat } }
      if (!payload || typeof payload !== 'object') return;
      commit('PATCH_DEVICE_STATUS', payload);
    },

    /**
     * 断开设备连接（触发重新获取设备列表）
     */
    async disconnectDevice({ dispatch }) {
      await dispatch('fetchDevices');
    },

    /**
     * 重连设备（触发重新获取设备列表）
     */
    async reconnectDevice({ dispatch }) {
      await dispatch('fetchDevices');
    },
  },

  getters: {
    /**
     * 获取设备负责人列表
     */
    deviceManagerList: (state) => Object.keys(state.areaDevices),

    /**
     * 获取指定设备负责人下的设备信息
     */
    getDevicesByPerson: (state) => (personName) => {
      return state.areaDevices[personName] || {};
    },

    /**
     * 获取在线设备列表
     */
    onlineDeviceList: (state) => state.onlineDevices,

    /**
     * 根据显示索引获取真实设备ID（关键getter！）
     * @param {number} displayIndex - 在视频网格中的显示位置（0开始）
     * @returns {number|null} 真实的设备ID，如果该位置没有设备则返回null
     */
    getDeviceIdByDisplayIndex: (state) => (displayIndex) => {
      const deviceId = state.displayIndexToDeviceId[displayIndex];
      // 使用严格比较，避免设备ID为0时被错误判断为falsy
      return deviceId !== undefined && deviceId !== null ? deviceId : null;
    },

    /**
     * 根据设备ID获取显示索引
     * @param {number} deviceId - 设备ID
     * @returns {number} 显示位置，-1表示不在线
     */
    getDisplayIndexByDeviceId: (state) => (deviceId) => {
      for (const [index, id] of Object.entries(state.displayIndexToDeviceId)) {
        if (id === deviceId) {
          return parseInt(index);
        }
      }
      return -1;
    },

    /**
     * 获取所有已连接的设备
     */
    connectedDevices: (state) => {
      return state.onlineDevices.map(d => d.deviceInfo);
    },

    /**
     * 获取所有设备（扁平化列表）
     */
    allDevices: (state) => {
      const devices = [];
      for (const personName in state.areaDevices) {
        for (const deviceName in state.areaDevices[personName]) {
          const device = state.areaDevices[personName][deviceName];
          devices.push({ ...device, responsiblePerson: personName, deviceName });
        }
      }
      return devices;
    },

    /**
     * 根据设备编号查找设备
     */
    getDeviceById: (state) => (deviceNumber) => {
      for (const personName in state.areaDevices) {
        for (const deviceName in state.areaDevices[personName]) {
          const device = state.areaDevices[personName][deviceName];
          if (device.deviceNumber === deviceNumber) {
            return { ...device, responsiblePerson: personName, deviceName };
          }
        }
      }
      return null;
    },

    /**
     * 获取人员列表（设备负责人列表）
     */
    personList: (state) => {
      return Object.keys(state.areaDevices);
    },
  },
};
