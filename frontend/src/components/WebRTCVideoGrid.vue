<template>
  <div class="webrtc-video-grid-container">
    <!-- 顶部工具栏 -->
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

      <div class="video-info">
        <span class="stat">在线摄像头：{{ paths.length }} 路</span>
        <button class="refresh-btn" @click="refreshPaths" :disabled="loading">
          {{ loading ? '刷新中...' : '刷新摄像头' }}
        </button>
      </div>

      <div class="video-pagination-controls">
        <button type="button" class="video-page-btn" @click="navigate('prev')">
          {{ displayMode === 'one' ? '上一张' : '上一组' }}
        </button>
        <span class="page-info">{{ currentIndex + 1 }} / {{ totalItems }}</span>
        <button type="button" class="video-page-btn" @click="navigate('next')">
          {{ displayMode === 'one' ? '下一张' : '下一组' }}
        </button>
      </div>
    </div>

    <!-- 视频网格 -->
    <div class="grid" :class="displayMode">
      <!--
        v-show 控制：没视频流的格子隐藏（display:none 不占 grid 空间）
        但组件不销毁，继续在后台尝试重连
      -->
      <WhepVideoCell
        v-for="item in displayPaths"
        v-show="pathStates[item.path] === 'playing'"
        :key="item.path"
        :path="item.path"
        :label="item.label"
        :base-url="baseUrl"
        :rotation="getRotationForPath(item.path)"
        :alarming="isAlarming(item.path)"
        :detections="getDetectionsForPath(item.path)"
        :show-detections="detectionConnected"
        :gas-info="getGasInfoForPath(item.path)"
        @click="handleCellClick"
        @state-change="handlePathStateChange"
      />
      <!-- 空槽位：填满有流数量之外的格子 -->
      <div
        v-for="i in emptySlots"
        :key="'empty-' + i"
        class="empty-cell">
        <img :src="defaultImage" alt="no video" />
      </div>
    </div>

    <!-- 空状态提示 -->
    <div v-if="paths.length === 0 && !loading" class="empty-state">
      未发现在线摄像头。请确认 mediamtx 已启动并有流推入。
    </div>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted } from 'vue';
import WhepVideoCell from './WhepVideoCell.vue';
import { getMediamtxBaseUrl, fetchOnlinePaths } from '@/utils/mediamtx';
import { DISPLAY_MODE_CELLS, DEFAULT_IMAGE } from '@/utils/constants';
import { useDetectionStream } from '@/composables/useDetectionStream';

export default {
  name: 'WebRTCVideoGrid',
  
  components: {
    WhepVideoCell
  },
  
  props: {
    alarmStatus: {
      type: Object,
      default: () => ({})
    },
    gasData: {
      type: Object,
      default: () => ({})
    },
    /**
     * 设备旋转角度映射 { device_id: rotation }
     * rotation: 0=正常, 180=倒装
     */
    deviceRotationMap: {
      type: Object,
      default: () => ({})
    }
  },
  
  emits: ['select'],
  
  setup(props, { emit }) {
    const paths = ref([]);
    const loading = ref(false);
    const displayMode = ref('nine');
    const currentIndex = ref(0);
    const defaultImage = DEFAULT_IMAGE;
    
    // 跟踪每个路径的播放状态: { pathName: 'playing' | 'connecting' | 'error' | ... }
    const pathStates = reactive({});
    
    const baseUrl = getMediamtxBaseUrl();
    
    // 集成检测框 SSE 订阅
    const { detections, connected: detectionConnected } = useDetectionStream();
    
    function getDetectionsForPath(path) {
      return detections.value[path] || null;
    }
    
    function getRotationForPath(path) {
      return props.deviceRotationMap[path] ?? 0;
    }
    
    function getGasInfoForPath(path) {
      const data = props.gasData[path] || props.gasData[String(path)] || null;
      if (!data) return null;
      return {
        o2: formatGasValue(data.O2),
        temp: formatGasValue(data.TEMP),
        rh: formatGasValue(data.RH)
      };
    }
    
    function formatGasValue(value) {
      if (value === null || value === undefined || value === '' || value === '-1') return '-';
      const num = parseFloat(value);
      if (Number.isNaN(num)) return '-';
      return String(Math.trunc(num));
    }
    
    const cellCount = computed(() => DISPLAY_MODE_CELLS[displayMode.value] || 9);
    
    // 不做排序，保持原始顺序，避免 state 变化时组件被销毁重建
    const displayPaths = computed(() => {
      return paths.value.slice(currentIndex.value, currentIndex.value + cellCount.value)
        .map(p => ({ path: p.name, label: p.name }));
    });
    
    const totalItems = computed(() => paths.value.length);
    
    // 当前页实际 playing 的数量
    const playingCount = computed(() => {
      return displayPaths.value.filter(p => pathStates[p.path] === 'playing').length;
    });
    
    // 空槽位 = 总格子数 - 正在播放的数量
    const emptySlots = computed(() => {
      const count = cellCount.value - playingCount.value;
      return count > 0 ? count : 0;
    });
    
    function handlePathStateChange({ path, state }) {
      pathStates[path] = state;
    }
    
    function isAlarming(path) {
      return props.alarmStatus[path] === true;
    }
    
    async function refreshPaths() {
      loading.value = true;
      try {
        const items = await fetchOnlinePaths();
        paths.value = items;
      } catch (e) {
        console.error('刷新摄像头失败:', e);
      } finally {
        loading.value = false;
      }
    }
    
    function changeMode(mode) {
      displayMode.value = mode;
      currentIndex.value = 0;
    }
    
    function navigate(direction) {
      const step = cellCount.value;
      if (direction === 'prev') {
        currentIndex.value = Math.max(0, currentIndex.value - step);
      } else {
        const newIndex = currentIndex.value + step;
        if (newIndex < paths.value.length) {
          currentIndex.value = newIndex;
        }
      }
    }
    
    function handleCellClick(path) {
      // 设备ID就是 mediamtx 路径名（数据库里 device_id = cam1, cam-238 等）
      emit('select', { path, deviceId: path });
    }
    
    onMounted(() => {
      refreshPaths();
    });
    
    return {
      paths,
      loading,
      displayMode,
      currentIndex,
      baseUrl,
      defaultImage,
      cellCount,
      totalItems,
      displayPaths,
      emptySlots,
      pathStates,
      isAlarming,
      getGasInfoForPath,
      refreshPaths,
      changeMode,
      navigate,
      handleCellClick,
      handlePathStateChange,
      detectionConnected,
      getDetectionsForPath,
      getRotationForPath
    };
  }
};
</script>

<style scoped>
.webrtc-video-grid-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  min-height: 0;
  overflow: hidden;
  box-sizing: border-box;
}

/* 顶部工具栏 - 匹配 VideoGrid 蓝色科技风 */
.video-toolbar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  min-height: 34px;
  gap: 16px;
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

.video-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stat {
  color: #e6f6ff;
  font-size: 14px;
}

.refresh-btn {
  height: 28px;
  padding: 0 12px;
  border: 1px solid rgba(220, 242, 255, 0.74);
  border-radius: 3px;
  background: linear-gradient(180deg, rgba(52, 162, 120, 0.98), rgba(38, 132, 96, 0.98));
  color: #f7fcff;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease;
}

.refresh-btn:hover:not(:disabled) {
  background: linear-gradient(180deg, rgba(62, 182, 140, 1), rgba(48, 152, 116, 1));
  border-color: rgba(134, 212, 255, 0.98);
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.video-pagination-controls {
  display: flex;
  gap: 8px;
  align-items: center;
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

.page-info {
  color: #e6f6ff;
  font-size: 14px;
  min-width: 60px;
  text-align: center;
}

/* 视频网格 - 匹配 VideoGrid 蓝色科技风 */
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

/* 空槽位：蓝色渐变背景 + 默认图片，匹配 VideoGrid 风格 */
.empty-cell {
  position: relative;
  min-height: 0;
  overflow: hidden;
  border: 1px solid rgba(156, 225, 255, 0.88);
  background: linear-gradient(180deg, rgba(110, 205, 255, 0.58), rgba(56, 162, 235, 0.52));
  box-shadow: inset 0 0 22px rgba(124, 214, 255, 0.34);
  border-radius: 4px;
  box-sizing: border-box;
}

.empty-cell::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(122, 212, 255, 0.20), rgba(78, 182, 245, 0.12));
  pointer-events: none;
}

.empty-cell img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  opacity: 0.6;
}

.empty-state {
  padding: 40px;
  text-align: center;
  color: #e6f6ff;
  font-size: 15px;
}

/* 让 WhepVideoCell 也使用蓝色科技边框 */
.grid > :deep(.whep-video-cell) {
  border: 1px solid rgba(156, 225, 255, 0.88);
  background: linear-gradient(180deg, rgba(110, 205, 255, 0.12), rgba(56, 162, 235, 0.08));
  box-shadow: inset 0 0 22px rgba(124, 214, 255, 0.14);
  border-radius: 4px;
}

.grid > :deep(.whep-video-cell:hover) {
  border-color: rgba(134, 212, 255, 0.98);
  box-shadow: inset 0 0 22px rgba(124, 214, 255, 0.24), 0 0 10px rgba(71, 184, 255, 0.2);
}

.grid > :deep(.whep-video-cell.is-alarming) {
  border-color: #ff0000;
  animation: alarmBlink 1s infinite;
}

/* 报警闪烁动画 */
@keyframes alarmBlink {
  0% {
    border-color: #ff0000;
    box-shadow: 0 0 10px #ff0000;
  }
  50% {
    border-color: #ff6666;
    box-shadow: 0 0 20px #ff6666;
  }
  100% {
    border-color: #ff0000;
    box-shadow: 0 0 10px #ff0000;
  }
}

</style>

