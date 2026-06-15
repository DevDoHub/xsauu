<template>
  <div class="whep-video-cell" :class="{ 'is-alarming': alarming }" @click="$emit('click', path)">
    <video 
      ref="videoRef" 
      autoplay 
      muted 
      playsinline
      :style="videoTransformStyle"
    ></video>
    
    <!-- 检测框叠加层（边缘端已做坐标旋转，canvas 不需要 transform） -->
    <canvas 
      v-if="showDetections"
      ref="canvasRef" 
      class="detection-overlay"
    ></canvas>
    
    <!-- 状态指示器 -->
    <div class="status-badge" :class="stateClass"></div>
    
    <!-- 左上角标签 -->
    <div class="label">{{ label || path }}</div>
    
    <!-- 信号中断遮罩（非 playing 且非 idle 时显示） -->
    <div v-if="state !== 'playing' && state !== 'idle'" class="signal-lost-overlay">
      <div class="signal-lost-content">
        <span v-if="state === 'connecting'">连接中...</span>
        <span v-else-if="state === 'retrying'">信号中断，重连中...</span>
        <span v-else-if="state === 'error'" class="error">连接失败</span>
        <span v-else-if="state === 'stopped'">已停止</span>
        <span v-else>{{ state }}</span>
      </div>
    </div>
    
    <!-- 环境数据信息栏 -->
    <div v-if="gasInfo" class="gas-info-bar">
      <span class="gas-item">氧气：{{ gasInfo.o2 }}%</span>
      <span class="gas-item">温度：{{ gasInfo.temp }}°C</span>
      <span class="gas-item">湿度：{{ gasInfo.rh }}%</span>
    </div>
    
    <!-- 底部状态栏 -->
    <div class="state-bar">
      <span v-if="state === 'connecting'" class="connecting">● 连接中</span>
      <span v-else-if="state === 'retrying'" class="retrying">● 重连中</span>
      <span v-else-if="state === 'error'" class="error">● 连接失败</span>
      <span v-else-if="state === 'playing'" class="playing">● 直播</span>
      <span v-else>{{ state }}</span>
    </div>
    
    <!-- 报警闪烁边框 -->
    <div v-if="alarming" class="alarm-border"></div>
  </div>
</template>

<script>
import { ref, onMounted, onBeforeUnmount, watch, computed, nextTick } from 'vue';
import { WhepPlayer } from '@/utils/whep_player';

export default {
  name: 'WhepVideoCell',
  
  props: {
    /**
     * mediamtx 路径名（如 cam1, cam-238）
     */
    path: {
      type: String,
      required: true
    },
    
    /**
     * 显示标签（可选，默认使用 path）
     */
    label: {
      type: String,
      default: ''
    },
    
    /**
     * mediamtx WebRTC 基地址（如 http://localhost:8889）
     */
    baseUrl: {
      type: String,
      required: true
    },
    
    /**
     * 是否处于报警状态
     */
    alarming: {
      type: Boolean,
      default: false
    },
    
    /**
     * 摄像头旋转角度（0=正常, 180=倒装）
     */
    rotation: {
      type: Number,
      default: 0
    },
    
    /**
     * 是否自动播放
     */
    autoPlay: {
      type: Boolean,
      default: true
    },
    
    /**
     * 检测框数据
     * 格式: { boxes: [{ x, y, w, h, label, conf }] }
     */
    detections: {
      type: Object,
      default: null
    },
    
    /**
     * 是否显示检测框
     */
    showDetections: {
      type: Boolean,
      default: false
    },
    
    /**
     * 环境数据 { o2, temp, rh }
     */
    gasInfo: {
      type: Object,
      default: null
    }
  },
  
  emits: ['click', 'state-change'],
  
  setup(props, { emit }) {
    const videoRef = ref(null);
    const canvasRef = ref(null);
    const state = ref('idle');
    let player = null;
    let animationFrame = null;
    
    const stateClass = computed(() => ({
      'badge-playing': state.value === 'playing',
      'badge-connecting': state.value === 'connecting' || state.value === 'retrying',
      'badge-error': state.value === 'error',
      'badge-idle': state.value === 'idle' || state.value === 'stopped'
    }));
    
    const whepUrl = computed(() => {
      const base = props.baseUrl.replace(/\/$/, '');
      return `${base}/${props.path}/whep`;
    });
    
    /**
     * 视频/检测框旋转样式
     */
    const videoTransformStyle = computed(() => {
      if (props.rotation) {
        return { transform: `rotate(${props.rotation}deg)` };
      }
      return {};
    });
    
    function initPlayer() {
      if (!videoRef.value) return;
      
      // 清理旧播放器
      if (player) {
        player.stop();
        player = null;
      }
      
      player = new WhepPlayer({
        videoEl: videoRef.value,
        whepUrl: whepUrl.value,
        onState: (s, detail) => {
          state.value = s;
          emit('state-change', { path: props.path, state: s, detail });
          
          // 流断开时清除检测框叠加层
          if (s !== 'playing') {
            clearDetectionCanvas();
          }
        }
      });
      
      if (props.autoPlay) {
        player.start();
      }
    }
    
    /**
     * 清除检测框 canvas 叠加层
     */
    function clearDetectionCanvas() {
      if (animationFrame) {
        cancelAnimationFrame(animationFrame);
        animationFrame = null;
      }
      const canvas = canvasRef.value;
      if (canvas) {
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
      }
    }
    
    /**
     * 根据标签返回颜色
     */
    function colorForLabel(label) {
      if (!label) return '#00ff00';
      const l = label.toLowerCase();
      if (l.includes('no_helmet') || l.includes('fire') || l.includes('smoke') || l.includes('wh')) {
        return '#ff0000'; // 红色 - 危险
      }
      if (l.includes('no_uniform') || l.includes('no_clothes')) {
        return '#ffaa00'; // 橙色 - 警告
      }
      return '#00ff00'; // 默认绿色
    }

    /**
     * 绘制检测框
     */
    function drawDetections() {
      const canvas = canvasRef.value;
      const video = videoRef.value;
      
      // 非 playing 状态时停止绘制循环
      if (state.value !== 'playing') {
        clearDetectionCanvas();
        return;
      }
      
      if (!canvas || !video || !props.detections) {
        animationFrame = requestAnimationFrame(drawDetections);
        return;
      }
      
      const ctx = canvas.getContext('2d');
      
      // canvas 内部分辨率对齐视频原始帧，保证坐标空间一致
      // 浏览器 CSS 会自动把 canvas 元素缩放到格子显示尺寸，视觉上完全对齐
      const nativeW = video.videoWidth || 640;
      const nativeH = video.videoHeight || 360;
      
      if (canvas.width !== nativeW || canvas.height !== nativeH) {
        canvas.width = nativeW;
        canvas.height = nativeH;
      }
      
      // 清除之前的绘制
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      // 绘制检测框
      const boxes = props.detections.boxes || [];
      const frameW = props.detections.frame_w || canvas.width;
      const frameH = props.detections.frame_h || canvas.height;
      const scaleX = canvas.width / frameW;
      const scaleY = canvas.height / frameH;

      boxes.forEach(box => {
        // 兼容两种格式:
        // 边缘端: { x1, y1, x2, y2, color, label }  label="WH:0.96"
        // 标准:   { x, y, w, h, label, conf }
        let x, y, w, h, labelText, color;

        if ('x1' in box) {
          // 边缘端格式: x1/y1/x2/y2 是像素坐标，需要缩放到 canvas 尺寸
          x = box.x1 * scaleX;
          y = box.y1 * scaleY;
          w = (box.x2 - box.x1) * scaleX;
          h = (box.y2 - box.y1) * scaleY;

          // label 格式: "WH:0.96" → 分离标签和置信度
          const parts = (box.label || '').split(':');
          const name = parts[0] || box.label;
          const conf = parts[1] ? parseFloat(parts[1]) : null;
          labelText = conf !== null ? `${name} ${(conf * 100).toFixed(0)}%` : name;

          // 使用边缘端提供的颜色，或根据标签判断
          if (box.color && box.color.length >= 3) {
            color = `rgb(${box.color[0]}, ${box.color[1]}, ${box.color[2]})`;
          } else {
            color = colorForLabel(name);
          }
        } else {
          // 标准格式
          x = box.x || 0;
          y = box.y || 0;
          w = box.w || 0;
          h = box.h || 0;
          labelText = `${box.label || ''} ${box.conf != null ? (box.conf * 100).toFixed(0) + '%' : ''}`;
          color = colorForLabel(box.label);
        }

        // 绘制边框
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, w, h);

        // 绘制标签背景
        ctx.font = '12px Arial';
        const textWidth = ctx.measureText(labelText).width;
        ctx.fillStyle = color;
        ctx.fillRect(x, y - 16, textWidth + 8, 16);

        // 绘制标签文字
        ctx.fillStyle = '#ffffff';
        ctx.fillText(labelText, x + 4, y - 4);
      });
      
      animationFrame = requestAnimationFrame(drawDetections);
    }
    
    onMounted(() => {
      initPlayer();
      // 检测框绘制由 state watcher 控制，playing 时自动启动
    });
    
    onBeforeUnmount(() => {
      if (player) {
        player.stop();
        player = null;
      }
      if (animationFrame) {
        cancelAnimationFrame(animationFrame);
      }
    });
    
    // 监听 path 或 baseUrl 变化重新初始化
    watch([() => props.path, () => props.baseUrl], () => {
      initPlayer();
    });
    
    // 监听 showDetections 变化
    watch(() => props.showDetections, (val) => {
      if (val && state.value === 'playing') {
        drawDetections();
      } else {
        clearDetectionCanvas();
      }
    });
    
    // 监听 state 变化：playing 时恢复检测框绘制，否则清除
    watch(state, (newState) => {
      if (newState === 'playing' && props.showDetections) {
        drawDetections();
      } else if (newState !== 'playing') {
        clearDetectionCanvas();
      }
    });
    
    return {
      videoRef,
      canvasRef,
      state,
      stateClass,
      videoTransformStyle
    };
  }
};
</script>

<style scoped>
.whep-video-cell {
  position: relative;
  background: #000;
  border: 1px solid #30363d;
  border-radius: 8px;
  overflow: hidden;
  width: 100%;
  height: 100%;
  min-height: 0;
  cursor: pointer;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.whep-video-cell:hover {
  border-color: #58a6ff;
}

.whep-video-cell.is-alarming {
  border-color: #f85149;
}

video {
  width: 100%;
  height: 100%;
  object-fit: fill;
  display: block;
  background: #000;
  /* 旋转由 prop 控制，通过 :style 动态绑定 */
}

.detection-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  /* 旋转由 prop 控制，通过 :style 动态绑定 */
}

.status-badge {
  position: absolute;
  right: 8px;
  top: 8px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #6e7681;
  box-shadow: 0 0 6px rgba(0, 0, 0, 0.6);
}

.badge-playing {
  background: #3fb950;
  box-shadow: 0 0 8px rgba(63, 185, 80, 0.6);
}

.badge-connecting {
  background: #d29922;
  animation: pulse 1.5s infinite;
}

.badge-error {
  background: #f85149;
}

.badge-idle {
  background: #6e7681;
}

.label {
  position: absolute;
  left: 8px;
  top: 8px;
  padding: 2px 8px;
  background: rgba(0, 0, 0, 0.7);
  border-radius: 3px;
  font-size: 13px;
  font-weight: 600;
  color: #e6f6ff;
  pointer-events: none;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.8);
}

.gas-info-bar {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 22px;
  padding: 3px 10px;
  background: rgba(0, 0, 0, 0.6);
  font-size: 12px;
  color: #b8d8e8;
  display: flex;
  gap: 12px;
  pointer-events: none;
}

.gas-item {
  white-space: nowrap;
}

.state-bar {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 4px 10px;
  background: rgba(0, 0, 0, 0.6);
  font-size: 12px;
  color: #b8d8e8;
}

.state-bar .error {
  color: #f85149;
}

.state-bar .playing {
  color: #3fb950;
}

.state-bar .connecting {
  color: #d29922;
}

.state-bar .retrying {
  color: #d29922;
  animation: pulse 1.5s infinite;
}

.signal-lost-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.65);
  z-index: 5;
  pointer-events: none;
}

.signal-lost-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #8b949e;
  font-size: 14px;
}

.signal-lost-icon {
  font-size: 32px;
  opacity: 0.7;
}

.signal-lost-content .error {
  color: #f85149;
}

.alarm-border {
  position: absolute;
  inset: 0;
  border: 3px solid #f85149;
  border-radius: 8px;
  animation: alarm-flash 1s infinite;
  pointer-events: none;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@keyframes alarm-flash {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
</style>
