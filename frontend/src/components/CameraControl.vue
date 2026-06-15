<template>
  <div class="camera-control">
    <!-- PTZ 控制按钮网格 -->
    <ul class="control-buttons">
      <!-- 第一行：启动、上、断开 -->
      <li 
        @click="handleControl('reconnect')" 
        class="reconnect"
        title="启动连接"
      >
        启动
      </li>
      <li 
        @mousedown="handlePtzStart('up')" 
        @mouseup="handlePtzStop" 
        @mouseleave="handlePtzStop"
        class="up"
        title="向上"
      >
        上
      </li>
      <li 
        @click="handleControl('disconnect')" 
        class="disconnect"
        title="断开连接"
      >
        断开
      </li>

      <!-- 第二行：左、自动、右 -->
      <li 
        @mousedown="handlePtzStart('left')" 
        @mouseup="handlePtzStop" 
        @mouseleave="handlePtzStop"
        class="mleft"
        title="向左"
      >
        左
      </li>
      <li 
        @click="handleControl('auto')" 
        class="auto"
        title="自动巡航"
      >
        自动
      </li>
      <li 
        @mousedown="handlePtzStart('right')" 
        @mouseup="handlePtzStop" 
        @mouseleave="handlePtzStop"
        class="mright"
        title="向右"
      >
        右
      </li>

      <!-- 第三行：放大、下、缩小 -->
      <li 
        @mousedown="handlePtzStart('zoom_in')" 
        @mouseup="handlePtzStop" 
        @mouseleave="handlePtzStop"
        class="zoom-in"
        title="放大"
      >
        放大
      </li>
      <li 
        @mousedown="handlePtzStart('down')" 
        @mouseup="handlePtzStop" 
        @mouseleave="handlePtzStop"
        class="down"
        title="向下"
      >
        下
      </li>
      <li 
        @mousedown="handlePtzStart('zoom_out')" 
        @mouseup="handlePtzStop" 
        @mouseleave="handlePtzStop"
        class="zoom-out"
        title="缩小"
      >
        缩小
      </li>
    </ul>
  </div>
</template>

<script>
/**
 * CameraControl 组件
 * 负责单个摄像头的 PTZ 控制、缩放控制、连接控制
 * Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
 */
export default {
  name: 'CameraControl',

  props: {
    /**
     * 设备信息对象
     * @type {Object}
     * @property {number} deviceNumber - 设备编号（可以是0）
     * @property {string} deviceName - 设备名称
     * @property {string} ipAddress - IP地址
     * @property {string} port - 端口号
     * @property {string} note - 备注
     * @property {number} status - 连接状态 (2 = 已连接)
     */
    device: {
      type: Object,
      required: true,
      validator: (value) => {
        // 使用严格比较，因为 deviceNumber 可能是 0
        return value !== null && value !== undefined && 
               value.deviceNumber !== undefined && value.deviceNumber !== null;
      }
    }
  },

  emits: [
    'ptz-start',    // PTZ 控制开始 (direction, deviceId)
    'ptz-stop',     // PTZ 控制停止 (deviceId)
    'control'       // 一般控制命令 (action, deviceId)
  ],

  data() {
    return {
      // 当前是否正在进行 PTZ 控制
      isPtzActive: false
    };
  },

  computed: {
    /**
     * 获取设备ID
     */
    deviceId() {
      return this.device?.deviceNumber;
    }
  },

  methods: {
    /**
     * 检查设备ID是否有效（包括0）
     * @returns {boolean}
     */
    hasValidDeviceId() {
      return this.deviceId !== undefined && this.deviceId !== null;
    },

    /**
     * 处理 PTZ 控制开始
     * 当用户按下 PTZ 按钮时触发，发送持续控制命令
     * Requirements: 4.2
     * @param {string} direction - 控制方向 (up/down/left/right/zoom_in/zoom_out)
     */
    handlePtzStart(direction) {
      if (!this.hasValidDeviceId()) {
        console.warn('CameraControl: No device ID available');
        return;
      }
      console.log('CameraControl handlePtzStart:', direction, this.deviceId);
      this.isPtzActive = true;
      this.$emit('ptz-start', direction, this.deviceId);
    },

    /**
     * 处理 PTZ 控制停止
     * 当用户释放 PTZ 按钮时触发，发送停止命令
     * Requirements: 4.3
     */
    handlePtzStop() {
      if (!this.isPtzActive) return;
      if (!this.hasValidDeviceId()) {
        console.warn('CameraControl: No device ID available');
        return;
      }
      console.log('CameraControl handlePtzStop:', this.deviceId);
      this.isPtzActive = false;
      this.$emit('ptz-stop', this.deviceId);
    },

    /**
     * 处理一般控制命令
     * 用于自动巡航、启动连接、断开连接等单次操作
     * Requirements: 4.1, 4.4, 4.5
     * @param {string} action - 控制动作 (auto/reconnect/disconnect)
     */
    handleControl(action) {
      if (!this.hasValidDeviceId()) {
        console.warn('CameraControl: No device ID available');
        return;
      }
      this.$emit('control', action, this.deviceId);
    }
  },

  /**
   * 组件卸载前确保停止任何进行中的 PTZ 控制
   */
  beforeUnmount() {
    if (this.isPtzActive) {
      this.handlePtzStop();
    }
  }
};
</script>

<style scoped>
.camera-control {
  width: 100%;
  display: flex;
  justify-content: center;
}

/* 控制按钮网格布局 */
.control-buttons {
  list-style-type: none;
  padding: 0;
  margin: 10px 0 0;
  display: grid;
  grid-template-columns: repeat(3, 75px);
  grid-template-rows: repeat(3, 50px);
  gap: 5px;
  justify-items: center;
  align-items: center;
  background: rgba(30, 40, 60, 0.6);
  padding: 14px;
  border-radius: 12px;
  border: 1px solid rgba(100, 120, 150, 0.3);
}

/* 按钮基础样式 */
.control-buttons > li {
  cursor: pointer;
  background: linear-gradient(145deg, #4a5568, #3d4654);
  color: #e2e8f0;
  width: 75px;
  height: 50px;
  border-radius: 6px;
  transition: all 0.2s ease;
  text-align: center;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 14px;
  font-weight: 500;
  user-select: none;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.control-buttons > li:hover {
  background: linear-gradient(145deg, #5a6578, #4d5664);
  border-color: rgba(64, 158, 255, 0.4);
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
}

.control-buttons > li:active {
  background: linear-gradient(145deg, #3d4654, #4a5568);
  transform: translateY(0);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

/* 上按钮位置 */
.control-buttons .up {
  grid-column: 2 / 3;
  grid-row: 1 / 2;
}

/* 下按钮位置 */
.control-buttons .down {
  grid-column: 2 / 3;
  grid-row: 3 / 4;
}

/* 左按钮位置 */
.control-buttons .mleft {
  grid-column: 1 / 2;
  grid-row: 2 / 3;
}

/* 右按钮位置 */
.control-buttons .mright {
  grid-column: 3 / 4;
  grid-row: 2 / 3;
}

/* 自动按钮位置和样式 */
.control-buttons .auto {
  grid-column: 2 / 3;
  grid-row: 2 / 3;
  background: linear-gradient(145deg, #2d6a4f, #1b4332);
  border-color: rgba(103, 194, 58, 0.3);
}

.control-buttons .auto:hover {
  background: linear-gradient(145deg, #40916c, #2d6a4f);
  border-color: rgba(103, 194, 58, 0.5);
}

/* 启动按钮位置和样式 */
.control-buttons .reconnect {
  grid-column: 1 / 2;
  grid-row: 1 / 2;
  border-top-left-radius: 10px;
  background: linear-gradient(145deg, #2563eb, #1d4ed8);
  border-color: rgba(64, 158, 255, 0.3);
}

.control-buttons .reconnect:hover {
  background: linear-gradient(145deg, #3b82f6, #2563eb);
  border-color: rgba(64, 158, 255, 0.5);
}

/* 断开按钮位置和样式 */
.control-buttons .disconnect {
  grid-column: 3 / 4;
  grid-row: 1 / 2;
  border-top-right-radius: 10px;
  background: linear-gradient(145deg, #dc2626, #b91c1c);
  border-color: rgba(245, 108, 108, 0.3);
}

.control-buttons .disconnect:hover {
  background: linear-gradient(145deg, #ef4444, #dc2626);
  border-color: rgba(245, 108, 108, 0.5);
}

/* 放大按钮位置和样式 */
.control-buttons .zoom-in {
  grid-column: 1 / 2;
  grid-row: 3 / 4;
  border-bottom-left-radius: 10px;
}

/* 缩小按钮位置和样式 */
.control-buttons .zoom-out {
  grid-column: 3 / 4;
  grid-row: 3 / 4;
  border-bottom-right-radius: 10px;
}
</style>