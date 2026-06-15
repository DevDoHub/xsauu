<template>
  <div class="video-grid-container">
    <!-- 顶部工具栏：左侧分屏图标 + 右侧翻页按钮 -->
    <div class="video-toolbar">
      <div class="video-mode-switcher">
        <span class="mode-label">分屏:</span>
        <button 
          type="button"
          :class="['video-mode-btn', { 'is-active': displayMode === 'one' }]"
          @click="changeMode('one')"
          title="单画面">
          <svg viewBox="0 0 16 16" class="mode-icon"><rect x="1" y="1" width="14" height="14" rx="1"/></svg>
        </button>
        <button 
          type="button"
          :class="['video-mode-btn', { 'is-active': displayMode === 'four' }]" 
          @click="changeMode('four')"
          title="四宫格">
          <svg viewBox="0 0 16 16" class="mode-icon"><rect x="1" y="1" width="6" height="6" rx="0.5"/><rect x="9" y="1" width="6" height="6" rx="0.5"/><rect x="1" y="9" width="6" height="6" rx="0.5"/><rect x="9" y="9" width="6" height="6" rx="0.5"/></svg>
        </button>
        <button 
          type="button"
          :class="['video-mode-btn', { 'is-active': displayMode === 'nine' }]"
          @click="changeMode('nine')"
          title="九宫格">
          <svg viewBox="0 0 16 16" class="mode-icon"><rect x="1" y="1" width="4" height="4" rx="0.3"/><rect x="6" y="1" width="4" height="4" rx="0.3"/><rect x="11" y="1" width="4" height="4" rx="0.3"/><rect x="1" y="6" width="4" height="4" rx="0.3"/><rect x="6" y="6" width="4" height="4" rx="0.3"/><rect x="11" y="6" width="4" height="4" rx="0.3"/><rect x="1" y="11" width="4" height="4" rx="0.3"/><rect x="6" y="11" width="4" height="4" rx="0.3"/><rect x="11" y="11" width="4" height="4" rx="0.3"/></svg>
        </button>
        <button 
          type="button"
          :class="['video-mode-btn', { 'is-active': displayMode === 'sixteen' }]"
          @click="changeMode('sixteen')"
          title="16宫格">
          <svg viewBox="0 0 16 16" class="mode-icon"><rect x="1" y="1" width="3" height="3" rx="0.2"/><rect x="5" y="1" width="3" height="3" rx="0.2"/><rect x="9" y="1" width="3" height="3" rx="0.2"/><rect x="13" y="1" width="2" height="3" rx="0.2"/><rect x="1" y="5" width="3" height="3" rx="0.2"/><rect x="5" y="5" width="3" height="3" rx="0.2"/><rect x="9" y="5" width="3" height="3" rx="0.2"/><rect x="13" y="5" width="2" height="3" rx="0.2"/><rect x="1" y="9" width="3" height="3" rx="0.2"/><rect x="5" y="9" width="3" height="3" rx="0.2"/><rect x="9" y="9" width="3" height="3" rx="0.2"/><rect x="13" y="9" width="2" height="3" rx="0.2"/><rect x="1" y="13" width="3" height="2" rx="0.2"/><rect x="5" y="13" width="3" height="2" rx="0.2"/><rect x="9" y="13" width="3" height="2" rx="0.2"/><rect x="13" y="13" width="2" height="2" rx="0.2"/></svg>
        </button>
        <select class="mode-select" :value="displayMode" @change="changeMode($event.target.value)">
          <option value="one">1×</option>
          <option value="four">4×</option>
          <option value="nine">9×</option>
          <option value="sixteen">16×</option>
        </select>
      </div>

      <div class="video-pagination-controls">
        <button type="button" class="video-page-btn" @click="navigate('prev')">
          {{ displayMode === 'one' ? '上一张' : '上一组' }}
        </button>
        <button type="button" class="video-page-btn" @click="navigate('next')">
          {{ displayMode === 'one' ? '下一张' : '下一组' }}
        </button>
      </div>
    </div>

    <!-- 视频网格 -->
    <div class="grid" :class="displayMode">
      <div 
        v-for="(image, index) in computedImages" 
        :key="index"
        @click="handleCellClick(image, index)"
        :class="{ 'alarming': isDeviceAlarming(getDeviceId(index)) }">
        <img 
          :src="image" 
          alt="video feed" 
          :class="{ 'selected': isSelected(image) }">
        <!-- 左下角信息条：区域 + O2 + 温度 + 湿度 -->
        <div v-if="getDeviceId(index) !== null" class="video-overlay">
          <!-- <span class="overlay-item overlay-device">设备{{ getDeviceId(index) }}</span> -->
          <span class="overlay-item">{{ getOverlayData(index).workshop }}</span>
          <span class="overlay-item">氧气：{{ getOverlayData(index).o2 }}%</span>
          <span class="overlay-item">温度：{{ getOverlayData(index).temp }}°C</span>
          <span class="overlay-item">湿度：{{ getOverlayData(index).rh }}%</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { DISPLAY_MODES, DISPLAY_MODE_CELLS, DEFAULT_IMAGE } from '@/utils/constants';

export default {
  name: 'VideoGrid',
  
  props: {
    /**
     * 视频源URL数组
     * @type {Array<string>}
     */
    images: {
      type: Array,
      required: true,
      default: () => []
    },
    
    /**
     * 显示位置到设备ID的映射表
     * @type {Object<number, number>}
     */
    displayIndexToDeviceId: {
      type: Object,
      default: () => ({})
    },

    /**
     * 每个格子的温湿度及区域叠加数据
     * @type {Object<number, {deviceId: string, temp: string, rh: string, workshop: string}>}
     */
    overlayMap: {
      type: Object,
      default: () => ({})
    },
    
    /**
     * 显示模式: 'one' | 'four' | 'nine' | 'sixteen'
     * @type {string}
     */
    displayMode: {
      type: String,
      required: true,
      default: DISPLAY_MODES.NINE,
      validator: (value) => Object.values(DISPLAY_MODES).includes(value)
    },
    
    /**
     * 报警状态对象
     * @type {Object<string, { alarm_active: boolean }>}
     */
    alarmStatus: {
      type: Object,
      default: () => ({})
    },
    
    /**
     * 当前显示起始索引
     * @type {number}
     */
    currentIndex: {
      type: Number,
      default: 0
    },
    
    /**
     * 当前选中的图片URL（可选，用于高亮显示）
     * @type {string|null}
     */
    selectedImage: {
      type: String,
      default: null
    }
  },
  
  emits: ['select', 'mode-change', 'navigate'],
  
  computed: {
    /**
     * 根据显示模式计算当前应显示的图片
     * @returns {Array<string>}
     */
    computedImages() {
      const cellCount = DISPLAY_MODE_CELLS[this.displayMode] || 9;
      const slice = this.images.slice(this.currentIndex, this.currentIndex + cellCount);
      // 用占位图填充空槽位（单画面/四宫格/九宫格）
      if (slice.length === 0) {
        slice.push(DEFAULT_IMAGE);
      }
      while (slice.length < cellCount) {
        slice.push(DEFAULT_IMAGE);
      }
      return slice;
    }
  },
  
  methods: {
    /**
     * 切换显示模式
     * @param {string} mode - 新的显示模式
     */
    changeMode(mode) {
      if (mode !== this.displayMode) {
        this.$emit('mode-change', mode);
      }
    },
    
    /**
     * 处理视频单元格点击
     * @param {string} image - 点击的图片URL
     * @param {number} index - 在当前视图中的索引
     */
    handleCellClick(image, index) {
      const deviceId = this.getDeviceId(index);
      // 传递真实的设备ID（如果有的话）
      this.$emit('select', deviceId !== null ? String(deviceId) : null, image);
    },
    
    /**
     * 根据当前显示位置获取真实的设备ID
     * @param {number} index - 在当前视图中的索引
     * @returns {number|null} 真实的设备ID，如果该位置没有设备则返回null
     */
    getDeviceId(index) {
      const actualIndex = this.currentIndex + index;
      const deviceId = this.displayIndexToDeviceId[actualIndex];
      // 使用严格比较，避免设备ID为0时被错误判断为falsy
      return deviceId !== undefined && deviceId !== null ? deviceId : null;
    },

    /**
     * 获取当前格子的气氧温湿度及区域显示数据
     * @param {number} index - 在当前视图中的索引
     * @returns {{deviceId: string, temp: string, rh: string, o2: string, workshop: string}}
     */
    getOverlayData(index) {
      const actualIndex = this.currentIndex + index;
      const data = this.overlayMap?.[actualIndex] || {};

      return {
        deviceId: data.deviceId || '-',
        temp: data.temp ?? '-',
        rh: data.rh ?? '-',
        o2: data.o2 ?? '-',
        workshop: data.workshop || '-'
      };
    },
    
    /**
     * 检查设备是否处于报警状态
     * @param {number} deviceId - 设备ID
     * @returns {boolean}
     */
    isDeviceAlarming(deviceId) {
      if (!this.alarmStatus || deviceId === undefined || deviceId === null) {
        return false;
      }
      const deviceStatus = this.alarmStatus[String(deviceId)];
      return deviceStatus ? deviceStatus.alarm_active : false;
    },
    
    /**
     * 检查图片是否被选中
     * @param {string} image - 图片URL
     * @returns {boolean}
     */
    isSelected(image) {
      return this.selectedImage === image;
    },
    
    /**
     * 导航到上一张/组或下一张/组
     * @param {string} direction - 'prev' 或 'next'
     */
    navigate(direction) {
      this.$emit('navigate', direction);
    }
  }
};
</script>

<style scoped>
.video-grid-container {
  width: 100%;
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-sizing: border-box;
}

/* 顶部工具栏 */
.video-toolbar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  min-height: 34px;
}

.video-mode-switcher {
  display: flex;
  align-items: center;
  gap: 6px;
}

.mode-label {
  color: #e6f6ff;
  font-size: 16px;
  margin-right: 4px;
}

.video-mode-btn {
  width: 28px;
  height: 28px;
  padding: 4px;
  border: 1px solid rgba(220, 242, 255, 0.74);
  border-radius: 3px;
  background: linear-gradient(180deg, rgba(90, 179, 239, 0.98), rgba(52, 132, 198, 0.98));
  color: #f7fcff;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
  box-shadow: inset 0 0 16px rgba(132, 207, 255, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
}

.video-mode-btn .mode-icon {
  width: 16px;
  height: 16px;
  fill: #f0faff;
  transition: fill 0.2s ease;
}

.video-mode-btn.is-active,
.video-mode-btn:hover {
  border-color: rgba(134, 212, 255, 0.98);
  background: linear-gradient(180deg, rgba(116, 198, 250, 1), rgba(67, 152, 219, 1));
  box-shadow: inset 0 0 18px rgba(190, 234, 255, 0.4), 0 0 14px rgba(71, 184, 255, 0.34);
}

.video-mode-btn.is-active .mode-icon,
.video-mode-btn:hover .mode-icon {
  fill: #ffffff;
}

.video-page-btn {
  height: 28px;
  min-width: 60px;
  padding: 0 12px;
  border: 1px solid rgba(220, 242, 255, 0.74);
  border-radius: 3px;
  background: linear-gradient(180deg, rgba(90, 179, 239, 0.98), rgba(52, 132, 198, 0.98));
  color: #f7fcff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease, color 0.2s ease;
  box-shadow: inset 0 0 16px rgba(132, 207, 255, 0.3);
}

.video-page-btn:hover {
  color: #ffffff;
  border-color: rgba(134, 212, 255, 0.98);
  background: linear-gradient(180deg, rgba(116, 198, 250, 1), rgba(67, 152, 219, 1));
  box-shadow: inset 0 0 18px rgba(190, 234, 255, 0.4), 0 0 14px rgba(71, 184, 255, 0.34);
}

.video-pagination-controls {
  display: flex;
  gap: 8px;
}

.grid {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-gap: 10px;
  overflow: hidden;
}

.grid.one {
  grid-template-columns: 1fr;
  grid-template-rows: minmax(0, 1fr);
}

.grid.four {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-template-rows: repeat(2, minmax(0, 1fr));
}

.grid.nine {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  grid-template-rows: repeat(3, minmax(0, 1fr));
}

.grid.sixteen {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  grid-template-rows: repeat(4, minmax(0, 1fr));
}

.mode-select {
  height: 28px;
  padding: 0 8px;
  margin-left: 6px;
  border: 1px solid rgba(220, 242, 255, 0.78);
  border-radius: 3px;
  background: linear-gradient(180deg, rgba(99, 185, 242, 0.98), rgba(60, 143, 208, 0.98));
  color: #f8fcff;
  font-size: 14px;
  cursor: pointer;
  outline: none;
}

.mode-select:hover,
.mode-select:focus {
  border-color: rgba(134, 212, 255, 0.98);
}

.mode-select option {
  background: #5daee8;
  color: #f8fcff;
}

/* 报警闪烁动画 */
@keyframes alarmBlink {
  0% {
    border: 3px solid #ff0000;
    box-shadow: 0 0 10px #ff0000;
  }
  50% {
    border: 3px solid #ff6666;
    box-shadow: 0 0 20px #ff6666;
  }
  100% {
    border: 3px solid #ff0000;
    box-shadow: 0 0 10px #ff0000;
  }
}

/* 报警状态样式 */
.alarming {
  animation: alarmBlink 1s infinite;
  border-radius: 4px;
}

/* 确保图片容器有相对定位以便边框显示正确 */
.grid > div {
  position: relative;
  min-height: 0;
  overflow: hidden;
  border: 1px solid rgba(156, 225, 255, 0.88);
  background: linear-gradient(180deg, rgba(110, 205, 255, 0.58), rgba(56, 162, 235, 0.52));
  box-shadow: inset 0 0 22px rgba(124, 214, 255, 0.34);
  transition: border 0.3s ease, background 0.3s ease;
  cursor: pointer;
  box-sizing: border-box;
}

.grid > div::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(122, 212, 255, 0.20), rgba(78, 182, 245, 0.12));
  pointer-events: none;
}

.grid > div img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  background: rgba(88, 186, 245, 0.34);
}

.grid > div img.selected {
  border: 2px solid #4CAF50;
}

/* 左下角信息条 */
.video-overlay {
  position: absolute;
  left: 6px;
  bottom: 6px;
  z-index: 3;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px;
  max-width: calc(100% - 12px);
  background: rgba(0, 0, 0, 0.78);
  border-radius: 4px;
  pointer-events: none;
  box-sizing: border-box;
  overflow: hidden;
  white-space: nowrap;
  font-family: "Microsoft YaHei", "微软雅黑", Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: geometricPrecision;
}

.overlay-item {
  color: #fff;
  font-size: 13px;
  line-height: 1;
  font-weight: 600;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.95);
  flex-shrink: 0;
}

.overlay-device {
  font-weight: 700;
}
</style>
