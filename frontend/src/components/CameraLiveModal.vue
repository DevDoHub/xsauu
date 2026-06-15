<!--
  CameraLiveModal.vue
  摄像头实时画面弹窗组件
  
  功能说明：
  - 显示指定设备的实时视频流（WebRTC/WHEP）
  - 支持点击关闭按钮或弹窗外部区域关闭
  - 模态框居中显示，带半透明背景遮罩
  - 点击画面可放大到全屏查看
  
  Requirements: 4.2, 4.3, 4.4
-->

<template>
  <!-- 弹窗遮罩层，v-if 控制显示，点击遮罩关闭 -->
  <div v-if="visible" class="live-modal-overlay" @click.self="handleClose">
    <div class="live-modal-content" :class="{ 'fullscreen': isFullscreen }">
      <!-- 弹窗头部 -->
      <div class="live-modal-header">
        <span class="live-modal-title">摄像头实时画面 - 设备{{ deviceId }}</span>
        <div class="header-actions">
          <button class="fullscreen-btn" @click="toggleFullscreen" :title="isFullscreen ? '退出全屏' : '全屏查看'">
            {{ isFullscreen ? '⊙' : '⛶' }}
          </button>
          <button class="live-modal-close-btn" @click="handleClose">×</button>
        </div>
      </div>
      
      <!-- 弹窗主体：WebRTC 视频流显示 -->
      <div class="live-modal-body" @click="toggleFullscreen">
        <WhepVideoCell
          v-if="mediamtxPath"
          :path="mediamtxPath"
          :base-url="webrtcBaseUrl"
          :rotation="deviceRotation"
          :auto-play="true"
          class="live-webrtc-cell"
          @state-change="handleVideoStateChange"
        />
        <!-- 无视频路径提示 -->
        <div v-else class="video-error">
          <span class="error-icon">⚠️</span>
          <span class="error-text">未找到设备视频路径</span>
        </div>
        <!-- 视频连接失败提示 -->
        <div v-if="videoState === 'error'" class="video-error">
          <span class="error-icon">⚠️</span>
          <span class="error-text">视频连接失败</span>
        </div>
        <!-- 点击提示 -->
        <div v-if="!isFullscreen && videoState === 'playing'" class="click-hint">点击画面放大</div>
      </div>
    </div>
  </div>
</template>

<script>
import WhepVideoCell from './WhepVideoCell.vue';
import { getMediamtxBaseUrl } from '@/utils/mediamtx';

export default {
  name: 'CameraLiveModal',

  components: {
    WhepVideoCell,
  },

  props: {
    // 控制弹窗显示/隐藏
    visible: {
      type: Boolean,
      default: false
    },
    // 设备编号，用于显示标题
    deviceId: {
      type: [Number, String],
      default: null
    },
    // 设备信息对象
    deviceInfo: {
      type: Object,
      default: null
    }
  },

  emits: ['close'],

  data() {
    return {
      isFullscreen: false,
      videoState: 'idle',
    };
  },

  computed: {
    /**
     * WebRTC WHEP 基地址
     */
    webrtcBaseUrl() {
      return getMediamtxBaseUrl();
    },

    /**
     * 获取 mediamtx 路径名，用于 WebRTC 播放
     */
    mediamtxPath() {
      if (this.deviceInfo?.mediamtx_path) {
        return this.deviceInfo.mediamtx_path;
      }
      if (this.deviceInfo?.device_id) {
        return this.deviceInfo.device_id;
      }
      if (this.deviceId) {
        return String(this.deviceId);
      }
      return '';
    },

    /**
     * 摄像头旋转角度
     */
    deviceRotation() {
      return this.deviceInfo?.camera_rotation || 0;
    },
  },

  watch: {
    // 当弹窗打开时，重置状态
    visible(newVal) {
      if (newVal) {
        this.videoState = 'idle';
        this.isFullscreen = false;
      }
    }
  },

  methods: {
    /**
     * 关闭弹窗
     * 发出 close 事件通知父组件
     */
    handleClose() {
      this.$emit('close');
    },

    /**
     * 处理视频播放状态变化
     */
    handleVideoStateChange({ state }) {
      this.videoState = state;
    },

    /**
     * 切换全屏模式
     */
    toggleFullscreen() {
      this.isFullscreen = !this.isFullscreen;
    }
  }
};
</script>

<style scoped>
/* 弹窗遮罩层 - 半透明背景 */
.live-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 1920px;
  height: 1080px;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2000;
}

/* 弹窗内容容器 - 居中显示 */
.live-modal-content {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border-radius: 12px;
  width: 70vw;
  max-width: 900px;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(79, 195, 247, 0.3);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
  transition: all 0.3s ease;
}

/* 全屏模式 */
.live-modal-content.fullscreen {
  width: 98vw;
  max-width: none;
  height: 98vh;
  max-height: none;
  border-radius: 8px;
}

/* 弹窗头部 */
.live-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  background: rgba(0, 0, 0, 0.3);
  border-bottom: 1px solid rgba(79, 195, 247, 0.2);
}

.live-modal-title {
  color: #72cfff;
  font-size: 16px;
  font-weight: bold;
}

.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

/* 全屏按钮 */
.fullscreen-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: rgba(79, 195, 247, 0.2);
  color: #72cfff;
  font-size: 18px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  justify-content: center;
  align-items: center;
  transition: all 0.3s ease;
}

.fullscreen-btn:hover {
  background: rgba(79, 195, 247, 0.4);
  transform: scale(1.1);
}

/* 关闭按钮 */
.live-modal-close-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  font-size: 20px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  justify-content: center;
  align-items: center;
  transition: all 0.3s ease;
}

.live-modal-close-btn:hover {
  background: rgba(255, 82, 82, 0.6);
  transform: scale(1.1);
}

/* 弹窗主体 */
.live-modal-body {
  display: flex;
  justify-content: center;
  align-items: center;
  background: #000;
  min-height: 400px;
  flex: 1;
  position: relative;
  padding: 10px;
  cursor: pointer;
}

.live-modal-content.fullscreen .live-modal-body {
  min-height: unset;
}

/* WebRTC 视频单元格 */
.live-webrtc-cell {
  width: 100%;
  height: 100%;
}

.live-modal-content.fullscreen .live-webrtc-cell {
  max-height: 90vh;
}

/* 点击提示 */
.click-hint {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.6);
  color: rgba(255, 255, 255, 0.7);
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 12px;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.live-modal-body:hover .click-hint {
  opacity: 1;
}

/* 视频加载失败提示 */
.video-error {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.error-icon {
  font-size: 48px;
}

.error-text {
  color: #ff5252;
  font-size: 16px;
  font-weight: 500;
}
</style>
