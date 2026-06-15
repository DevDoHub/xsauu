/**
 * Vuex Store 主入口
 * 集中管理应用状态
 * Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8
 */
import { createStore } from 'vuex';
import devices from './modules/devices';
import alarms from './modules/alarms';
import detection from './modules/detection';

export default createStore({
  modules: {
    devices,
    alarms,
    detection,
  },
});
