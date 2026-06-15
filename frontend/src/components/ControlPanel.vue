<template>
  <div class="control-panel">
    <div class="custom-border-box" style="position:relative;height:100%;margin-bottom:5px;">
      <!-- 检测控制按钮区域 - 使用原版样式 -->
      <div class="unique-button-container" style="margin-bottom: 10px;">
        <button class="unique-button" @click="handleStartDetection">
          ▶ 开始检测
        </button>
        <button class="unique-button" @click="handleStopDetection">
          ■ 停止检测
        </button>
      </div>
    </div>
  </div>
</template>

<script>
/**
 * ControlPanel 组件
 * 负责检测控制和系统操作
 * 
 */
export default {
  name: 'ControlPanel',

  props: {
    /**
     * 当前检测状态
     * @type {boolean}
     * Requirements: 6.4
     */
    isDetecting: {
      type: Boolean,
      required: true,
      default: false
    }
  },

  emits: [
    'start-detection',  // 开始检测事件 
    'stop-detection'    // 停止检测事件
  ],

  methods: {
    /**
     * 处理开始检测按钮点击
     * Requirements: 6.1, 6.2
     */
    handleStartDetection() {
      this.$emit('start-detection');
    },

    /**
     * 处理停止检测按钮点击
     * Requirements: 6.1, 6.3
     */
    handleStopDetection() {
        this.$emit('stop-detection');
    }
  }
};
</script>

<style scoped>
/* 控制面板使用全局样式 */
.control-panel {
  height: 100%;
}

/* 使用全局 main.css 中的 custom-border-box 和 unique-button 样式 */
</style>
