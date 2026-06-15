<template>
  <div 
    class="device-sidebar" 
    :class="{ 'collapsed': !isOpen }"
    :style="{ width: isOpen ? sidebarWidth + 'px' : '0' }"
  >
    <!-- 侧边栏内容 -->
    <div class="sidebar-content" v-show="isOpen">
      <!-- 时间显示区域 -->
      <div class="time-display-box" v-if="showTime">
        <div class="time-content" v-if="currentTime">
          {{ currentDate }} {{ currentTime }}
        </div>
        <div class="time-loading" v-else>加载中...</div>
      </div>

      <!-- 区域设备列表 - 三级层次结构 -->
      <div class="area-device-box">
        <ul class="area-list">
          <!-- 第一层：设备负责人 -->
          <li v-for="personName in deviceManagerList" :key="personName" class="area-item">
            <div class="area-header" @click="toggleArea(personName)">
              <span class="expand-icon">{{ expandedAreas[personName] ? '▼' : '►' }}</span>
              <span class="area-name">{{ personName }}</span>
            </div>

            <!-- 第二层：设备列表 -->
            <ul class="person-list" v-if="expandedAreas[personName]">
              <li 
                v-for="(deviceInfo, deviceName) in getDevicesByPerson(personName)" 
                :key="deviceName"
                class="person-item"
              >
                <div class="person-header" @click="togglePerson(personName, deviceName)">
                  <span class="expand-icon">{{ expandedPersons[`${personName}_${deviceName}`] ? '▼' : '►' }}</span>
                  <span class="person-name-badge" :title="deviceName">{{ deviceName }}</span>
                  <span :class="['status-badge', deviceInfo.is_online ? 'online' : 'offline']">
                    {{ deviceInfo.is_online ? '在线' : '离线' }}
                  </span>
                  <span class="live-view-btn" @click.stop="openLiveModal(deviceInfo)">实时画面</span>
                </div>

                <!-- 第三层：作业信息详情 - 每个字段单独一个框 -->
                <div class="work-info-panel" v-if="expandedPersons[`${personName}_${deviceName}`]">
                  <!-- 工作详情信息折叠分组 -->
                  <div class="collapsible-group">
                    <div 
                      class="group-header" 
                      @click.stop="toggleWorkDetail(personName, deviceName)"
                    >
                      <span class="expand-icon">{{ expandedWorkDetail[`${personName}_${deviceName}_workDetail`] ? '▼' : '►' }}</span>
                      <span class="group-title">工作详情信息</span>
                    </div>
                    <div class="group-content" v-if="expandedWorkDetail[`${personName}_${deviceName}_workDetail`]">
                      <div class="info-card">
                        <span class="info-label">作业区域负责人</span>
                        <span class="info-value">{{ deviceInfo.area_manager || '--' }}</span>
                      </div>
                      <div class="info-card">
                        <span class="info-label">作业区域负责人电话</span>
                        <span class="info-value">{{ deviceInfo.area_manager_phone || '--' }}</span>
                      </div>
                      <div class="info-card">
                        <span class="info-label">安全许可证号</span>
                        <span class="info-value">{{ deviceInfo.safety_permit_no || '--' }}</span>
                      </div>
                      <div class="info-card">
                        <span class="info-label">作业内容</span>
                        <span class="info-value">{{ deviceInfo.work_content || '--' }}</span>
                      </div>
                      <div class="info-card">
                        <span class="info-label">作业地点</span>
                        <span class="info-value">{{ deviceInfo.workshop || '--' }}</span>
                      </div>
                      <div class="info-card">
                        <span class="info-label">作业级别</span>
                        <span class="info-value">{{ deviceInfo.work_level || '--' }}</span>
                      </div>
                      <div class="info-card">
                        <span class="info-label">作业类型</span>
                        <span class="info-value">{{ deviceInfo.work_type || '--' }}</span>
                      </div>
                      <div class="info-card">
                        <span class="info-label">是否受限空间</span>
                        <span class="info-value">{{ deviceInfo.confined_space || '--' }}</span>
                      </div>
                      <!-- 作业起止时间 - 强制换行 -->
                      <div class="info-card time-card">
                        <span class="info-label">作业起止时间</span>
                        <div class="time-value">
                          <div class="time-row">开始: {{ formatTime(deviceInfo.work_start_time) || '--' }}</div>
                          <div class="time-row">结束: {{ getEndTimeDisplay(deviceInfo) }}</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- 工作环境数据信息折叠分组（原设备状态） -->
                  <div class="collapsible-group">
                    <div 
                      class="group-header" 
                      @click.stop="toggleEnvData(personName, deviceName)"
                    >
                      <span class="expand-icon">{{ expandedEnvData[`${personName}_${deviceName}_envData`] ? '▼' : '►' }}</span>
                      <span class="group-title">气体数据信息</span>
                    </div>
                    <div class="group-content" v-if="expandedEnvData[`${personName}_${deviceName}_envData`]">
                      <!-- 气体数据面板（由注册表驱动） -->
                      <div
                        v-for="gas in gasRegistry"
                        :key="gas.key"
                        :class="['gas-card', gas.has_threshold && isGasOverThreshold(deviceInfo.deviceNumber, gas.key) ? 'alarm' : 'normal']"
                      >
                        <span class="gas-label">{{ gas.category === 'gas' ? gas.key + ' ' + gas.display : gas.display }}</span>
                        <span class="gas-value">{{ getGasValue(deviceInfo.deviceNumber, gas.key) }}</span>
                        <span class="gas-unit">{{ gas.unit }}</span>
                      </div>
                    </div>
                  </div>

                  <!-- 远程设备控制折叠分组 -->
                  <div class="collapsible-group">
                    <div 
                      class="group-header" 
                      @click.stop="toggleRemoteControl(personName, deviceName)"
                    >
                      <span class="expand-icon">{{ expandedRemoteControl[`${personName}_${deviceName}_remoteControl`] ? '▼' : '►' }}</span>
                      <span class="group-title">远程设备控制</span>
                    </div>
                    <div class="group-content" v-if="expandedRemoteControl[`${personName}_${deviceName}_remoteControl`]">
                      <!-- 摄像头控制组件 - 居中 -->
                      <div class="camera-control-wrapper">
                        <CameraControl 
                          :device="deviceInfo"
                          @ptz-start="handlePtzStart"
                          @ptz-stop="handlePtzStop"
                          @control="handleDeviceControl"
                        />
                      </div>
                    </div>
                  </div>

                  <!-- 参数调整（与远程设备控制同级） -->
                  <div class="collapsible-group config-adjust-group">
                    <button
                      class="group-header config-adjust-header"
                      @click.stop="handleOpenConfigAdjust(deviceInfo.deviceNumber)"
                    >
                      <span class="group-title">功能控制</span>
                    </button>
                  </div>
                </div>
              </li>
            </ul>
          </li>
        </ul>
      </div>
    </div>

    <!-- 拖拽调整宽度的手柄 -->
    <div 
      class="resize-handle" 
      v-show="isOpen"
      @mousedown="startResize"
    ></div>

    <!-- 摄像头实时画面弹窗 -->
    <CameraLiveModal
      :visible="showLiveModal"
      :deviceId="liveModalDeviceId"
      :deviceInfo="liveModalDeviceInfo"
      @close="closeLiveModal"
    />
  </div>
</template>

<script>
/**
 * DeviceSidebar 组件
 * 负责设备列表展示、人员管理和设备控制
 * 实现三级层次结构：设备负责人 → 设备 → 作业信息（含作业区域负责人）
 */
import CameraControl from './CameraControl.vue';
import CameraLiveModal from './CameraLiveModal.vue';

export default {
  name: 'DeviceSidebar',

  components: {
    CameraControl,
    CameraLiveModal
  },

  props: {
    areaDevices: {
      type: Object,
      required: true,
      default: () => ({})
    },
    gasData: {
      type: Object,
      default: () => ({})
    },
    gasThreshold: {
      type: Object,
      default: () => ({})
    },
    isOpen: {
      type: Boolean,
      default: true
    },
    showTime: {
      type: Boolean,
      default: true
    }
  },

  emits: [
    'batch-control',
    'device-control',
    'open-config-adjust',
    'update-note'
  ],

  data() {
    return {
      expandedAreas: {},
      expandedPersons: {},
      expandedGasData: {},
      // 新增：工作详情信息展开状态
      // key: `${areaManager}_${personName}_workDetail`
      expandedWorkDetail: {},
      // 新增：工作环境数据信息展开状态（替代原 expandedGasData 的功能）
      // key: `${areaManager}_${personName}_envData`
      expandedEnvData: {},
      // 新增：远程设备控制展开状态
      // key: `${areaManager}_${personName}_remoteControl`
      expandedRemoteControl: {},
      // 新增：摄像头实时画面弹窗状态
      showLiveModal: false,
      liveModalDeviceId: null,
      liveModalDeviceInfo: null,
      currentDate: '',
      currentTime: '',
      timeTimer: null,
      // 气体注册表（从后端动态获取，驱动卡片渲染）
      gasRegistry: [],
      // 侧边栏宽度（可拖拽调整）
      sidebarWidth: 360,
      isResizing: false,
      minWidth: 300,
      maxWidth: 600
    };
  },

  computed: {
    /**
     * 按"场地（workshop）"重新分组的设备结构。
     * 返回 { workshop: { deviceName: deviceInfo } }，
     * 没填 workshop 的设备聚到 "未指定场地"。
     *
     * 这样侧边栏第一层就显示场地名，而不是区域负责人名。
     */
    devicesByWorkshop() {
      const grouped = {};
      Object.values(this.areaDevices || {}).forEach(devicesMap => {
        Object.entries(devicesMap || {}).forEach(([deviceName, deviceInfo]) => {
          if (!deviceInfo || typeof deviceInfo !== 'object') return;
          const workshop = (deviceInfo.workshop && String(deviceInfo.workshop).trim()) || '未指定场地';
          if (!grouped[workshop]) grouped[workshop] = {};
          grouped[workshop][deviceName] = deviceInfo;
        });
      });
      return grouped;
    },

    deviceManagerList() {
      // 第一层从"区域负责人"切换为"场地"
      return Object.keys(this.devicesByWorkshop);
    }
  },

  mounted() {
    this.startTimeUpdate();
    this.fetchGasRegistry();
    // 添加全局鼠标事件监听
    document.addEventListener('mousemove', this.onResize);
    document.addEventListener('mouseup', this.stopResize);
  },

  beforeUnmount() {
    if (this.timeTimer) {
      clearInterval(this.timeTimer);
    }
    // 移除全局鼠标事件监听
    document.removeEventListener('mousemove', this.onResize);
    document.removeEventListener('mouseup', this.stopResize);
  },

  methods: {
    async fetchGasRegistry() {
      try {
        const response = await fetch(`/api/detections/gas/registry`);
        if (response.ok) {
          this.gasRegistry = await response.json();
        }
      } catch (e) {
        console.error('Failed to fetch gas registry:', e);
      }
    },

    getDevicesByPerson(personName) {
      // personName 现在实际是"场地名（workshop）"
      return this.devicesByWorkshop[personName] || {};
    },

    toggleArea(personName) {
      if (this.expandedAreas[personName] === undefined) {
        this.expandedAreas[personName] = true;
      } else {
        this.expandedAreas[personName] = !this.expandedAreas[personName];
      }
    },

    togglePerson(personName, deviceName) {
      const key = `${personName}_${deviceName}`;
      if (this.expandedPersons[key] === undefined) {
        this.expandedPersons[key] = true;
      } else {
        this.expandedPersons[key] = !this.expandedPersons[key];
      }
    },

    toggleGasData(deviceNumber) {
      if (this.expandedGasData[deviceNumber] === undefined) {
        this.expandedGasData[deviceNumber] = true;
      } else {
        this.expandedGasData[deviceNumber] = !this.expandedGasData[deviceNumber];
      }
    },

    /**
     * 切换工作详情信息展开状态
     * @param {string} personName - 设备负责人名称（从后端数据动态获取）
     * @param {string} deviceName - 设备名称（从后端数据动态获取）
     */
    toggleWorkDetail(personName, deviceName) {
      const key = `${personName}_${deviceName}_workDetail`;
      if (this.expandedWorkDetail[key] === undefined) {
        this.expandedWorkDetail[key] = true;
      } else {
        this.expandedWorkDetail[key] = !this.expandedWorkDetail[key];
      }
    },

    /**
     * 切换工作环境数据信息展开状态
     * @param {string} personName - 设备负责人名称（从后端数据动态获取）
     * @param {string} deviceName - 设备名称（从后端数据动态获取）
     */
    toggleEnvData(personName, deviceName) {
      const key = `${personName}_${deviceName}_envData`;
      if (this.expandedEnvData[key] === undefined) {
        this.expandedEnvData[key] = true;
      } else {
        this.expandedEnvData[key] = !this.expandedEnvData[key];
      }
    },

    /**
     * 切换远程设备控制展开状态
     * @param {string} personName - 设备负责人名称（从后端数据动态获取）
     * @param {string} deviceName - 设备名称（从后端数据动态获取）
     */
    toggleRemoteControl(personName, deviceName) {
      const key = `${personName}_${deviceName}_remoteControl`;
      if (this.expandedRemoteControl[key] === undefined) {
        this.expandedRemoteControl[key] = true;
      } else {
        this.expandedRemoteControl[key] = !this.expandedRemoteControl[key];
      }
    },

    /**
     * 打开摄像头实时画面弹窗
     * @param {Object} deviceInfo - 设备信息对象（从后端数据动态获取）
     */
    openLiveModal(deviceInfo) {
      this.liveModalDeviceId = deviceInfo.deviceNumber;
      this.liveModalDeviceInfo = deviceInfo;
      this.showLiveModal = true;
    },

    /**
     * 关闭摄像头实时画面弹窗
     */
    closeLiveModal() {
      this.showLiveModal = false;
      this.liveModalDeviceId = null;
      this.liveModalDeviceInfo = null;
    },

    /**
     * 获取设备视频流URL
     * @param {number|string} deviceNumber - 设备编号（从后端数据动态获取）
     * @returns {string} 视频流URL，格式: http://{hostname}:5020/video_feed/{deviceNumber}
     */
    getVideoStreamUrl(deviceNumber) {
      const baseUrl = `${window.location.protocol}//${window.location.hostname}:5020`;
      return `${baseUrl}/video_feed/${deviceNumber}`;
    },

    /**
     * 格式化时间显示，去除ISO格式中的T
     */
    formatTime(timeStr) {
      if (!timeStr || timeStr === '--') {
        return '--';
      }
      // 将 ISO 格式的 T 替换为空格
      return String(timeStr).replace('T', ' ');
    },

    /**
     * 获取结束时间显示
     */
    getEndTimeDisplay(deviceInfo) {
      if (deviceInfo.work_status === '进行中' || !deviceInfo.work_end_time) {
        return '工作中';
      }
      return this.formatTime(deviceInfo.work_end_time);
    },

    getGasValue(deviceNumber, gasType) {
      const deviceGasData = this.gasData[deviceNumber] || this.gasData[String(deviceNumber)];
      if (!deviceGasData) {
        return '--';
      }
      let value = deviceGasData[gasType];
      if (value === undefined || value === null || value === '') {
        return '--';
      }
      // 去除数据中可能包含的单位符号（如 ℃、°C、%、ppm 等）
      if (typeof value === 'string') {
        value = value.replace(/[℃°C%ppm]/g, '').trim();
      }
      return value;
    },

    isGasOverThreshold(deviceNumber, gasType) {
      const deviceGasData = this.gasData[deviceNumber] || this.gasData[String(deviceNumber)];
      const deviceThreshold = this.gasThreshold[deviceNumber] || this.gasThreshold[String(deviceNumber)];
      
      if (!deviceGasData || !deviceThreshold) {
        return false;
      }
      
      const value = parseFloat(deviceGasData[gasType]);
      const threshold = parseFloat(deviceThreshold[gasType]);
      
      if (isNaN(value) || isNaN(threshold) || threshold === 0) {
        return false;
      }
      
      return value > threshold;
    },

    // 拖拽调整宽度相关方法
    startResize(e) {
      this.isResizing = true;
      e.preventDefault();
    },

    onResize(e) {
      if (!this.isResizing) return;
      
      const newWidth = e.clientX;
      if (newWidth >= this.minWidth && newWidth <= this.maxWidth) {
        this.sidebarWidth = newWidth;
      }
    },

    stopResize() {
      this.isResizing = false;
    },

    handleBatchControl(person, action) {
      // person 现在是"场地名（workshop）"。直接展开成 device_id 列表传给父组件，
      // 避免父组件还按 areaDevices[person]（按区域负责人分组）查不到设备。
      const devicesMap = this.devicesByWorkshop[person] || {};
      const deviceIds = Object.values(devicesMap)
        .map(d => d && d.device_id)
        .filter(Boolean);
      this.$emit('batch-control', { workshop: person, deviceIds, action });
    },

    handlePtzStart(direction, deviceId) {
      this.$emit('device-control', deviceId, direction);
    },

    handlePtzStop(deviceId) {
      this.$emit('device-control', deviceId, 'stop');
    },

    handleDeviceControl(action, deviceId) {
      this.$emit('device-control', deviceId, action);
    },

    handleOpenConfigAdjust(deviceId) {
      if (deviceId === undefined || deviceId === null || deviceId === '') {
        console.warn('DeviceSidebar: No valid device SN for config adjustment');
        return;
      }
      this.$emit('open-config-adjust', String(deviceId));
    },

    startTimeUpdate() {
      this.updateTime();
      this.timeTimer = setInterval(this.updateTime, 1000);
    },

    updateTime() {
      const now = new Date();
      const year = now.getFullYear();
      const month = String(now.getMonth() + 1).padStart(2, '0');
      const day = String(now.getDate()).padStart(2, '0');
      const hours = String(now.getHours()).padStart(2, '0');
      const minutes = String(now.getMinutes()).padStart(2, '0');
      const seconds = String(now.getSeconds()).padStart(2, '0');
      this.currentDate = `${year}-${month}-${day}`;
      this.currentTime = `${hours}:${minutes}:${seconds}`;
    },

    /**
     * 格式化设备负责人显示名称
     * 将负责人名称和设备编号组合显示
     * @param {string} personName - 负责人名称（从后端数据动态获取）
     * @param {Object} deviceInfo - 设备信息对象（从后端数据动态获取）
     * @returns {string} 格式化后的显示名称，如"李四（设备1）"
     */
    formatPersonDisplay(personName, deviceInfo) {
      const deviceNum = deviceInfo && deviceInfo.deviceNumber !== undefined 
        ? deviceInfo.deviceNumber 
        : '--';
      return `${personName}（设备${deviceNum}）`;
    }
  }
};
</script>


<style scoped>
/* 全局字体优化 */
.device-sidebar {
  position: relative;
  height: 100%;
  transition: width 0.3s ease;
  overflow: hidden;
  font-family: 'Microsoft YaHei', 'PingFang SC', 'Helvetica Neue', Arial, sans-serif;
}

.device-sidebar.collapsed {
  width: 0 !important;
}

.sidebar-content {
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
}

/* 时间显示区域 */
.time-display-box {
  position: relative;
  height: 60px;
  margin-bottom: 5px;
  margin-top: 5px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  background-color: rgba(13, 19, 33, 0.8);
  box-shadow: 0 0 10px rgb(89, 89, 89);
  border: 1px solid rgb(89, 89, 89);
}

.time-content {
  width: 80%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 1px;
}

.time-loading {
  color: #888;
}

/* 区域设备列表区域 */
.area-device-box {
  border-radius: 6px;
  background-color: transparent;
  box-shadow: none;
  border: none;
  padding: 10px;
  min-height: calc(100% - 80px);
}

/* ==================== 第一层：区域负责人样式 ==================== */
.area-list {
  list-style-type: none;
  padding: 0;
  margin: 0;
}

.area-item {
  margin-bottom: 8px;
}

.area-header {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  background: linear-gradient(135deg, rgba(, , , 0.35) 0%, rgba(, , , 0.35) 100%);
  border: 1px solid rgba(, , , 0.35);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.area-header:hover {
  background: linear-gradient(135deg, rgba(, , , 0.35) 0%, rgba(, , , 0.35) 100%);
  border-color: rgba(, , , 0.35);
}

.area-name {
  color: #4bb8ff;
  font-size: 15px;
  font-weight: 600;
  flex: 1;
  text-align: left;
}

/* ==================== 第二层：设备负责人样式 ==================== */
.person-list {
  list-style-type: none;
  padding: 0;
  margin: 8px 0 0 16px;
}

.person-item {
  margin-bottom: 6px;
}

.person-header {
  display: flex;
  align-items: center;
  padding: 8px 10px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.person-header:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
}

.person-name {
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  flex: 1;
  margin-left: 4px;
  text-align: left;
}

/* 设备负责人名称徽章样式 */
.person-name-badge {
  color: #e0e0e0;
  font-size: 13px;
  font-weight: 500;
  padding: 4px 10px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  margin-left: 4px;
  margin-right: 8px;
  text-align: left;
  max-width: 120px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis; /* 超出部分用省略号表示 */
}

/* 在线/离线状态徽章 */
.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  min-width: 50px;
  text-align: center;
}

.status-badge.online {
  background: rgba(103, 194, 58, 0.2);
  color: #67c23a;
  border: 1px solid rgba(103, 194, 58, 0.4);
}

.status-badge.offline {
  background: rgba(245, 108, 108, 0.2);
  color: #f56c6c;
  border: 1px solid rgba(245, 108, 108, 0.4);
}

/* 实时画面按钮 */
.live-view-btn {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  min-width: 50px;
  text-align: center;
  color: #72cfff;
  background: rgba(79, 195, 247, 0.15);
  border: 1px solid rgba(79, 195, 247, 0.4);
  cursor: pointer;
  transition: all 0.3s ease;
  margin-left: 8px;
}

.live-view-btn:hover {
  background: rgba(79, 195, 247, 0.3);
  border-color: rgba(79, 195, 247, 0.6);
}

/* 展开/折叠图标 */
.expand-icon {
  color: #888;
  font-size: 10px;
  margin-right: 8px;
  transition: transform 0.3s ease;
}

/* ==================== 第三层：作业信息面板样式 ==================== */
.work-info-panel {
  margin: 8px 0 0 24px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

/* 每个信息字段单独一个卡片 */
.info-card {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background: rgba(30, 40, 60, 0.6);
  border: 1px solid rgba(100, 120, 150, 0.3);
  border-radius: 4px;
  transition: all 0.2s ease;
}

.info-card:hover {
  background: rgba(40, 50, 70, 0.7);
  border-color: rgba(100, 120, 150, 0.5);
}

.info-label {
  color: #4bb8ff;
  font-size: 13px;
  font-weight: 500;
  min-width: 130px;
  flex-shrink: 0;
}

.info-value {
  color: #fff;
  font-size: 13px;
  flex: 1;
  text-align: left;
  word-break: break-all;
}

/* 作业起止时间卡片 - 强制换行 */
.time-card {
  flex-direction: column;
  align-items: flex-start;
}

.time-card .info-label {
  margin-bottom: 6px;
}

.time-value {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.time-row {
  color: #fff;
  font-size: 13px;
  padding: 4px 8px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 3px;
}

/* 设备状态卡片（可点击） */
.device-status-card {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background: rgba(30, 40, 60, 0.6);
  border: 1px solid rgba(100, 120, 150, 0.3);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.device-status-card:hover {
  background: rgba(40, 50, 70, 0.7);
  border-color: rgba(100, 120, 150, 0.5);
}

.device-status-card .status-value {
  font-size: 13px;
  font-weight: 500;
  flex: 1;
  text-align: left;
}

.device-status-card .status-value.online {
  color: #67c23a;
}

.device-status-card .status-value.offline {
  color: #f56c6c;
}

.device-status-card .expand-hint {
  color: #888;
  font-size: 10px;
}

/* ==================== 第四层：气体数据面板样式 ==================== */
.gas-data-panel {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 4px;
}

/* 气体数据卡片 */
.gas-card {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  border-radius: 4px;
  transition: all 0.3s ease;
}

/* 正常状态 - 绿色闪烁 */
.gas-card.normal {
  background: rgba(103, 194, 58, 0.15);
  border: 1px solid rgba(103, 194, 58, 0.4);
  animation: normalPulse 2s ease-in-out infinite;
}

/* 报警状态 - 红色闪烁 */
.gas-card.alarm {
  background: rgba(245, 108, 108, 0.25);
  border: 1px solid rgba(245, 108, 108, 0.6);
  animation: alarmPulse 0.8s ease-in-out infinite;
}

@keyframes normalPulse {
  0%, 100% {
    background: rgba(103, 194, 58, 0.1);
    box-shadow: 0 0 5px rgba(103, 194, 58, 0.2);
  }
  50% {
    background: rgba(103, 194, 58, 0.2);
    box-shadow: 0 0 10px rgba(103, 194, 58, 0.4);
  }
}

@keyframes alarmPulse {
  0%, 100% {
    background: rgba(245, 108, 108, 0.2);
    box-shadow: 0 0 8px rgba(245, 108, 108, 0.4);
  }
  50% {
    background: rgba(245, 108, 108, 0.4);
    box-shadow: 0 0 15px rgba(245, 108, 108, 0.7);
  }
}

.gas-label {
  color: #7ec8e3;
  font-size: 13px;
  font-weight: 500;
  min-width: 90px;
}

.gas-value {
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  flex: 1;
  text-align: left;
  margin-left: 10px;
}

.gas-card.alarm .gas-value {
  color: #ff6b6b;
}

.gas-unit {
  color: #909399;
  font-size: 12px;
  margin-left: 4px;
}

/* 摄像头控制组件居中包装 */
.camera-control-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 10px;
}

.config-adjust-group {
  margin-top: 0;
}

.config-adjust-header {
  width: 100%;
  border: 1px solid rgba(, , , 0.35) !important;
  background: linear-gradient(135deg, rgba(, , , 0.35) 0%, rgba(, , , 0.35) 100%) !important;
  color: #4bb8ff;
}

.config-adjust-header:hover {
  background: linear-gradient(135deg, rgba(, , , 0.35) 0%, rgba(, , , 0.35) 100%) !important;
  border-color: rgba(, , , 0.35) !important;
}

.config-adjust-header .group-title {
  color: #4bb8ff;
}

/* 摄像头实时画面按钮样式 - 与折叠分组对齐 */
.live-camera-header {
  background: linear-gradient(135deg, rgba(79, 195, 247, 0.2) 0%, rgba(79, 195, 247, 0.1) 100%) !important;
  border-color: rgba(79, 195, 247, 0.4) !important;
}

.live-camera-header:hover {
  background: linear-gradient(135deg, rgba(79, 195, 247, 0.35) 0%, rgba(79, 195, 247, 0.2) 100%) !important;
  border-color: rgba(79, 195, 247, 0.6) !important;
}

.live-camera-header .btn-icon {
  font-size: 14px;
  margin-right: 6px;
}

.live-camera-header .group-title {
  color: #72cfff;
}

.click-hint {
  color: rgba(79, 195, 247, 0.7);
  font-size: 11px;
  margin-left: auto;
}

/* 拖拽调整宽度的手柄 */
.resize-handle {
  position: absolute;
  right: 0;
  top: 0;
  width: 6px;
  height: 100%;
  cursor: ew-resize;
  background: transparent;
  transition: background 0.2s ease;
  z-index: 101;
}

.resize-handle:hover {
  background: rgba(64, 158, 255, 0.5);
}

.resize-handle:active {
  background: rgba(64, 158, 255, 0.8);
}

/* 滚动条样式 */
.sidebar-content::-webkit-scrollbar {
  width: 6px;
}

.sidebar-content::-webkit-scrollbar-track {
  background: transparent;
}

.sidebar-content::-webkit-scrollbar-thumb {
  background-color: rgba(255, 255, 255, 0.3);
  border-radius: 3px;
}

.sidebar-content::-webkit-scrollbar-thumb:hover {
  background-color: rgba(255, 255, 255, 0.5);
}

/* ==================== 折叠分组通用样式 ==================== */
/* 
 * 折叠分组容器
 * 用于包装工作详情信息、工作环境数据信息、远程设备控制等可折叠区域
 * Requirements: 2.1, 3.1, 5.1
 */
.collapsible-group {
  margin-bottom: 6px;
  border-radius: 5px;
  overflow: hidden;
}

/* 
 * 分组标题样式（包含展开/折叠图标）
 * Requirements: 2.1, 2.5, 3.1, 3.5, 5.1, 5.4
 */
.group-header {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  background: linear-gradient(135deg, rgba(, , , 0.35) 0%, rgba(, , , 0.35) 100%);
  border: 1px solid rgba(, , , 0.35);
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.3s ease;
  user-select: none;
}

.group-header:hover {
  background: linear-gradient(135deg, rgba(, , , 0.35) 0%, rgba(, , , 0.35) 100%);
  border-color: rgba(, , , 0.35);
  transform: translateX(2px);
}

.group-header:active {
  transform: translateX(0);
}

/* 分组标题中的展开/折叠图标样式 */
.group-header .expand-icon {
  color: #4bb8ff;
  font-size: 10px;
  margin-right: 8px;
  transition: transform 0.3s ease, color 0.3s ease;
  flex-shrink: 0;
}

.group-header:hover .expand-icon {
  color: #38ffec;
}

/* 分组标题文字样式 */
.group-title {
  color: #4bb8ff;
  font-size: 13px;
  font-weight: 600;
  flex: 1;
  text-align: left;
  letter-spacing: 0.5px;
}

.group-header:hover .group-title {
  color: #38ffec;
}

/* 
 * 分组内容区域样式
 * 折叠时隐藏，展开时显示
 * Requirements: 2.5, 3.5, 5.4
 */
.group-content {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 6px;
  padding: 8px;
  padding-left: 12px;
  background: rgba(20, 30, 50, 0.3);
  border: 1px solid rgba(, , , 0.35);
  border-top: none;
  border-radius: 0 0 5px 5px;
  animation: slideDown 0.3s ease-out;
}

/* 分组内容展开动画 */
@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 当分组展开时，调整标题样式 */
.collapsible-group:has(.group-content) .group-header {
  border-radius: 5px 5px 0 0;
  border-bottom-color: transparent;
}
</style>
