<template>
  <div class="alarm-panel">
    <!-- 报警列表滚动容器 -->
    <div class="alarm-list-box">
      <div class="scroll-container">
        <div 
          v-for="(alarm, index) in reversedAlarmList" 
          :key="`${alarm.index}-${alarm.time}-${index}`" 
          class="alarm-card"
        >
          <!-- 图片区域 -->
          <div v-if="alarm.image" class="card-image-box" @click="openFullscreen(alarm)">
            <img :src="alarm.image" alt="报警截图" class="card-image" :style="getAlarmImageStyle(alarm)" />
          </div>
          <div v-else class="card-image-box card-image-empty">
            <span>无图片</span>
          </div>
          <!-- 信息区域 -->
          <div class="card-info">
            <div class="card-type">{{ alarm.type || '未知类型' }}</div>
            <div class="card-meta">#{{ formatCameraIndex(alarm.index) }} · {{ extractTime(alarm.time) }}</div>
            <div class="card-detail">{{ alarm.note || '未知区域' }}</div>
          </div>
        </div>

        <!-- 空状态提示 -->
        <div v-if="alarmList.length === 0" class="empty-state">
          <p>暂无报警记录</p>
        </div>
      </div>
    </div>

    <!-- 全屏图片查看器 -->
    <div v-if="fullscreenImage" class="fullscreen-viewer" @click="fullscreenImage = null">
      <img :src="fullscreenImage" alt="全屏截图" @click.stop />
      <button class="close-btn" @click="fullscreenImage = null; fullscreenImageIndex = null">×</button>
    </div>
  </div>
</template>

<script>
/**
 * AlarmPanel 组件
 * 负责报警信息展示和管理 (极致空间压缩版)
 */
export default {
  name: 'AlarmPanel',

  props: {
    alarmList: {
      type: Array,
      required: true,
      default: () => []
    },
  },

  data() {
    return {
      fullscreenImage: null
    };
  },

  computed: {
    /**
     * 按时间倒序排列的报警列表（最新的在最上面）
     */
    reversedAlarmList() {
      return [...(this.alarmList || [])].sort((a, b) => {
        return (b.time || '').localeCompare(a.time || '');
      });
    },

    /**
     * 设备旋转角度映射 { device_id: rotation }
     */
    deviceRotationMap() {
      const map = {};
      const areaDevices = this.$store?.state?.devices?.areaDevices || {};
      // areaDevices 结构: { "区域负责人": { "设备名": DeviceRespVO } }
      for (const areaName in areaDevices) {
        const devicesMap = areaDevices[areaName] || {};
        for (const deviceName in devicesMap) {
          const device = devicesMap[deviceName];
          if (device && typeof device === 'object') {
            const rotation = device.camera_rotation ?? 0;
            if (rotation) {
              map[String(device.device_id)] = rotation;
            }
          }
        }
      }
      return map;
    }
  },

  methods: {
    /**
     * 获取报警图片样式
     * 截图已在 captureSnapshot 中根据设备旋转角度做了180度翻转，
     * 保存的图片本身已经是正向的，展示时不再需要旋转。
     */
    getAlarmImageStyle(alarm) {
      return {};
    },
    formatCameraIndex(index) {
      const normalized = String(index ?? '').trim();
      return normalized || '--';
    },

    extractTime(fullTimeStr) {
      if (!fullTimeStr) return '--:--';
      const parts = fullTimeStr.split(' ');
      if (parts.length > 1) {
        return parts[1];
      }
      return fullTimeStr;
    },

    /**
     * 打开全屏图片查看
     */
    openFullscreen(alarm) {
      this.fullscreenImage = alarm.image;
    }
  }
};
</script>

<style scoped>
.alarm-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
}

.alarm-list-box {
  flex: 1;
  border-radius: 4px;
  background-color: transparent;
  overflow: hidden;
}

.scroll-container {
  height: 100%;
  overflow-y: auto;
  padding: 0 4px;
}

/* 报警卡片 */
.alarm-card {
  margin-bottom: 10px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.03);
  transition: border-color 0.2s, background 0.2s;
}

.alarm-card:hover {
  border-color: rgba(255, 184, 77, 0.4);
  background: rgba(255, 255, 255, 0.06);
}

.card-image-box {
  width: 100%;
  height: 120px;
  background: #000;
  cursor: pointer;
  overflow: hidden;
}

.card-image-box.card-image-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.3);
  color: #5a5a6a;
  font-size: 12px;
  cursor: default;
}

.card-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  /* 旋转由 prop 控制，通过 :style 动态绑定 */
}

.card-info {
  padding: 8px 10px;
}

.card-type {
  color: #ffad9b;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 4px;
}

.card-meta {
  color: #72cfff;
  font-size: 12px;
  margin-bottom: 3px;
}

.card-detail {
  color: #93939f;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 空状态 */
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100px;
  color: #75758a;
  font-size: 13px;
}

/* 全屏图片查看器 */
.fullscreen-viewer {
  position: fixed;
  top: 0;
  left: 0;
  width: 1920px;
  height: 1080px;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 10000;
}

.fullscreen-viewer img {
  max-width: 90%;
  max-height: 90%;
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.5);
  /* 旋转由 prop 控制，通过 :style 动态绑定 */
}

.fullscreen-viewer .close-btn {
  position: absolute;
  top: 20px;
  right: 30px;
  background: rgba(255, 255, 255, 0.1);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.3);
  font-size: 24px;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  justify-content: center;
  align-items: center;
  transition: all 0.3s;
}

.fullscreen-viewer .close-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: scale(1.1);
}

/* 滚动条样式 */
.scroll-container::-webkit-scrollbar {
  width: 4px;
}
.scroll-container::-webkit-scrollbar-track {
  background: transparent;
}
.scroll-container::-webkit-scrollbar-thumb {
  background-color: rgba(255, 255, 255, 0.2);
  border-radius: 2px;
}
.scroll-container::-webkit-scrollbar-thumb:hover {
  background-color: rgba(255, 255, 255, 0.4);
}
</style>
