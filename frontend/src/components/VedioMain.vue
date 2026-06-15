<template>
  <div class="vedio-main" ref="vedioMainRoot" :style="scaleStyle">
    <ConfigAdjustModal
      :visible="showConfigAdjustModal"
      :deviceId="configAdjustDeviceId"
      :configData="configAdjustData"
      :loading="configAdjustLoading"
      :saving="configAdjustSaving"
      :errorMessage="configAdjustError"
      @close="handleCloseConfigAdjust"
      @save="handleSaveConfigAdjust"
    />

    <div class="dashboard-header">
      <div class="header-logo"></div>
      <div class="header-title-wrap">
        <div class="header-line"></div>
        <h1>核电建造安全智能监控系统</h1>
      </div>
      <div class="header-status">
        <div class="status-chip server-chip">
          <span>主服务器</span>
          <strong>{{ formattedData }}</strong>
        </div>
      </div>
    </div>

    <div class="dashboard-shell" :class="{ 'focus-mode': activeView !== 'monitor' }">
      <aside class="dashboard-panel dashboard-left">
        <div class="nav-stack">
          <button class="nav-btn" :class="{ active: selectedNav === 'cockpit' }" @click="switchView('cockpit')">安全驾驶舱</button>
          <button class="nav-btn" :class="{ active: selectedNav === 'monitor' }" @click="switchView('monitor')">监控画面</button>
          <button class="nav-btn" :class="{ active: selectedNav === 'alarm-mgmt' }" @click="switchView('alarm-mgmt')">
            报警管理
            <span v-if="pendingAlarmCount > 0" class="alarm-badge">{{ pendingAlarmCount > 99 ? '99+' : pendingAlarmCount }}</span>
          </button>
          <button class="nav-btn" :class="{ active: selectedNav === 'gas-monitor' }" @click="switchView('gas-monitor')">气体监控</button>
          <button class="nav-btn" :class="{ active: selectedNav === 'history' }" @click="switchView('history')">历史查询</button>
          <button class="nav-btn" :class="{ active: selectedNav === 'statistics' }" @click="switchView('statistics')">数据报表</button>
          <button class="nav-btn" :class="{ active: selectedNav === 'project' }" @click="switchView('project')">项目管理</button>
          <button class="nav-btn" :class="{ active: selectedNav === 'personnel' }" @click="switchView('personnel')">人员管理</button>
          <button class="nav-btn" :class="{ active: selectedNav === 'features' }" @click="switchView('features')">功能板块</button>
          <button class="nav-btn" :class="{ active: selectedNav === 'settings' }" @click="switchView('settings')">系统配置</button>
        </div>

      </aside>

      <main class="dashboard-center" v-if="activeView === 'monitor'">
        <div class="center-card video-card">
          <div class="video-container">
            <!-- WebRTC 视频网格 -->
            <WebRTCVideoGrid
              :alarmStatus="alarmStatus"
              :gasData="normalizedRealtimeGasMap"
              :deviceRotationMap="deviceRotationMap"
              @select="handleWebRTCSelect"
            />
          </div>

          <div class="center-footer">
            <div class="action-card footer-half">

              <div class="footer-btn-row">
                <button class="footer-btn" @click="handleStartDetection">▶ 开始检测</button>
                <button class="footer-btn" @click="handleStopDetection">■ 停止检测</button>
              </div>
            </div>
            <button class="action-card footer-half" @click="openFaceRecSystem">
              <span>人脸识别系统</span>
              <strong>进入</strong>
            </button>
          </div>

        </div>
      </main>

      <aside class="dashboard-panel dashboard-right" v-if="activeView === 'monitor'">
        <div class="right-tab-header">
          <button class="right-tab-btn" :class="{ active: rightTab === 'alarm' }" @click="rightTab = 'alarm'">报警列表</button>
          <button class="right-tab-btn" :class="{ active: rightTab === 'person' }" @click="rightTab = 'person'">设备列表</button>
        </div>

        <div class="alarm-panel-wrapper" v-if="rightTab === 'alarm'">
          <div class="panel-title alarm-title alarm-title-flex">
            <span>最新报警事件</span>
            <div class="alarm-actions">
              <span class="action-link" @click="handleResetAlarms">清空</span>
            </div>
          </div>
          <AlarmPanel
            :alarmList="alarmList"
          />
        </div>

        <div class="right-tab-person" v-if="rightTab === 'person'">
          <DeviceSidebar
            :areaDevices="areaDevices"
            :gasData="normalizedRealtimeGasMap"
            :gasThreshold="normalizedGasThresholdMap"
            :isOpen="true"
            :showTime="false"
            :deviceDetectionStatus="deviceDetectionStatus"
            @batch-control="handleBatchControl"
            @device-control="handleDeviceControl"
            @open-config-adjust="handleOpenConfigAdjust"
            @start-all="handleStartAllDetection"
            @stop-all="handleStopAllDetection"
            @person-control="handlePersonDetectionControl"
          />
        </div>
      </aside>

      <main class="dashboard-center history-center" v-else-if="activeView === 'history'">
        <HistorySearchPage :persons="persons" @alarm-deleted="fetchPendingAlarmCount" />
      </main>

      <main v-else-if="activeView === 'features'" class="dashboard-center history-center">
        <FeatureModulePage />
      </main>

      <main v-else-if="activeView === 'alarm-mgmt'" class="dashboard-center history-center">
        <AlarmReviewPage :refreshKey="alarmReviewRefreshKey" @alarm-reviewed="fetchPendingAlarmCount" />
      </main>

      <main v-else-if="activeView === 'gas-monitor'" class="dashboard-center history-center">
        <GasMonitorPage />
      </main>

      <main v-else-if="activeView === 'settings'" class="dashboard-center history-center">
        <SystemSettingsPage />
      </main>

      <main class="dashboard-center history-center" v-else>
        <CockpitOverviewPage
          :trendSamples="trendSamples"
          :totalDeviceCount="totalDeviceCount"
          :onlineDeviceCount="onlineDeviceCount"
          :activeAlarmCount="activeAlarmCount"
          :gasAlertCount="gasAlertCount"
          :areaDevices="areaDevices"
          :alarmList="alarmList"
          :alarmStatus="alarmStatus"
          :realtimeGasData="realtimeGasData"
          :gasThreshold="gasThreshold"
          :gasRegistry="gasRegistry"
          :deviceStatusChartOption="deviceStatusChartOption"
          :alarmTypeChartOption="alarmTypeChartOption"
          :gasChartOption="gasChartOption"
          :alarmTrendChartOption="alarmTrendChartOption"
          @locate-device="handleLocateDeviceFromCockpit"
          @open-alarm-modal="handleOpenAlarmModalFromCockpit"
        />
      </main>
    </div>

    <AlarmControlModal
      :visible="selectedDeviceId !== null"
      :selectedImage="selectedImage"
      :selectedPath="selectedPath"
      :selectedDeviceId="selectedDeviceId"
      :alarmStatus="alarmStatus"
      :gasData="normalizedRealtimeGasMap"
      :areaDevices="areaDevices"
      :deviceRotationMap="deviceRotationMap"
      @close="closeModal"
      @clear-alarm="handleClearAlarm"
      @trigger-alarm="handleTriggerAlarm"
      @trigger-alarm-with-violation="handleTriggerAlarmWithViolation"
    />
  </div>
</template>

<script>
/**
 * VedioMain.vue - 视频监控系统主容器组件
 * 
 * 功能说明：
 * 1. 作为主容器组件，负责组合和协调所有子组件
 * 2. 管理全局状态（通过 Vuex Store）
 * 3. 处理子组件之间的通信和事件
 * 4. 管理定时轮询任务（设备状态、报警状态、气体数据等）
 * 
 * 子组件说明：
 * - VideoGrid: 视频网格显示组件（单画面/四宫格/九宫格）
 * - DeviceSidebar: 设备侧边栏组件（人员管理、设备控制）
 * - AlarmPanel: 报警面板组件（报警列表、历史记录）
 * - ControlPanel: 控制面板组件（开始/停止检测）
 * - AlarmControlModal: 报警控制弹窗
 * - HistorySearchPage: 历史记录全屏页
 */

// ==================== 导入依赖 ====================
import { mapState, mapGetters, mapActions } from 'vuex';

// 子组件导入
import VideoGrid from './VideoGrid.vue';           // 视频网格组件（传统图片流）
import WebRTCVideoGrid from './WebRTCVideoGrid.vue'; // WebRTC 视频网格组件
import DeviceSidebar from './DeviceSidebar.vue';   // 设备侧边栏组件
import AlarmPanel from './AlarmPanel.vue';         // 报警面板组件
import AlarmControlModal from './AlarmControlModal.vue'; // 报警控制弹窗
import ConfigAdjustModal from './ConfigAdjustModal.vue'; // 参数调整弹窗
import HistorySearchPage from './HistorySearchPage.vue'; // 历史记录全屏页
import CockpitOverviewPage from './CockpitOverviewPage.vue';
import FeatureModulePage from './FeatureModulePage.vue';
import AlarmReviewPage from './AlarmReviewPage.vue';
import GasMonitorPage from './GasMonitorPage.vue';
import SystemSettingsPage from './SystemSettingsPage.vue';

// API 服务层导入
import { cameraApi, configApi, deviceApi, alarmReviewApi } from '@/services/api';

// 常量导入
import { 
  DISPLAY_MODES,      // 显示模式枚举
  DISPLAY_MODE_CELLS, // 显示模式对应的单元格数量
} from '@/utils/constants';

// SSE 订阅 composable（实时推送主通道）
import { useDeviceStatusSSE, useGasDataSSE, useAlarmSSE } from '@/composables/useSSE';

export default {
  name: 'VedioMain',
  
  // ==================== 组件注册 ====================
  components: {
    VideoGrid,          // 视频网格（传统图片流）
    WebRTCVideoGrid,    // WebRTC 视频网格
    DeviceSidebar,      // 设备侧边栏
    AlarmPanel,         // 报警面板
    AlarmControlModal,  // 报警控制弹窗
    ConfigAdjustModal,  // 参数调整弹窗
    HistorySearchPage,   // 历史记录全屏页
    CockpitOverviewPage,
    FeatureModulePage,
    AlarmReviewPage,
    GasMonitorPage,
    SystemSettingsPage
  },

  // ==================== 组件数据 ====================
  data() {
    return {
      // ---------- 缩放相关 ----------
      scaleRatio: { x: 1, y: 1 },
      // ---------- 显示模式相关 ----------
      displayMode: DISPLAY_MODES.NINE,  // 当前显示模式，默认九宫格
      currentSingleIndex: 0,            // 单画面模式当前索引
      currentFourIndex: 0,              // 四宫格模式当前起始索引
      currentNineIndex: 0,              // 九宫格模式当前起始索引
      currentSixteenIndex: 0,           // 16宫格模式当前起始索引
      

      
      // ---------- 选中状态相关 ----------
      selectedDeviceId: null,           // 当前选中的设备ID
      selectedPath: null,               // 当前选中的 WebRTC 路径（用于弹窗视频流）
      
      // ---------- 侧边栏状态 ----------
      sidebarOpen: true,                // 侧边栏是否展开
      
      // ---------- 对话框状态 ----------
      activeView: 'monitor',            // 当前主视图: monitor | history | cockpit
      selectedNav: 'monitor',             // 当前高亮的导航按钮
      showConfigAdjustModal: false,     // 是否显示参数调整弹窗
      configAdjustDeviceId: '',         // 当前参数调整设备SN
      configAdjustData: null,           // 当前设备完整配置
      configAdjustLoading: false,       // 参数配置加载状态
      configAdjustSaving: false,        // 参数配置保存状态
      configAdjustError: '',            // 参数配置错误信息
      // ---------- 服务器信息 ----------
      formattedData: '',                // 格式化后的服务器IP显示
      
      // ---------- 定时器引用（仅保留超低频兜底轮询） ----------
      fallbackPollTimer: null,          // 5分钟兜底轮询定时器
      deviceIpTimer: null,              // 设备IP轮询定时器（极少变化）
      alarmStatusTimer: null,           // 报警状态轮询定时器
      gasThresholdTimer: null,          // 气体阈值轮询定时器
      streamPollingTimer: null,         // 报警流轮询定时器

      // ---------- 右侧面板宽度 ----------
      rightTab: 'alarm',                   // 右侧面板当前tab: 'alarm' | 'person'
      rightPanelWidth: 300,              // 右侧面板宽度（像素）
      isResizing: false,                 // 是否正在拖拽调整

      // 当前连接状态
      deviceCount: 0,
      gasRegistry: [],

      // ---------- 报警管理待处理数量 ----------
      pendingAlarmCount: 0,
      alarmReviewRefreshKey: 0,  // 递增 key 触发 AlarmReviewPage 刷新

      // ---------- 趋势采样（持久化，不随页面切换丢失） ----------
      trendSamples: [],
      trendTimer: null,

      // ---------- SSE 订阅（实时推送通道） ----------
      deviceStatusSSE: null,    // 设备状态 SSE 订阅
      gasDataSSE: null,         // 气体数据 SSE 订阅
      alarmSSE: null,           // 告警数据 SSE 订阅

      // ---------- 气体数据批量缓冲 ----------
      _gasBuffer: {},           // 临时缓冲：{ device_id: latestData }
      _gasFlushTimer: null,     // 定时 flush
    };
  },

  // ==================== 计算属性 ====================
  computed: {
    scaleStyle() {
      return {
        transform: `scale(${this.scaleRatio.x}, ${this.scaleRatio.y})`,
        transformOrigin: 'left top',
        width: '1920px',
        height: '1080px'
      };
    },

    // 从 Vuex devices 模块映射状态
    ...mapState('devices', [
      'areaDevices',            // 按设备负责人分组的设备数据
      'persons',                // 人员列表
      'images',                 // 视频源URL数组
      'displayIndexToDeviceId'  // 显示位置到设备ID的映射
    ]),
    
    // 从 Vuex alarms 模块映射状态
    ...mapState('alarms', [
      'alarmStatus',     // 所有设备的报警状态
      'alarmList'        // 报警事件列表
    ]),
    
    // 从 Vuex detection 模块映射状态
    ...mapState('detection', [
      'isDetecting',       // 检测运行状态
      'deviceDetectionStatus', // 单设备检测状态
      'realtimeGasData',   // 实时气体数据
      'gasThreshold'       // 气体报警阈值
    ]),
    
    // 从 Vuex devices 模块映射 getters
    ...mapGetters('devices', ['personList']),
    
    allDevices() {
      const devices = [];
      // areaDevices 结构: { 区域负责人: { 设备名: 设备对象 } }
      Object.keys(this.areaDevices || {}).forEach((area) => {
        const devicesMap = this.areaDevices[area] || {};
        Object.keys(devicesMap).forEach((deviceName) => {
          const device = devicesMap[deviceName];
          devices.push({ ...device, areaManager: area });
        });
      });
      return devices;
    },

    /**
     * 设备旋转角度映射 { device_id: rotation, mediamtx_path: rotation }
     * 用于传递给 WebRTCVideoGrid，控制每个摄像头的视频方向
     * 同时用 device_id 和 mediamtx_path 做 key，避免因路径名不同而查不到
     */
    deviceRotationMap() {
      const map = {};
      this.allDevices.forEach((device) => {
        const rotation = device.camera_rotation ?? 0;
        if (rotation) {
          map[device.device_id] = rotation;
          // mediamtx_path 可能与 device_id 不同，也建立映射
          const mtxPath = device.mediamtx_path || device.device_id;
          map[mtxPath] = rotation;
        }
      });
      return map;
    },

    totalDeviceCount() {
      return this.allDevices.length;
    },

    onlineDeviceCount() {
      // 始终从响应式 allDevices 计算，SSE 推送更新 areaDevices 后立即反映
      return this.allDevices.filter(device => device.is_online).length;
    },

    offlineDeviceCount() {
      return Math.max(this.totalDeviceCount - this.onlineDeviceCount, 0);
    },

    activeAlarmCount() {
      return Object.values(this.alarmStatus || {}).filter(status => status && status.alarm_active).length;
    },

    gasAlertCount() {
      let count = 0;
      const gasData = this.normalizedRealtimeGasMap;
      const threshold = this.normalizedGasThresholdMap;
      const gasKeys = this.gasChartKeys;

      Object.keys(gasData).forEach((deviceId) => {
        const data = gasData[deviceId] || {};
        const limit = threshold[deviceId] || threshold[String(deviceId)] || {};
        gasKeys.forEach((key) => {
          const value = parseFloat(data[key]);
          if (Number.isNaN(value)) return;
          // O2 使用 O2_max 和 O2_min 判断
          if (key === 'O2') {
            const o2Max = parseFloat(limit['O2_max']);
            const o2Min = parseFloat(limit['O2_min']);
            if (!Number.isNaN(o2Max) && value > o2Max) count += 1;
            if (!Number.isNaN(o2Min) && value < o2Min) count += 1;
          } else {
            const target = parseFloat(limit[key]);
            if (Number.isNaN(target)) return;
            if (value > target) count += 1;
          }
        });
      });

      return count;
    },

    normalizedRealtimeGasMap() {
      const raw = this.realtimeGasData || {};
      if (raw && typeof raw === 'object' && raw.data && typeof raw.data === 'object' && !Array.isArray(raw.data)) {
        return raw.data;
      }
      return raw && typeof raw === 'object' ? raw : {};
    },

    normalizedGasThresholdMap() {
      const raw = this.gasThreshold || {};
      if (raw && typeof raw === 'object' && raw.data && typeof raw.data === 'object' && !Array.isArray(raw.data)) {
        return raw.data;
      }
      return raw && typeof raw === 'object' ? raw : {};
    },

    displayModeText() {
      const textMap = {
        [DISPLAY_MODES.ONE]: '单画面',
        [DISPLAY_MODES.FOUR]: '四宫格',
        [DISPLAY_MODES.NINE]: '九宫格',
        [DISPLAY_MODES.SIXTEEN]: '16宫格'
      };
      return textMap[this.displayMode] || '九宫格';
    },

    gasChartKeys() {
      const keys = (this.gasRegistry || []).map(gas => gas.key).filter(Boolean);
      return keys.length ? keys : ['C3H8', 'C2H2', 'CO2', 'HCN', 'O2', 'AR', 'H2S'];
    },

    deviceStatusChartOption() {
      return {
        color: ['#4bb8ff', '#ffb84d'],
        tooltip: { trigger: 'item' },
        legend: {
          bottom: 0,
          itemGap: 16,
          itemWidth: 14,
          itemHeight: 10,
          textStyle: { color: '#b8d8e8', fontSize: 11 }
        },
        series: [{
          type: 'pie',
          radius: ['52%', '72%'],
          center: ['50%', '42%'],
          label: { show: false },
          data: [
            { name: '在线', value: this.onlineDeviceCount },
            { name: '离线', value: this.offlineDeviceCount }
          ]
        }]
      };
    },

    alarmTypeChartOption() {
      const counter = {};
      (this.alarmList || []).forEach((alarm) => {
        const key = alarm.type2 || alarm.type || '未知';
        counter[key] = (counter[key] || 0) + 1;
      });
      const names = Object.keys(counter).slice(0, 6);
      const values = names.map(name => counter[name]);

      return {
        color: ['#ffb84d'],
        tooltip: { trigger: 'axis' },
        grid: { left: 36, right: 12, top: 22, bottom: 32 },
        xAxis: {
          type: 'category',
          data: names.length ? names : ['暂无'],
          axisLabel: { color: '#b8d8e8', fontSize: 10, interval: 0 },
          axisLine: { lineStyle: { color: 'rgba(, , , 0.35)' } }
        },
        yAxis: {
          type: 'value',
          minInterval: 1,
          axisLabel: { color: '#b8d8e8' },
          splitLine: { lineStyle: { color: 'rgba(, , , 0.35)' } }
        },
        series: [{
          type: 'bar',
          barWidth: 14,
          data: values.length ? values : [0],
          itemStyle: { borderRadius: [8, 8, 0, 0] }
        }]
      };
    },

    gasChartOption() {
      const gasKeys = this.gasChartKeys;
      const valuesByKey = {};
      const maxValues = {};
      const p95Values = {};
      const medianValues = {};
      const thresholds = this.normalizedGasThresholdMap;
      const rows = Object.values(this.normalizedRealtimeGasMap || {});

      gasKeys.forEach((key) => {
        valuesByKey[key] = [];
      });

      rows.forEach((row) => {
        gasKeys.forEach((key) => {
          const value = parseFloat(row && row[key]);
          if (!Number.isNaN(value)) valuesByKey[key].push(value);
        });
      });

      gasKeys.forEach((key) => {
        const sortedValues = valuesByKey[key].slice().sort((a, b) => a - b);
        const count = sortedValues.length;
        const maxValue = count ? sortedValues[count - 1] : 0;
        const p95Index = count ? Math.floor((count - 1) * 0.95) : 0;
        const medianIndex = count ? Math.floor((count - 1) * 0.5) : 0;

        maxValues[key] = maxValue;
        p95Values[key] = count ? sortedValues[p95Index] : 0;
        medianValues[key] = count ? sortedValues[medianIndex] : 0;
      });

      const thresholdRows = Object.values(thresholds);
      const indicatorMaxes = gasKeys.reduce((acc, key) => {
        let thresholdMax = 0;
        thresholdRows.forEach((row) => {
          const value = parseFloat(row && row[key]);
          if (!Number.isNaN(value)) thresholdMax = Math.max(thresholdMax, value);
        });
        const baseMax = Math.max(thresholdMax, maxValues[key]);
        acc[key] = Math.max(baseMax * 1.2, 10);
        return acc;
      }, {});

      return {
        color: ['#ff6b6b', '#ffd166', '#4bb8ff'],
        tooltip: {},
        legend: {
          bottom: 0,
          itemWidth: 12,
          itemHeight: 6,
          textStyle: { color: '#b8d8e8', fontSize: 9 }
        },
        radar: {
          radius: '62%',
          indicator: gasKeys.map(key => ({ name: key, max: indicatorMaxes[key] })),
          axisName: { color: '#d9fbff' },
          splitLine: { lineStyle: { color: 'rgba(, , , 0.35)' } },
          splitArea: { areaStyle: { color: ['rgba(, , , 0.35)', 'rgba(, , , 0.35)'] } },
          axisLine: { lineStyle: { color: 'rgba(, , , 0.35)' } }
        },
        series: [{
          type: 'radar',
          data: [
            {
              value: gasKeys.map(key => maxValues[key]),
              name: '最大值',
              lineStyle: { color: '#ff6b6b', width: 2 },
              itemStyle: { color: '#ff6b6b' },
              areaStyle: { color: 'rgba(255, 107, 107, 0.14)' }
            },
            {
              value: gasKeys.map(key => p95Values[key]),
              name: 'P95',
              lineStyle: { color: '#ffd166', width: 2 },
              itemStyle: { color: '#ffd166' },
              areaStyle: { color: 'rgba(255, 209, 102, 0.12)' }
            },
            {
              value: gasKeys.map(key => medianValues[key]),
              name: '中位数',
              lineStyle: { color: '#4bb8ff', width: 2 },
              itemStyle: { color: '#4bb8ff' },
              areaStyle: { color: 'rgba(, , , 0.35)' }
            }
          ]
        }]
      };
    },

    alarmTrendChartOption() {
      const counter = {};
      (this.alarmList || []).forEach((alarm) => {
        const label = String(alarm.time || '').slice(5, 16) || '未知';
        counter[label] = (counter[label] || 0) + 1;
      });
      const labels = Object.keys(counter).slice(0, 8).reverse();
      const values = labels.map(label => counter[label]);

      return {
        color: ['#4bb8ff'],
        tooltip: { trigger: 'axis' },
        grid: { left: 34, right: 12, top: 24, bottom: 28 },
        xAxis: {
          type: 'category',
          data: labels.length ? labels : ['暂无'],
          axisLabel: { color: '#b8d8e8', fontSize: 10 },
          axisLine: { lineStyle: { color: 'rgba(, , , 0.35)' } }
        },
        yAxis: {
          type: 'value',
          minInterval: 1,
          axisLabel: { color: '#b8d8e8' },
          splitLine: { lineStyle: { color: 'rgba(, , , 0.35)' } }
        },
        series: [{
          type: 'line',
          smooth: true,
          symbolSize: 6,
          areaStyle: { color: 'rgba(, , , 0.35)' },
          data: values.length ? values : [0]
        }]
      };
    },

    currentIndex() {
      switch (this.displayMode) {
        case DISPLAY_MODES.ONE: 
          return this.currentSingleIndex;
        case DISPLAY_MODES.FOUR: 
          return this.currentFourIndex;
        case DISPLAY_MODES.SIXTEEN:
          return this.currentSixteenIndex;
        default: 
          return this.currentNineIndex;
      }
    },

    deviceIdToWorkshop() {
      const map = {};
      const areaDevices = this.areaDevices || {};
      // areaDevices 结构: { "区域负责人": { "设备名": DeviceRespVO } }
      Object.values(areaDevices).forEach((devicesMap) => {
        Object.values(devicesMap || {}).forEach((device) => {
          if (device && typeof device === 'object' && device.deviceNumber !== undefined && device.workshop) {
            map[String(device.deviceNumber)] = device.workshop;
          }
        });
      });
      return map;
    },

    videoOverlayMap() {
      const result = {};
      const gasMap = this.normalizedRealtimeGasMap || {};
      const mapping = this.displayIndexToDeviceId || {};
      Object.entries(mapping).forEach(([index, deviceId]) => {
        const data = gasMap[String(deviceId)] || gasMap[deviceId] || {};
        result[index] = {
          deviceId: String(deviceId),
          temp: this.formatGasDisplayValue(data.TEMP),
          rh: this.formatGasDisplayValue(data.RH),
          o2: this.formatGasDisplayValue(data.O2),
          workshop: this.deviceIdToWorkshop[String(deviceId)] || '-'
        };
      });
      return result;
    },

    selectedImage() {
      if (this.selectedDeviceId === null) return null;
      // 在 displayIndexToDeviceId 中找到该设备对应的 displayIndex
      for (const [index, id] of Object.entries(this.displayIndexToDeviceId)) {
        if (String(id) === String(this.selectedDeviceId)) {
          return this.images[Number(index)] || null;
        }
      }
      return null;
    }
  },

  // ==================== 生命周期钩子 ====================
  
  created() {
  },
  
  /**
   * 组件挂载后：初始化数据并启动各种轮询
   */
  mounted() {
    // 初始化缩放
    this.updateScale();
    window.addEventListener('resize', this.updateScale);

    // 初始化 SSE 订阅（实时推送通道）
    this._initSSESubscriptions();

    // 初始数据加载 + 超低频兜底轮询
    this.initializeData();

    // 启动趋势采样（本地计算，不发网络请求）
    this.pushTrendSample();
    this.trendTimer = setInterval(this.pushTrendSample, 10000);

    // 获取待处理报警计数（初始加载，后续通过SSE实时更新）
    this.fetchPendingAlarmCount();
    // 定时刷新角标（兜底，防止删除/审核后不同步）
    this.pendingCountTimer = setInterval(() => this.fetchPendingAlarmCount(), 15000);
  },
  
  /**
   * 组件销毁前：清除所有定时器，防止内存泄漏
   */
  beforeUnmount() {
    window.removeEventListener('resize', this.updateScale);
    this.clearAllTimers();
    if (this.trendTimer) clearInterval(this.trendTimer);
    if (this.pendingCountTimer) clearInterval(this.pendingCountTimer);
    if (this._gasFlushTimer) { clearTimeout(this._gasFlushTimer); this._gasFlushTimer = null; }
    // 断开所有 SSE 连接
    [this.deviceStatusSSE, this.gasDataSSE, this.alarmSSE].forEach(sse => {
      if (sse) sse.disconnect();
    });
  },

  // ==================== 方法定义 ====================
  methods: {
    /**
     * 根据窗口尺寸计算缩放比例（设计稿基准 1920×1080）
     */
    updateScale() {
      const designW = 1920;
      const designH = 1080;
      const scaleX = window.innerWidth / designW;
      const scaleY = window.innerHeight / designH;
      this.scaleRatio = { x: scaleX, y: scaleY };
    },

    formatGasDisplayValue(value) {
      if (value === null || value === undefined || value === '' || value === '-1') {
        return '-';
      }

      const num = parseFloat(value);
      if (Number.isNaN(num)) return '-';

      return String(Math.trunc(num));
    },

    // ---------- Vuex Actions 映射 ----------
    ...mapActions('devices', [
      'fetchDevices',      // 获取设备列表
      'fetchPersons',      // 获取人员列表
      'fetchDeviceIp',     // 获取设备IP
      'disconnectDevice',  // 断开设备连接
      'reconnectDevice'    // 重连设备
    ]),
    ...mapActions('alarms', [
      'fetchAlarmStatus',  // 获取报警状态
      'fetchStream',       // 获取报警流数据
      'clearAlarm',        // 清除报警
      'triggerAlarm',      // 触发报警
      'triggerAlarmWithViolation', // 带违规信息的报警触发
      'resetAbnormal'      // 重置异常计数
    ]),
    ...mapActions('detection', [
      'startDetection',    // 开始检测
      'stopDetection',     // 停止检测
      'fetchRealtimeGas',  // 获取实时气体数据
      'fetchGasThreshold'  // 获取气体阈值
    ]),

    switchView(view) {
      this.selectedNav = view;
      const implemented = ['monitor', 'history', 'cockpit', 'features', 'alarm-mgmt','gas-monitor','settings'];
      if (implemented.includes(view)) {
        this.activeView = view;
      }
    },



    /**
     * 初始化 SSE 订阅
     */
    _initSSESubscriptions() {
      // 设备状态 SSE 订阅
      this.deviceStatusSSE = useDeviceStatusSSE({
        onMessage: (data) => {
          console.log('设备状态更新:', data);
          // 更新 Vuex 中的设备状态
          if (data.device_id) {
            // 把 SSE 推过来的所有元字段（除 type / device_id / timestamp 外）
            // 全部透传给 store，由 PATCH_DEVICE_STATUS 做字段级 merge。
            // 这样后端兼容层广播的 workshop / work_type / confined_space /
            // work_start_time / responsible_person 等"信息编辑"字段都能实时刷新。
            const { type, device_id, timestamp, ...rest } = data;
            this.$store.dispatch('devices/applyPushUpdate', {
              [device_id]: rest,
            });
            // 设备上下线时立即刷新趋势图（无需等待 10 秒定时器）
            this.$nextTick(() => this.pushTrendSample());
          }
        },
        onError: (error) => {
          console.error('设备状态 SSE 错误:', error);
        },
      });
      this.deviceStatusSSE.connect();

      // 气体数据 SSE 订阅（批量缓冲，每秒 flush 一次避免阻塞 UI）
      this.gasDataSSE = useGasDataSSE({
        onMessage: (data) => {
          if (data.device_id) {
            // 只缓冲，不立即提交
            this._gasBuffer[data.device_id] = data;
            if (!this._gasFlushTimer) {
              this._gasFlushTimer = setTimeout(() => {
                this._gasFlushTimer = null;
                const batch = this._gasBuffer;
                this._gasBuffer = {};
                this.$store.dispatch('detection/applyGasPush', {
                  schema_version: 1,
                  data: batch,
                });
              }, 1000);
            }
          }
        },
        onError: (error) => {
          console.error('气体数据 SSE 错误:', error);
        },
      });
      this.gasDataSSE.connect();

      // 告警数据 SSE 订阅
      this.alarmSSE = useAlarmSSE({
        onMessage: (data) => {
          console.log('收到告警:', data);
          // 更新 Vuex 中的告警数据
          this.$store.dispatch('alarms/applyAlarmStreamPush', {
            schema_version: 1,
            data: data,
          });
          // 重新从后端拉取未处理数量（不盲目 +1）
          this.fetchPendingAlarmCount();
          // 通知子组件（AlarmReviewPage）刷新告警审核列表
          this.alarmReviewRefreshKey++;
        },
        onError: (error) => {
          console.error('告警 SSE 错误:', error);
        },
      });
      this.alarmSSE.connect();
    },

    handleLocateDeviceFromCockpit(deviceId) {
      const normalizedId = String(deviceId ?? '').trim();
      if (!normalizedId) return;

      this.switchView('monitor');

      const entries = Object.entries(this.displayIndexToDeviceId || {});
      const targetEntry = entries.find(([, mappedId]) => String(mappedId) === normalizedId);
      if (!targetEntry) {
        alert(`设备 ${normalizedId} 当前不在线或不在监控画面中`);
        return;
      }

      const displayIndex = Number(targetEntry[0]);
      if (!Number.isFinite(displayIndex)) return;

      if (this.displayMode === DISPLAY_MODES.ONE) {
        this.currentSingleIndex = displayIndex;
      } else if (this.displayMode === DISPLAY_MODES.FOUR) {
        this.currentFourIndex = Math.floor(displayIndex / 4) * 4;
      } else if (this.displayMode === DISPLAY_MODES.SIXTEEN) {
        this.currentSixteenIndex = Math.floor(displayIndex / 16) * 16;
      } else {
        this.currentNineIndex = Math.floor(displayIndex / 9) * 9;
      }

      this.selectedDeviceId = targetEntry[1];
      this.selectedPath = String(targetEntry[1]);
    },

    handleOpenAlarmModalFromCockpit(payload) {
      const normalizedId = String(payload?.deviceId ?? '').trim();
      if (!normalizedId) return;

      const entries = Object.entries(this.displayIndexToDeviceId || {});
      const targetEntry = entries.find(([, mappedId]) => String(mappedId) === normalizedId);
      const displayIndex = targetEntry ? Number(targetEntry[0]) : -1;

      let image = '';
      if (Number.isFinite(displayIndex) && displayIndex >= 0) {
        image = this.images[displayIndex] || '';
      } else {
        const baseUrl = `${window.location.protocol}//${window.location.hostname}:5020`;
        image = `${baseUrl}/video_feed/${encodeURIComponent(normalizedId)}`;
      }

      // Alarm records keep a still evidence image; the control modal should prefer live video.
      if (!image && payload?.alarm?.image) {
        image = String(payload.alarm.image);
      }

      this.selectedDeviceId = normalizedId;
      this.selectedPath = normalizedId;
    },

    // ==================== 初始化方法 ====================
    /**
     * 获取当天未处理报警数量（review_status === 0）
     * 初始加载一次，后续通过 SSE 实时更新
     */
    async fetchPendingAlarmCount() {
      try {
        const result = await alarmReviewApi.getToday();
        if (!result.error && result.data && result.data.data) {
          this.pendingAlarmCount = result.data.data.filter(r => r.review_status === 0).length;
        }
      } catch (e) {
        // 静默失败，不影响主流程
      }
    },
    
    /**
     * 初始化数据获取
     * 初始加载全量快照，后续由 SSE 推送驱动更新
     * 仅保留 5 分钟超低频兜底轮询作为断线保护
     */
    async initializeData() {
      this.startStreamPolling();         // 报警流兜底轮询
      await this.fetchDeviceIpData();   // 获取服务器IP（启动时拉一次）
      await this.fetchDevices();        // 获取设备列表（启动时拉一次）
      await this.fetchPersons();        // 获取人员列表（启动时拉一次）
      await this.fetchAlarmStatus();    // 获取报警状态快照（后续 SSE 推送）
      await this.fetchRealtimeGas();    // 获取气体数据快照（后续 SSE 推送）
      await this.fetchGasThreshold();   // 获取气体阈值配置（静态配置，变化极少）
      await this.fetchDeviceCount();    // 获取设备数量
      await this.fetchGasRegistry();    // 获取气体注册表
      this.startPolling();              // 启动低频兜底轮询
    },

    /**
     * 获取服务器IP并更新显示
     */
    async fetchDeviceIpData() {
      // 直接使用当前访问的 hostname，与旧系统 /get_device_ip 语义一致
      this.formattedData = window.location.hostname || '未知';
    },

    async fetchGasRegistry() {
      try {
        const { gasApi } = await import('@/services/api');
        const result = await gasApi.getMonitorData();
        if (!result.error && result.data) {
          if (result.data.registry && result.data.registry.length) {
            this.gasRegistry = result.data.registry;
          }
          if (result.data.threshold) {
            this.$store.commit('detection/SET_GAS_THRESHOLD', result.data.threshold);
          }
          if (result.data.realtime) {
            this.$store.commit('detection/SET_GAS_DATA', result.data.realtime);
          }
        }
      } catch (e) {
        console.error('Failed to fetch gas registry:', e);
      }
    },

    pushTrendSample() {
      const now = new Date();
      const label = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
      this.trendSamples.push({
        time: label,
        online: this.onlineDeviceCount,
        total: this.totalDeviceCount
      });
      if (this.trendSamples.length > 12) {
        this.trendSamples.shift();
      }
    },

    // ==================== 轮询管理方法 ====================
    
    /**
     * 启动报警流轮询
     * 使用递归 setTimeout 实现，避免请求堆积
     */
    startStreamPolling() {
      const pollStream = async () => {
        try {
          await this.fetchStream();
        } catch (e) {
          console.error('获取报警流失败:', e);
        }
        this.streamPollingTimer = setTimeout(pollStream, 30000);
      };
      pollStream();
    },

    /**
     * 启动所有定时轮询任务
     */
    startPolling() {
      this.gasThresholdTimer = setInterval(
        () => this.fetchGasThreshold(),
        30000
      );

      this.deviceIpTimer = setInterval(
        () => this.fetchDeviceIpData(),
        30000
      );

      this.alarmStatusTimer = setInterval(
        () => this.fetchAlarmStatus(),
        30000
      );
    },

    /**
     * 获取在线设备数量
     */
    async fetchDeviceCount() {
      const result = await deviceApi.getDeviceCount();
      if (!result.error&& result.data){
        this.deviceCount = result.data.online || 0;
      }
    },

    /**
     * 清除所有定时器
     * 在组件销毁前调用，防止内存泄漏
     */
    clearAllTimers() {
      const intervalTimers = [
        this.alarmStatusTimer,
        this.gasThresholdTimer,
        this.deviceIpTimer,
      ];
      intervalTimers.forEach(timer => timer && clearInterval(timer));

      if (this.streamPollingTimer) {
        clearTimeout(this.streamPollingTimer);
      }
    },

    // ==================== 视频网格事件处理 ====================
    
    /**
     * 处理视频单元格选择事件
     * @param {string} deviceId - 设备ID
     * @param {string} image - 图片URL
     */
    handleVideoSelect(deviceId) {
      if (this.selectedDeviceId != null) {
        // 点击已选中的图片，取消选择
        // this.selectedImage = null;
        this.selectedDeviceId = null;
      } else {
        // 选择新的图片
        // this.selectedImage = image;
        this.selectedDeviceId = deviceId;
      }
    },

    /**
     * 处理 WebRTC 视频单元格选择事件
     * @param {Object} payload - { path: mediamtx路径, deviceId: 设备ID }
     */
    handleWebRTCSelect({ path, deviceId }) {
      console.log('WebRTC 视频选中:', path, '设备ID:', deviceId);
      if (this.selectedDeviceId != null && String(this.selectedDeviceId) === String(deviceId)) {
        // 点击已选中的，取消选择
        this.selectedDeviceId = null;
        this.selectedPath = null;
      } else {
        this.selectedDeviceId = deviceId;
        this.selectedPath = path;
      }
    },

    /**
     * 处理显示模式切换事件
     * @param {string} mode - 新的显示模式 ('one'/'four'/'nine')
     */
    handleModeChange(mode) {
      this.displayMode = mode;
      // 切换模式时重置对应的索引
      if (mode === DISPLAY_MODES.ONE) {
        this.currentSingleIndex = 0;
      } else if (mode === DISPLAY_MODES.FOUR) {
        this.currentFourIndex = 0;
      } else if (mode === DISPLAY_MODES.SIXTEEN) {
        this.currentSixteenIndex = 0;
      } else {
        this.currentNineIndex = 0;
      }
    },

    /**
     * 处理导航事件（上一张/组、下一张/组）
     * @param {string} direction - 导航方向 ('prev'/'next')
     */
    handleNavigate(direction) {
      const cellCount = DISPLAY_MODE_CELLS[this.displayMode] || 9;
      const maxIndex = this.images.length;
      
      if (this.displayMode === DISPLAY_MODES.ONE) {
        // 单画面模式：逐张切换
        if (direction === 'prev' && this.currentSingleIndex > 0) {
          this.currentSingleIndex -= 1;
        } else if (direction === 'next' && this.currentSingleIndex < maxIndex - 1) {
          this.currentSingleIndex += 1;
        }
      } else if (this.displayMode === DISPLAY_MODES.FOUR) {
        // 四宫格模式：每次切换4张
        if (direction === 'prev' && this.currentFourIndex >= cellCount) {
          this.currentFourIndex -= cellCount;
        } else if (direction === 'next' && this.currentFourIndex + cellCount < maxIndex) {
          this.currentFourIndex += cellCount;
        }
      } else if (this.displayMode === DISPLAY_MODES.SIXTEEN) {
        // 16宫格模式：每次切换16张
        if (direction === 'prev' && this.currentSixteenIndex >= cellCount) {
          this.currentSixteenIndex -= cellCount;
        } else if (direction === 'next' && this.currentSixteenIndex + cellCount < maxIndex) {
          this.currentSixteenIndex += cellCount;
        }
      } else {
        // 九宫格模式：每次切换9张
        if (direction === 'prev' && this.currentNineIndex >= cellCount) {
          this.currentNineIndex -= cellCount;
        } else if (direction === 'next' && this.currentNineIndex + cellCount < maxIndex) {
          this.currentNineIndex += cellCount;
        }
      }
    },

    /**
     * 关闭视频弹窗
     */
    closeModal() {
      this.selectedDeviceId = null;
      this.selectedPath = null;
    },

    // ==================== 设备侧边栏事件处理 ====================
    
    /**
     * 切换侧边栏展开/折叠状态
     */
    toggleSidebar() {
      this.sidebarOpen = !this.sidebarOpen;
    },

    async handleOpenConfigAdjust(deviceId) {
      this.configAdjustDeviceId = String(deviceId || '');
      this.showConfigAdjustModal = true;
      this.configAdjustLoading = true;
      this.configAdjustSaving = false;
      this.configAdjustError = '';
      this.configAdjustData = null;

      try {
        const result = await configApi.getConfig(this.configAdjustDeviceId);
        if (result.error || !result.data || !result.data.config) {
          this.configAdjustError = result.message || '获取参数配置失败';
          return;
        }
        this.configAdjustData = result.data.config;
      } catch (e) {
        this.configAdjustError = '获取参数配置失败';
      } finally {
        this.configAdjustLoading = false;
      }
    },

    handleCloseConfigAdjust() {
      if (this.configAdjustSaving) return;
      this.showConfigAdjustModal = false;
      this.configAdjustLoading = false;
      this.configAdjustError = '';
    },

    hasPayloadChanges(payload) {
      return payload && typeof payload === 'object' && Object.keys(payload).length > 0;
    },

    async handleSaveConfigAdjust(payload) {
      if (!this.hasPayloadChanges(payload)) {
        alert('无参数改动，无需保存');
        this.handleCloseConfigAdjust();
        return;
      }

      this.configAdjustSaving = true;
      this.configAdjustError = '';

      try {
        const result = await configApi.updateConfig(this.configAdjustDeviceId, payload);
        if (result.error) {
          this.configAdjustError = result.message || '保存参数失败，请重试';
          alert(this.configAdjustError);
          return;
        }
        this.showConfigAdjustModal = false;
      } catch (e) {
        this.configAdjustError = '保存参数失败，请重试';
        alert(this.configAdjustError);
      } finally {
        this.configAdjustSaving = false;
      }
    },

    /**
     * 处理批量控制事件
     * 子组件按"场地（workshop）"分组后，直接把该场地下所有 device_id 传上来。
     * @param {Object} payload - { workshop: 场地名, deviceIds: 设备号数组, action: 操作 }
     */
    handleBatchControl(payload, legacyAction) {
      // 兼容旧调用：handleBatchControl(person, action)
      let deviceIds = [];
      let action = '';
      if (payload && typeof payload === 'object' && Array.isArray(payload.deviceIds)) {
        deviceIds = payload.deviceIds;
        action = payload.action;
      } else if (typeof payload === 'string') {
        // 旧签名兜底（按区域负责人查 areaDevices）
        action = legacyAction;
        const devicesMap = this.areaDevices[payload] || {};
        deviceIds = Object.values(devicesMap)
          .map(d => d && d.device_id)
          .filter(Boolean);
      }
      deviceIds.forEach(id => this.handleDeviceControl(id, action));
    },

    /**
     * 处理设备控制命令
     * 包括 PTZ 方向控制、启动/断开连接等
     * @param {number} deviceId - 设备ID
     * @param {string} action - 控制动作 (up/down/left/right/zoom_in/zoom_out/stop/auto/reconnect/disconnect)
     */
    async handleDeviceControl(deviceId, action) {
      console.log('VedioMain handleDeviceControl:', deviceId, action);
      
      // 对于 PTZ 控制命令，直接发送 API 请求
      if (['up', 'down', 'left', 'right', 'zoom_in', 'zoom_out', 'stop', 'auto'].includes(action)) {
        console.log('发送PTZ控制命令:', action, deviceId);
        try {
          const result = await cameraApi.control(action, deviceId);
          if (result.error) {
            console.error('PTZ控制失败:', result.message);
          }
        } catch (e) {
          console.error('PTZ控制异常:', e);
        }
        return;
      }
      
      // 对于连接控制命令，需要查找设备并更新状态
      const device = this.findDeviceById(deviceId);
      if (!device) {
        console.error(`设备 ${deviceId} 未找到`);
        return;
      }
      
      if (action === 'disconnect') {
        // 断开连接：更新本地视频源为默认图片
        this.disconnectDevice(deviceId);
        await cameraApi.control('disconnect', deviceId);
      } else if (action === 'reconnect') {
        // 重新连接：更新视频源URL
        this.reconnectDevice(deviceId);
        await cameraApi.control('reconnect', deviceId);
      }
    },

    /**
     * 根据设备ID查找设备信息
     * @param {string} deviceId - 设备ID (device_id)
     * @returns {Object|null} 设备对象或null
     */
    findDeviceById(deviceId) {
      // areaDevices 结构: { "区域负责人": { "设备名": DeviceRespVO } }
      for (const area in this.areaDevices) {
        const devicesMap = this.areaDevices[area] || {};
        for (const deviceName in devicesMap) {
          const device = devicesMap[deviceName];
          if (device && typeof device === 'object' && device.device_id === deviceId) {
            return { ...device, areaManager: area };
          }
        }
      }
      return null;
    },

    // ==================== 检测控制事件处理 ====================

    /**
     * 处理单设备检测控制
     * @param {string} deviceId - 设备ID
     * @param {string} action - 控制动作 (start/stop)
     */
    async handleDeviceDetectionControl(deviceId, action) {
      console.log('设备检测控制:', deviceId, action);
      try {
        await this.$store.dispatch('detection/controlDeviceDetection', {
          deviceId,
          action,
        });
        console.log(`设备 ${deviceId} 检测${action === 'start' ? '启动' : '停止'}成功`);
      } catch (e) {
        console.error('设备检测控制失败:', e);
        alert(`设备检测控制失败: ${e.message || '请重试'}`);
      }
    },

    /**
     * 处理全部开始检测
     */
    async handleStartAllDetection() {
      console.log('全部开始检测');
      try {
        await this.startDetection();
        console.log('全部检测已启动');
      } catch (e) {
        console.error('启动全部检测失败:', e);
        alert('启动全部检测失败，请重试');
      }
    },

    /**
     * 处理全部停止检测
     */
    async handleStopAllDetection() {
      console.log('全部停止检测');
      try {
        await this.stopDetection();
        console.log('全部检测已停止');
      } catch (e) {
        console.error('停止全部检测失败:', e);
        alert('停止全部检测失败，请重试');
      }
    },

    /**
     * 处理按负责人控制检测
     * @param {string} personName - 负责人名称
     * @param {string} action - 控制动作 (start/stop)
     */
    async handlePersonDetectionControl(personName, action) {
      console.log('按负责人控制检测:', personName, action);
      
      // 遍历所有区域找到该负责人的设备
      const deviceIds = [];
      // areaDevices 结构: { "区域负责人": { "设备名": DeviceRespVO } }
      // personName 在此结构中是区域负责人 key
      const devicesMap = this.areaDevices[personName] || {};
      Object.values(devicesMap).forEach((device) => {
        if (device && typeof device === 'object' && device.device_id) {
          deviceIds.push(device.device_id);
        }
      });
      
      if (deviceIds.length === 0) {
        alert('该负责人下没有设备');
        return;
      }

      try {
        await this.$store.dispatch('detection/controlBatchDetection', {
          deviceIds,
          action,
        });
        console.log(`${personName} 的设备检测${action === 'start' ? '启动' : '停止'}成功`);
      } catch (e) {
        console.error('批量检测控制失败:', e);
        alert('批量检测控制失败，请重试');
      }
    },

    // ==================== 报警相关事件处理 ====================
    
    /**
     * 处理清除报警事件
     * @param {string|number} deviceId - 设备ID
     */
    async handleClearAlarm(deviceId) {
      try { 
        await this.clearAlarm(deviceId);
        console.log('清除报警成功');
      } catch (e) { 
        console.error('清除报警失败:', e); 
        alert('清除报警失败，请重试'); 
      }
    },

    /**
     * 处理触发报警事件
     * @param {string|number} deviceId - 设备ID
     */
    async handleTriggerAlarm(deviceId) {
      try { 
        await this.triggerAlarm(deviceId);
        console.log('触发报警成功');
      } catch (e) { 
        console.error('触发报警失败:', e); 
        alert('触发报警失败，请重试'); 
      }
    },

    /**
     * 处理带违规信息的报警触发事件
     * @param {Object} payload - 包含 deviceId, violationType, violationDetail
     */
    async handleTriggerAlarmWithViolation({ deviceId, alarmType, alarmTypeLabel, severity, description, image, note, type, type2 }) {
      try {
        await this.triggerAlarmWithViolation({ deviceId, alarmType, alarmTypeLabel, severity, description, image, note, type, type2 });
        console.log('远程报警成功');
      } catch (e) {
        console.error('远程报警失败:', e);
        alert('报警失败，请重试');
      }
    },

    /**
     * 处理重置报警列表事件
     */
    async handleResetAlarms() {
      try { 
        await this.resetAbnormal();
        console.log('报警列表已重置');
      } catch (e) { 
        console.error('重置报警失败:', e); 
      }
    },

    // ==================== 检测控制事件处理 ====================
    
    /**
     * 处理开始检测事件
     */
    async handleStartDetection() {
      try { 
        await this.startDetection();
        console.log('检测已启动');
      } catch (e) { 
        console.error('启动检测失败:', e); 
      }
    },

    /**
     * 处理停止检测事件
     */
    async handleStopDetection() {
      try { 
        await this.stopDetection();
        console.log('检测已停止');
      } catch (e) { 
        console.error('停止检测失败:', e); 
      }
    },


    // ==================== 右侧面板拖拽调整 ====================
    
    /**
     * 开始拖拽调整右侧面板宽度
     */
    startResize() {
      this.isResizing = true;
      document.addEventListener('mousemove', this.doResize);
      document.addEventListener('mouseup', this.stopResize);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    },

    /**
     * 拖拽过程中调整宽度
     * @param {MouseEvent} e - 鼠标事件
     */
    doResize(e) {
      if (!this.isResizing) return;
      const containerRight = document.querySelector('.container').getBoundingClientRect().right;
      const newWidth = containerRight - e.clientX;
      // 限制宽度范围：200px ~ 500px
      if (newWidth >= 200 && newWidth <= 500) {
        this.rightPanelWidth = newWidth;
      }
    },

    /**
     * 停止拖拽
     */
    stopResize() {
      this.isResizing = false;
      document.removeEventListener('mousemove', this.doResize);
      document.removeEventListener('mouseup', this.stopResize);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    },
    /*打开人脸识别系统界面*/
    openFaceRecSystem () {
      const serverHost = window.location.hostname;
      const faceRecUrl = `http://${serverHost}:5000/face_recognition`;
      window.open(faceRecUrl, '_blank');
    }
  }
};
</script>

<style scoped>
/* CSS style additions for drawer and actions */
.alarm-title-flex {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.alarm-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.action-link {
  font-size: 13px;
  color: #93939f; /* Muted slate */
  cursor: pointer;
  transition: color 0.2s ease;
}

.action-link:hover {
  color: #72cfff; /* Focus blue/cyan */
  text-decoration: underline;
}

.action-separator {
  color: #4a4a5a;
  font-size: 12px;
}

/* Inline device sidebar embedded in left panel */
.inline-device-sidebar {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  margin-top: 10px;
}
.inline-device-sidebar :deep(.device-sidebar) {
  width: 100% !important;
  height: 100%;
}
.inline-device-sidebar :deep(.resize-handle) {
  display: none !important;
}

/* Allow chart to fill space */
.flex-grow-chart {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 240px;
}
.flex-grow-chart > div:last-child {
  flex: 1;
}

.vedio-main {
  width: 1920px;
  height: 1080px;
  display: flex;
  flex-direction: column;
  color: #e8fbff;
  background:
    radial-gradient(circle at 50% 0%, rgba(102, 199, 255, 0.20), transparent 38%),
    linear-gradient(135deg, #1a446d 0%, #255784 48%, #1b4b74 100%);
  overflow: hidden;
  will-change: transform;
}

.vedio-main::before {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(186, 230, 253, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(186, 230, 253, 0.08) 1px, transparent 1px);
  background-size: 32px 32px;
  mask-image: linear-gradient(to bottom, rgba(0, 0, 0, 0.9), transparent);
}

.dashboard-header {
  height: 86px;
  display: grid;
  grid-template-columns: 360px 1fr 360px;
  align-items: center;
  padding: 8px 18px 0;
  position: relative;
  flex-shrink: 0;
}

.dashboard-header::after {
  content: '';
  position: absolute;
  left: 280px;
  right: 280px;
  bottom: 2px;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(186, 230, 253, 0.9), transparent);
  box-shadow: 0 0 18px rgba(46, 168, 255, 0.5);
}

.header-logo {
  width: 100%;
  height: 92px;
  max-width: 420px;
  background-image: url('../assets/img/zhonghehuax_modified3_transparent.png');
  background-repeat: no-repeat;
  background-size: auto 100%;
  background-position: left center;
}

.header-title-wrap {
  justify-self: center;
  min-width: 520px;
  padding: 12px 44px;
  text-align: center;
  border: 1px solid rgba(186, 230, 253, 0.45);
  background: linear-gradient(180deg, rgba(22, 66, 104, 0.82), rgba(14, 45, 78, 0.72));
  clip-path: polygon(34px 0, calc(100% - 34px) 0, 100% 50%, calc(100% - 34px) 100%, 34px 100%, 0 50%);
  box-shadow: inset 0 0 22px rgba(186, 230, 253, 0.12), 0 0 20px rgba(46, 168, 255, 0.16);
}

.header-title-wrap h1 {
  margin: 0;
  font-size: 32px;
  letter-spacing: 3px;
  color: #ffffff;
  text-shadow: 0 0 18px rgba(186, 230, 253, 0.65);
}

.header-line {
  width: 78px;
  height: 3px;
  margin: 0 auto 6px;
  background: #2ea8ff;
  box-shadow: 0 0 12px #2ea8ff;
}

.header-status {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.status-chip {
  min-width: 132px;
  height: 58px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 0 12px;
  border: 1px solid rgba(186, 230, 253, 0.32);
  border-radius: 4px;
  background: rgba(24, 64, 104, 0.74);
  box-shadow: inset 0 0 16px rgba(46, 168, 255, 0.08);
}

.status-chip span {
  font-size: 13px;
  line-height: 1.2;
  color: #9fc9ff;
  white-space: nowrap;
}

.status-chip strong {
  font-size: 24px;
  line-height: 1.25;
  color: #ffffff;
}

.status-chip em {
  margin-left: 4px;
  font-size: 13px;
  font-style: normal;
  color: #9fc9ff;
}

.server-chip {
  min-width: 170px;
}

.server-chip strong {
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.dashboard-shell {
  height: calc(1080px - 86px);
  display: grid;
  grid-template-columns: 300px minmax(520px, 1fr) 310px;
  gap: 12px;
  padding: 10px 16px 14px;
  box-sizing: border-box;
  overflow: hidden;
}

.dashboard-shell.focus-mode {
  grid-template-columns: 300px minmax(760px, 1fr);
}

.dashboard-shell.standalone-view {
  grid-template-columns: minmax(760px, 1fr);
}

.dashboard-panel,
.center-card,
.chart-card,
.device-tree-card,
.alarm-panel-wrapper,
.control-card,
.action-card {
  position: relative;
  border: 1px solid rgba(186, 230, 253, 0.38);
  background: linear-gradient(180deg, rgba(34, 88, 136, 0.78), rgba(24, 68, 108, 0.84));
  box-shadow: inset 0 0 24px rgba(46, 168, 255, 0.10), 0 0 16px rgba(0, 0, 0, 0.20);
}

.dashboard-panel::before,
.center-card::before,
.chart-card::before,
.device-tree-card::before,
.alarm-panel-wrapper::before {
  content: '';
  position: absolute;
  inset: 8px;
  border-top: 1px solid rgba(186, 230, 253, 0.24);
  border-bottom: 1px solid rgba(186, 230, 253, 0.14);
  pointer-events: none;
}

.dashboard-left,
.dashboard-right {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  overflow: hidden;
}

.dashboard-center {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.history-center {
  min-height: 0;
}

.section-title,
.panel-title {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  min-height: 26px;
  color: #e6f1ff;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 1px;
}

.section-title::before,
.panel-title::before {
  content: '';
  width: 0;
  height: 0;
  margin-right: 8px;
  border-top: 6px solid transparent;
  border-bottom: 6px solid transparent;
  border-left: 7px solid #2ea8ff;
  filter: drop-shadow(0 0 6px #2ea8ff);
}

.nav-stack {
  display: grid;
  gap: 10px;
}

.nav-btn {
  position: relative;
  height: 45px;
  color: #e6f1ff;
  border: 1px solid rgba(186, 230, 253, 0.44);
  background: linear-gradient(90deg, rgba(46, 168, 255, 0.24), rgba(46, 168, 255, 0.10));
  cursor: pointer;
  letter-spacing: 1px;
  font-size: 18px;
}

.alarm-badge {
  position: absolute;
  top: -7px;
  right: -7px;
  min-width: 18px;
  height: 18px;
  border-radius: 9px;
  background: #ff3b3b;
  color: #fff;
  font-size: 11px;
  font-weight: bold;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 4px;
  line-height: 1;
  pointer-events: none;
}

.nav-btn.active,
.nav-btn:hover {
  color: #ffffff;
  border-color: rgba(46, 168, 255, 0.92);
  box-shadow: inset 0 0 18px rgba(46, 168, 255, 0.28), 0 0 12px rgba(46, 168, 255, 0.22);
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.metric-card {
  min-height: 68px;
  padding: 10px;
  border: 1px solid rgba(186, 230, 253, 0.30);
  background: rgba(255, 255, 255, 0.10);
}

.metric-card span,
.metric-card em {
  display: block;
  color: #c2e4ff;
  font-size: 12px;
  font-style: normal;
}

.metric-card strong {
  margin-right: 4px;
  color: #66c7ff;
  font-size: 30px;
  line-height: 1.15;
}

.metric-card.warning strong {
  color: #ffb84d;
}

.chart-card {
  min-height: 190px;
  padding: 10px;
  box-sizing: border-box;
}

.device-tree-card {
  flex: 1;
  min-height: 0;
  padding: 10px;
  overflow: hidden;
}

.video-card {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 12px;
}

.video-title {
  justify-content: space-between;
  flex-shrink: 0;
}

.mode-text {
  padding: 3px 10px;
  border: 1px solid rgba(255, 184, 77, 0.45);
  color: #ffcf7a;
  font-size: 12px;
  font-weight: 500;
}

/* 视频源模式切换按钮 */
.video-source-switcher {
  display: flex;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(14, 45, 78, 0.6);
  border-bottom: 1px solid rgba(186, 230, 253, 0.15);
  flex-shrink: 0;
}

.source-btn {
  padding: 6px 16px;
  border: 1px solid rgba(186, 230, 253, 0.3);
  border-radius: 4px;
  background: rgba(46, 168, 255, 0.1);
  color: #9fc9ff;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.source-btn:hover {
  background: rgba(46, 168, 255, 0.25);
  border-color: rgba(186, 230, 253, 0.5);
  color: #ffffff;
}

.source-btn.active {
  background: rgba(46, 168, 255, 0.4);
  border-color: #2ea8ff;
  color: #ffffff;
  box-shadow: 0 0 12px rgba(46, 168, 255, 0.3);
}

.video-container {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding-top: 8px;
}

.center-footer {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 10px;
  flex-shrink: 0;
}

.action-card {
  min-height: 68px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: #f2f7ff;
  cursor: pointer;
}

.action-card span {
  display: block;
  color: #c2e4ff;
  font-size: 13px;
}

.action-card strong {
  display: block;
  margin-top: 6px;
  color: #ffcf7a;
  font-size: 22px;
}

.footer-btn-row {
  display: flex;
  gap: 12px;
  margin-top: 6px;
}

.footer-btn {
  padding: 5px 16px;
  border: 1px solid rgba(186, 230, 253, 0.54);
  border-radius: 3px;
  background: rgba(46, 168, 255, 0.22);
  color: #f2f7ff;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
}

.footer-btn:hover {
  background: rgba(46, 168, 255, 0.34);
  border-color: rgba(46, 168, 255, 0.90);
}

.dashboard-right .chart-card {
  min-height: 202px;
}

.right-tab-header {
  display: flex;
  gap: 0;
  flex-shrink: 0;
  border-bottom: 1px solid rgba(186, 230, 253, 0.2);
  margin-bottom: 8px;
}

.right-tab-btn {
  flex: 1;
  padding: 8px 0;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 1px;
  color: #c2e4ff;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: color 0.2s, border-color 0.2s;
}

.right-tab-btn:hover {
  color: #e6f1ff;
}

.right-tab-btn.active {
  color: #66c7ff;
  border-bottom-color: #66c7ff;
  text-shadow: 0 0 8px rgba(102, 199, 255, 0.48);
}

.right-tab-person {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.right-tab-person :deep(.device-sidebar) {
  width: 100% !important;
  height: 100%;
}

.right-tab-person :deep(.resize-handle) {
  display: none !important;
}

.alarm-panel-wrapper {
  flex: 1;
  min-height: 0;
  padding: 10px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.alarm-title {
  flex-shrink: 0;
}

:deep(.video-grid-container) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

:deep(.video-mode-switcher) {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-bottom: 8px !important;
}

:deep(.video-mode-btn),
:deep(.video-page-btn),
:deep(.unique-button),
:deep(.control-btn) {
  color: #e6f1ff;
  border: 1px solid rgba(186, 230, 253, 0.54);
  background: rgba(52, 112, 164, 0.74);
  border-radius: 3px;
}

:deep(.video-mode-btn.is-active),
:deep(.video-mode-btn:hover),
:deep(.video-page-btn:hover),
:deep(.unique-button:hover),
:deep(.control-btn:hover) {
  color: #ffffff;
  border-color: rgba(46, 168, 255, 0.85);
  box-shadow: 0 0 12px rgba(46, 168, 255, 0.32);
}

:deep(.grid) {
  flex: 1;
  min-height: 0;
  gap: 8px;
  overflow: hidden;
}

:deep(.video-pagination-controls) {
  flex-shrink: 0;
  justify-content: flex-end;
  padding-top: 10px;
  min-height: 34px;
  box-sizing: border-box;
}

:deep(.grid > div) {
  border: 1px solid rgba(186, 230, 253, 0.52);
  background: rgba(255, 255, 255, 0.24);
}

:deep(.grid > div img) {
  border-radius: 2px;
  background: rgba(74, 128, 182, 0.42);
}

:deep(.device-label) {
  color: #e6f1ff;
  background: rgba(58, 108, 164, 0.62);
  border: 1px solid rgba(186, 230, 253, 0.62);
}

:deep(.device-sidebar) {
  width: 100% !important;
}

:deep(.time-display-box),
:deep(.area-device-box),
:deep(.control-buttons-box),
:deep(.alarm-list-box) {
  border-color: rgba(146, 196, 255, 0.34);
  background: rgba(36, 80, 128, 0.52);
  box-shadow: none;
}

:deep(.control-buttons-box) {
  height: auto;
  min-height: 54px;
}

:deep(.alarm-panel) {
  min-height: 0;
}

:deep(.alarm-list-box) {
  flex: 1;
  min-height: 0;
}

:deep(.alarm-item) {
  border-color: rgba(146, 196, 255, 0.24);
  background: rgba(255, 255, 255, 0.12);
}

:deep(.alarm-image) {
  max-height: 110px;
}

/* media query 已移除 — 使用 scale 方案后页面始终按 1920×1080 渲染 */
</style>
