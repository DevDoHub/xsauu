<!--
  AlarmControlModal.vue
  报警控制弹窗组件
  
  功能说明：
  - 显示选中摄像头的实时画面
  - 显示当前设备的报警状态（报警中/正常）
  - 提供清除报警、设备信息、远程报警、关闭四个按钮
  - 报警状态显示红色闪烁效果
  - 点击远程报警时弹出违规详情输入弹窗
  - 点击设备信息时弹出设备详情弹窗
  - 点击画面可放大查看
-->

<template>
  <!-- 弹窗遮罩层，v-if 控制显示，点击遮罩关闭 -->
  <div v-if="visible" class="alarm-modal-overlay" @click.self="closeModal">
    <div class="alarm-modal-content" :class="{ 'fullscreen': isFullscreen }">
      
      <!-- 第一部分：摄像头画面 -->
      <div class="alarm-modal-video" @click="toggleFullscreen">
        <!-- WebRTC 实时视频流 -->
        <WhepVideoCell
          v-if="selectedPath"
          :path="selectedPath"
          :base-url="webrtcBaseUrl"
          :rotation="currentDeviceRotation"
          :alarming="isAlarming"
          :detections="currentDetections"
          :show-detections="true"
          class="alarm-webrtc-cell"
        />
        <!-- 传统图片流 -->
        <img v-else-if="selectedImage" :src="selectedImage" alt="摄像头画面">
        <!-- 视频叠字：区域 + O2 + 温度 + 湿度 -->
        <div class="video-overlay">
          <span class="overlay-item">{{ videoOverlay.workshop }}</span>
          <span class="overlay-item">氧气：{{ videoOverlay.o2 }}%</span>
          <span class="overlay-item">温度：{{ videoOverlay.temp }}°C</span>
          <span class="overlay-item">湿度：{{ videoOverlay.rh }}%</span>
        </div>
        <!-- 点击提示 -->
        <div v-if="!isFullscreen" class="click-hint">点击画面放大</div>
        <div v-else class="click-hint">点击画面缩小</div>
      </div>
      
      <!-- 第二部分：报警状态显示（全屏时隐藏） -->
      <div class="alarm-modal-status" v-show="!isFullscreen">
        <div class="alarm-status-header">
          <span class="alarm-status-title">报警控制</span>
          <span class="alarm-device-info">设备 {{ selectedDeviceId }}</span>
        </div>
        
        <!-- 报警状态指示器，根据 isAlarming 添加 alarming 类 -->
        <div class="alarm-status-indicator" :class="{ 'alarming': isAlarming }">
          <span class="status-icon">{{ isAlarming ? '⚠️' : '✓' }}</span>
          <span class="status-text">{{ isAlarming ? '报警中' : '正常' }}</span>
        </div>
      </div>
      
      <!-- 第三部分：控制按钮（全屏时隐藏） -->
      <div class="alarm-modal-controls" v-show="!isFullscreen">
        <button 
        class="btn-voice"
        :class="{'talking': isVoiceCalling}"
        @mousedown="startVoiceCall"
        @mouseup="stopVoiceCall"
        >
          <div v-if="isVoiceCalling" class="voice-wave">
            <!-- 限制最大高度为24px，防止溢出 -->
            <span class="bar" :style="{ height: Math.min(10, Math.max(2, volumeLevel * 0.1)) + 'px' }"></span>
            <span class="bar" :style="{ height: Math.min(14, Math.max(3, volumeLevel * 0.2)) + 'px' }"></span>
            <span class="bar" :style="{ height: Math.min(18, Math.max(4, volumeLevel * 0.3)) + 'px' }"></span>
            <span class="bar" :style="{ height: Math.min(22, Math.max(5, volumeLevel * 0.4)) + 'px' }"></span>
            <span class="bar" :style="{ height: Math.min(24, Math.max(6, volumeLevel * 0.5)) + 'px' }"></span>
            <span class="bar" :style="{ height: Math.min(22, Math.max(5, volumeLevel * 0.4)) + 'px' }"></span>
            <span class="bar" :style="{ height: Math.min(18, Math.max(4, volumeLevel * 0.3)) + 'px' }"></span>
            <span class="bar" :style="{ height: Math.min(14, Math.max(3, volumeLevel * 0.2)) + 'px' }"></span>
            <span class="bar" :style="{ height: Math.min(10, Math.max(2, volumeLevel * 0.1)) + 'px' }"></span>
          </div>
          <span v-else>语音通话 (按住)</span>
        </button>
        <button class="btn-clear" @click="handleClearAlarm">清除报警</button>
        <button class="btn-trigger" @click="handleTriggerAlarm">远程报警</button>
        <button class="btn-info" @click="openDeviceInfoModal">设备信息</button>
        <button class="btn-close" @click="closeModal">关闭</button>
      </div>
      
    </div>
    

    
    <!-- 违规类型选择弹窗 -->
    <ViolationInputModal
      :visible="showViolationModal"
      @confirm="handleViolationConfirm"
      @cancel="handleViolationCancel"
    />

    <!-- 设备信息弹窗 -->
    <div v-if="showDeviceInfoModal" class="device-info-overlay" @click.self="closeDeviceInfoModal">
      <div class="device-info-content">
        <!-- 弹窗头部 -->
        <div class="device-info-header">
          <span class="device-info-title">设备信息</span>
          <button class="close-btn" @click="closeDeviceInfoModal">×</button>
        </div>
        
        <!-- 弹窗主体 -->
        <div class="device-info-body">
          <!-- 加载状态 -->
          <div v-if="deviceInfoLoading" class="loading-state">
            <span class="loading-icon">⏳</span>
            <span class="loading-text">加载中...</span>
          </div>
          
          <!-- 错误状态 -->
          <div v-else-if="deviceInfoError" class="error-state">
            <span class="error-icon">⚠️</span>
            <span class="error-text">{{ deviceInfoError }}</span>
          </div>
          
          <!-- 数据显示 -->
          <div v-else-if="deviceInfoData" class="info-sections">
            <!-- 设备基本信息区块 -->
            <div class="info-section">
              <h3 class="section-title">设备基本信息</h3>
              <div class="info-grid">
                <div class="info-item">
                  <span class="label">设备负责人</span>
                  <span class="value">{{ formatValue(deviceInfoData.responsible_person || deviceInfoData.device_manager) }}</span>
                </div>
                <div class="info-item">
                  <span class="label">作业区域</span>
                  <span class="value">{{ formatValue(deviceInfoData.workshop || deviceInfoData.work_location) }}</span>
                </div>
                <div class="info-item">
                  <span class="label">安全许可证号</span>
                  <span class="value">{{ formatValue(deviceInfoData.safety_permit_no) }}</span>
                </div>
                <div class="info-item">
                  <span class="label">作业区域负责人</span>
                  <span class="value">{{ formatValue(deviceInfoData.area_manager) }}</span>
                </div>
                <div class="info-item">
                  <span class="label">作业区域负责人电话</span>
                  <span class="value">{{ formatValue(deviceInfoData.area_manager_phone) }}</span>
                </div>
                <div class="info-item">
                  <span class="label">作业内容</span>
                  <span class="value">{{ formatValue(deviceInfoData.work_content) }}</span>
                </div>
                <div class="info-item">
                  <span class="label">作业级别</span>
                  <span class="value">{{ formatValue(deviceInfoData.work_level) }}</span>
                </div>
                <div class="info-item">
                  <span class="label">作业类型</span>
                  <span class="value">{{ formatValue(deviceInfoData.work_type) }}</span>
                </div>
                <div class="info-item">
                  <span class="label">是否受限空间</span>
                  <span class="value">{{ formatValue(deviceInfoData.confined_space) }}</span>
                </div>
                <div class="info-item">
                  <span class="label">作业开始时间</span>
                  <span class="value">{{ formatDateTime(deviceInfoData.work_start_time) }}</span>
                </div>
                <div class="info-item">
                  <span class="label">作业结束时间</span>
                  <span class="value">{{ formatDateTime(deviceInfoData.work_end_time) }}</span>
                </div>
                <div class="info-item">
                  <span class="label">作业状态</span>
                  <span class="value" :class="getWorkStatusClass(deviceInfoData.work_status)">
                    {{ formatValue(deviceInfoData.work_status) }}
                  </span>
                </div>
              </div>
            </div>
            
            <!-- 工作环境数据信息区块 -->
            <div class="info-section">
              <h3 class="section-title">工作环境数据信息</h3>
              <div class="gas-data-grid">
                <div
                  v-for="gas in gasRegistry"
                  :key="gas.key"
                  :class="['gas-card', gas.has_threshold && isGasOverThreshold(gas.key) ? 'alarm' : 'normal']"
                >
                  <span class="gas-label">{{ gas.category === 'gas' ? gas.key + ' ' + gas.display : gas.display }}</span>
                  <span class="gas-value">{{ getGasValue(gas.key) }}</span>
                  <span class="gas-unit">{{ gas.unit }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>


<script>
import { io } from 'socket.io-client';
import { computed } from 'vue';
import WhepVideoCell from './WhepVideoCell.vue';
import ViolationInputModal from './ViolationInputModal.vue';
import { getMediamtxBaseUrl } from '@/utils/mediamtx';
import { useDetectionStream } from '@/composables/useDetectionStream';

export default {
    name:"AlarmControlModal",
    
    components: {
      WhepVideoCell,
      ViolationInputModal
    },
    
    setup(props) {
      const { detections } = useDetectionStream();
      const currentDetections = computed(() => {
        if (!props.selectedPath) return null;
        return detections.value[props.selectedPath] || null;
      });
      return { currentDetections };
    },

    props:{
        visible:{
            type:Boolean,
            require:true,
            default:false
        },
        selectedImage: {
            type:String,
            default:null
        },
        /** WebRTC mediamtx 路径（如 cam1），有值时显示实时视频流 */
        selectedPath: {
            type:String,
            default:null
        },
        selectedDeviceId:{
            type:[String,Number],
            default:null
        },
        alarmStatus:{
            type:Object,
            default:()=>({})
        },
        // 实时气体数据
        gasData: {
            type: Object,
            default: () => ({})
        },
        // 气体报警阈值
        gasThreshold: {
            type: Object,
            default: () => ({})
        },
        // 区域设备分组数据（用于查找workshop）
        areaDevices: {
            type: Object,
            default: () => ({})
        },
        // 设备旋转角度映射 { device_id: rotation }
        deviceRotationMap: {
            type: Object,
            default: () => ({})
        }
    },
    
    data() {
      return {
        isFullscreen: false,
        // 语音通话相关状态
        isVoiceCalling:false, //是否正在通话
        voiceSocket:null, //socketIO连接状态
        mediaRecorder: null,   // 录音器实例
        mediaStream: null,     // 麦克风流
        // 全局 mouseup 监听器引用（用于跨元素松开按钮也能正确 stop）
        globalMouseUpHandler: null,

        // 音量分析相关
        audioContext: null,
        audioSource: null, // [新增] 保存音频源，防止被垃圾回收
        analyser: null,
        animationFrameId: null,
        volumeLevel: 0, // 0~100 的音量值
        
        // 设备信息弹窗相关状态
        showDeviceInfoModal: false,
        deviceInfoLoading: false,
        deviceInfoError: null,
        deviceInfoData: null,
        // 本地气体数据，从接口处获取
        localGasData: {},
        localGasThreshold:{},
        // 气体注册表（从后端动态获取，驱动卡片渲染）
        gasRegistry: [],
        // 违规输入弹窗
        showViolationModal: false
      };
    },

    computed:{
        webrtcBaseUrl() {
            return getMediamtxBaseUrl();
        },

        isAlarming(){
            // 使用严格比较，避免设备ID为0时被错误判断为falsy
            if (this.selectedDeviceId === null || this.selectedDeviceId === undefined || !this.alarmStatus){
                return false;
            }
            const deviceStatus = this.alarmStatus[String(this.selectedDeviceId)];
            return deviceStatus ? deviceStatus.alarm_active : false;
        },

        /**
         * 弹窗视频叠字数据
         * 从 gasData 中提取当前选中设备的 O2、温度、湿度，从 areaDevices 查找 workshop
         *
         * areaDevices 结构: { 区域负责人: { 设备名: 设备对象 } }
         */
        videoOverlay() {
            const deviceId = String(this.selectedDeviceId ?? '');
            const gasMap = this.gasData || {};
            const data = gasMap[deviceId] || gasMap[String(deviceId)] || {};
            // 从 areaDevices 中查找 workshop
            let workshop = '-';
            const areaDevices = this.areaDevices || {};
            for (const devicesMap of Object.values(areaDevices)) {
                for (const device of Object.values(devicesMap || {})) {
                    if (String(device.device_id || device.deviceNumber) === deviceId) {
                        workshop = device.workshop || '-';
                        break;
                    }
                }
                if (workshop !== '-') break;
            }
            return {
                temp: this.formatOverlayValue(data.TEMP),
                rh: this.formatOverlayValue(data.RH),
                o2: this.formatOverlayValue(data.O2),
                workshop
            };
        },

        /**
         * 当前选中设备的旋转角度
         */
        currentDeviceRotation() {
            const deviceId = String(this.selectedDeviceId ?? '');
            return this.deviceRotationMap?.[deviceId] ?? 0;
        },


    },
    
    watch: {
      // 当弹窗关闭时，重置全屏状态
      visible(newVal) {
        if (!newVal) {
          this.isFullscreen = false;
          this.showDeviceInfoModal = false;
          this.resetDeviceInfoState();

          // 弹窗关闭时，清理语音通话资源（停止通话 + 断开 Socket）
          this.cleanupVoice();
        } else {
          // 弹窗打开时，提前建立 Socket 连接（避免按住按钮时再握手导致延迟）
          this.initVoiceSocket();
        }
      }
    },
    
    methods:{
        /**
         * 格式化叠字显示值，无效值返回 '-'
         */
        formatOverlayValue(value) {
            if (value === null || value === undefined || value === '' || value === '-1') {
                return '-';
            }
            const num = parseFloat(value);
            if (Number.isNaN(num)) return '-';
            return String(Math.trunc(num));
        },

       //初始化语音Socket连接
        initVoiceSocket(){
          if(this.voiceSocket) return;
          
          // 连接到新后端 SocketIO 服务（与 API 同端口）
          // 新后端已集成 SocketIO 兼容层，无需单独端口
          const baseUrl = window.location.origin;
          this.voiceSocket = io(baseUrl,{
            transports:['websocket'], //强制使用websocket传输
            autoConnect:true
          });

          this.voiceSocket.on('connect',()=> {
            console.log('语音服务已连接');
          });

          this.voiceSocket.on('connect_error',(err)=> {
            console.log('语音服务连接失败:',err);
          });
        },
        closeModal(){
            this.$emit('close');
        },
        handleClearAlarm(){
            this.$emit('clear-alarm',this.selectedDeviceId);
        },
        handleTriggerAlarm() {
            this.showViolationModal = true;
        },
        async handleViolationConfirm({ alarmType, alarmTypeLabel, severity, description }) {
            this.showViolationModal = false;
            try {
                // 先截图（在 emit 之前，确保 video 还在 DOM 中）
                const imageData = this.captureSnapshot();
                console.log('[AlarmModal] 截图结果:', imageData ? `成功 (${Math.round(imageData.length/1024)}KB)` : '失败(null)');
                this.$emit('trigger-alarm-with-violation', {
                    deviceId: this.selectedDeviceId,
                    alarmType,
                    alarmTypeLabel,
                    severity,
                    description,
                    image: imageData,
                    note: this.videoOverlay?.workshop || '',
                    type: alarmTypeLabel || '',
                    type2: '手动报警',
                });
            } catch (e) {
                console.error('远程报警失败:', e);
                alert('报警失败，请重试');
            }
        },
        handleViolationCancel() {
            this.showViolationModal = false;
        },
        /**
         * 从 WhepVideoCell 的 video 元素截取当前帧，并叠加检测框
         * @returns {string|null} base64 图片数据，或 null
         */
        captureSnapshot() {
            try {
                // 尝试多种选择器找到 video 元素
                let videoEl = document.querySelector('.alarm-modal-overlay .alarm-webrtc-cell video')
                    || document.querySelector('.alarm-webrtc-cell video')
                    || document.querySelector('.alarm-modal-overlay video');
                if (!videoEl) {
                    console.warn('[截图] 未找到 video 元素');
                    return null;
                }
                if (videoEl.readyState < 1) {
                    console.warn('[截图] video readyState=', videoEl.readyState, '视频数据不足');
                    return null;
                }
                const canvas = document.createElement('canvas');
                canvas.width = videoEl.videoWidth || 640;
                canvas.height = videoEl.videoHeight || 360;
                const ctx = canvas.getContext('2d');
                // 1. 画视频帧
                // 如果设备需要旋转180度，先将 canvas 坐标系旋转180度
                // 这样截图本身就是正向的，检测框坐标也直接匹配
                const rotation = this.currentDeviceRotation || 0;
                if (rotation === 180) {
                    ctx.translate(canvas.width, canvas.height);
                    ctx.rotate(Math.PI);
                }
                ctx.drawImage(videoEl, 0, 0, canvas.width, canvas.height);
                // 旋转180度后恢复坐标系，确保检测框按正常坐标绘制
                if (rotation === 180) {
                    ctx.setTransform(1, 0, 0, 1, 0, 0);
                }
                // 2. 在截图上画检测框
                this._drawDetectionsOnCanvas(ctx, canvas.width, canvas.height);
                const dataUrl = canvas.toDataURL('image/jpeg', 0.8);
                console.log('[截图] 成功（含检测框）, videoSize:', videoEl.videoWidth, 'x', videoEl.videoHeight, ', rotation:', rotation);
                return dataUrl;
            } catch (e) {
                console.warn('[截图] 失败:', e);
                return null;
            }
        },

        /**
         * 在指定 canvas context 上绘制检测框（复用 WhepVideoCell 的坐标逻辑）
         */
        _drawDetectionsOnCanvas(ctx, canvasW, canvasH) {
            const dets = this.currentDetections;
            if (!dets || !dets.boxes || dets.boxes.length === 0) return;
            const boxes = dets.boxes;
            const frameW = dets.frame_w || canvasW;
            const frameH = dets.frame_h || canvasH;
            const scaleX = canvasW / frameW;
            const scaleY = canvasH / frameH;

            const COLORS = [
                [255, 77, 77], [255, 184, 77], [77, 184, 255],
                [126, 231, 126], [231, 126, 255], [255, 231, 77],
            ];
            function colorForLabel(label) {
                let hash = 0;
                for (let i = 0; i < (label || '').length; i++) hash = ((hash << 5) - hash + label.charCodeAt(i)) | 0;
                const c = COLORS[Math.abs(hash) % COLORS.length];
                return `rgb(${c[0]},${c[1]},${c[2]})`;
            }

            boxes.forEach(box => {
                let x, y, w, h, labelText, color;
                if ('x1' in box) {
                    x = box.x1 * scaleX;
                    y = box.y1 * scaleY;
                    w = (box.x2 - box.x1) * scaleX;
                    h = (box.y2 - box.y1) * scaleY;
                    const parts = (box.label || '').split(':');
                    const name = parts[0] || box.label;
                    const conf = parts[1] ? parseFloat(parts[1]) : null;
                    labelText = conf !== null ? `${name} ${(conf * 100).toFixed(0)}%` : name;
                    if (box.color && box.color.length >= 3) {
                        color = `rgb(${box.color[0]}, ${box.color[1]}, ${box.color[2]})`;
                    } else {
                        color = colorForLabel(name);
                    }
                } else {
                    x = box.x || 0;
                    y = box.y || 0;
                    w = box.w || 0;
                    h = box.h || 0;
                    labelText = `${box.label || ''} ${box.conf != null ? (box.conf * 100).toFixed(0) + '%' : ''}`;
                    color = colorForLabel(box.label);
                }
                ctx.strokeStyle = color;
                ctx.lineWidth = Math.max(2, Math.round(canvasW / 300));
                ctx.strokeRect(x, y, w, h);
                // 标签背景
                ctx.font = `bold ${Math.max(12, Math.round(canvasW / 50))}px sans-serif`;
                const textW = ctx.measureText(labelText).width;
                const textH = Math.max(14, Math.round(canvasW / 45));
                ctx.fillStyle = color;
                ctx.fillRect(x, y - textH - 2, textW + 6, textH + 2);
                ctx.fillStyle = '#fff';
                ctx.fillText(labelText, x + 3, y - 4);
            });
        },
        toggleFullscreen() {
            this.isFullscreen = !this.isFullscreen;
        },
        
        // ========== 设备信息弹窗相关方法 ==========
        
        /**
         * 打开设备信息弹窗
         * Requirements: 1.3
         */
        openDeviceInfoModal() {
            this.showDeviceInfoModal = true;
            this.fetchDeviceInfo();
            this.fetchGasData();
            this.fetchGasThreshold();
            this.fetchGasRegistry();
        },
        
        /**
         * 关闭设备信息弹窗
         * Requirements: 2.3, 2.4
         */
        closeDeviceInfoModal() {
            this.showDeviceInfoModal = false;
            this.resetDeviceInfoState();
        },
        
        /**
         * 重置设备信息状态
         */
        resetDeviceInfoState() {
            this.deviceInfoLoading = false;
            this.deviceInfoError = null;
            this.deviceInfoData = null;
        },

        /**
         * 启动音频分析
         */
        startAudioAnalysis(stream) {
            if (!this.audioContext) {
                this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            }
            
            // 确保 AudioContext 处于运行状态
            if (this.audioContext.state === 'suspended') {
                this.audioContext.resume();
            }
            
            // 创建源和分析器
            this.audioSource = this.audioContext.createMediaStreamSource(stream);
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 256; // 采样窗口大小
            
            this.audioSource.connect(this.analyser);
            
            const bufferLength = this.analyser.frequencyBinCount;
            const dataArray = new Uint8Array(bufferLength);
            
            const updateVolume = () => {
                if (!this.isVoiceCalling) return;
                
                this.analyser.getByteFrequencyData(dataArray);
                
                // 计算平均音量
                let sum = 0;
                const count = Math.min(bufferLength, 20); 
                for(let i = 0; i < count; i++) {
                    sum += dataArray[i];
                }
                
                this.volumeLevel = sum / count; 
                
                // 循环调用下一帧
                this.animationFrameId = requestAnimationFrame(updateVolume);
            };
            
            updateVolume();
        },

        /**
         * 开始语音通话（按下按钮）
         */
        async startVoiceCall(){
          if (this.isVoiceCalling) return;

          // [关键修复] 在用户点击的瞬间，立即创建/恢复 AudioContext
          // 必须在 await 之前执行，否则会被浏览器判定为非用户交互
          if (!this.audioContext) {
              this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
          }
          if (this.audioContext.state === 'suspended') {
              await this.audioContext.resume();
          }

          try {
            // 确保 Socket 连接可用（弹窗打开时已提前建立，这里做兜底）
            if(!this.voiceSocket) this.initVoiceSocket();
            if (!this.voiceSocket.connected) {
              console.warn('[语音] Socket 未连接，等待连接就绪...');
              await new Promise((resolve, reject) => {
                const timeout = setTimeout(() => reject(new Error('语音服务连接超时')), 3000);
                this.voiceSocket.once('connect', () => { clearTimeout(timeout); resolve(); });
              });
            }

            //获取浏览器麦克风权限
            this.mediaStream = await navigator.mediaDevices.getUserMedia({audio:true});
            
            // 必须先设置状态为true，否则 audioAnalysis 里的循环会直接退出
            this.isVoiceCalling = true;
            this.startAudioAnalysis(this.mediaStream);

          const options = {mimeType:'audio/webm;codecs=opus'};
          this.mediaRecorder = new MediaRecorder(this.mediaStream,options);

          // 监听数据切片事件
          this.mediaRecorder.ondataavailable = async (event)=>{
            if(event.data.size>0 && this.voiceSocket && this.voiceSocket.connected){
              // 将 Blob 转为 ArrayBuffer 再发送
              // Socket.IO 传输二进制时要求 ArrayBuffer/Uint8Array，不能直接传 Blob
              try {
                const arrayBuffer = await event.data.arrayBuffer();
                this.voiceSocket.emit('voice_data',{
                  device_id:this.selectedDeviceId,
                  audio_chunk:arrayBuffer
                });
              } catch (e) {
                console.error('[语音] 音频数据发送失败:', e);
              }
            }
          }
          // 开始录制，每250ms切割一个数据包发送
          this.voiceSocket.emit('voice_start', {
            device_id: this.selectedDeviceId
          });
          
          this.mediaRecorder.start(250);
          console.log('正在语音通话...', 'device_id:', this.selectedDeviceId);

          // 注册全局 mouseup / pointercancel / blur 兜底
          // 防止：鼠标移出按钮再松开、拖到窗外松开、按住期间窗口失焦等情况
          // 不再依赖按钮自身的 mouseleave（按钮内容变化会误触发 leave 导致瞬间 stop）
          if (!this.globalMouseUpHandler) {
            this.globalMouseUpHandler = () => this.stopVoiceCall();
            document.addEventListener('mouseup', this.globalMouseUpHandler);
            document.addEventListener('pointercancel', this.globalMouseUpHandler);
            window.addEventListener('blur', this.globalMouseUpHandler);
          }
          }catch (err){
            console.error('无法启动语音通话',err);
            alert('无法访问麦克风，请检查权限设置');
            this.stopVoiceCall();
          }
        },
        /**
         * 停止语音通话
         */
        stopVoiceCall() {
            if (!this.isVoiceCalling) return;
            // 0. 卸载全局监听（必须放在最前，避免重复触发 stopVoiceCall）
            if (this.globalMouseUpHandler) {
                document.removeEventListener('mouseup', this.globalMouseUpHandler);
                document.removeEventListener('pointercancel', this.globalMouseUpHandler);
                window.removeEventListener('blur', this.globalMouseUpHandler);
                this.globalMouseUpHandler = null;
            }
            // 1. 发送停止信号
            if (this.voiceSocket && this.voiceSocket.connected) {
                this.voiceSocket.emit('voice_stop', {
                    device_id: this.selectedDeviceId
                });
            }
            // 2. 停止录音
            if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
                this.mediaRecorder.stop();
            }
            // 3. 关闭麦克风流（释放硬件占用）
            if (this.mediaStream) {
                this.mediaStream.getTracks().forEach(track => track.stop());
                this.mediaStream = null;
            }
            // 4. 停止音频分析
            if (this.animationFrameId) {
                cancelAnimationFrame(this.animationFrameId);
                this.animationFrameId = null;
            }
            if (this.audioContext && this.audioContext.state !== 'closed') {
                // [新增] 断开源连接
                if (this.audioSource) {
                    this.audioSource.disconnect();
                    this.audioSource = null;
                }
                this.audioContext.close(); // 释放资源
                this.audioContext = null;
            }
            this.isVoiceCalling = false;
            this.mediaRecorder = null;
            console.log('语音通话已停止');
        },
        // 清理资源
        cleanupVoice() {
            this.stopVoiceCall();
            if (this.voiceSocket) {
                this.voiceSocket.disconnect();
                this.voiceSocket = null;
            }
        },
        /**
         * 获取设备信息
         * 调用后端API获取指定设备的完整信息
         */
        async fetchDeviceInfo() {
            this.deviceInfoLoading = true;
            this.deviceInfoError = null;
            this.deviceInfoData = null;
            
            try {
                const response = await fetch(`/api/devices/by-id/${this.selectedDeviceId}`);
                
                if (!response.ok) {
                    if (response.status === 404) {
                        throw new Error('设备不存在');
                    }
                    throw new Error('获取设备信息失败');
                }
                
                const result = await response.json();
                
                // 兼容两种格式：{status,data} 或直接返回数据对象
                if (result.status === 'success' && result.data) {
                    this.deviceInfoData = result.data;
                } else if (result.id || result.device_id) {
                    this.deviceInfoData = result;
                } else {
                    throw new Error(result.message || '获取设备信息失败');
                }
            } catch (err) {
                this.deviceInfoError = err.message || '获取设备信息失败，请重试';
            } finally {
                this.deviceInfoLoading = false;
            }
        },

      /*
      * 获取实时气体数据
      * */
      async fetchGasData() {
        try {
          const response = await fetch(`/api/detections/gas/latest`);
          if (response.ok) {
            const data = await response.json();
            this.localGasData = data;
          }
        } catch (err){
          console.error('获取气体数据失败：', err);
        }
      },
      /**
       * 获取气体阈值数据
       */
      async fetchGasThreshold() {
        try {
            const response = await fetch(`/api/detections/gas/threshold`);
          if (response.ok) {
            const data = await response.json();
            this.localGasThreshold = data;
          }
        } catch (err) {
          console.error('获取气体阈值失败:', err);
        }
      },

        /**
         * 格式化字段值
         * 当字段值为空、null或undefined时返回"--"
         * @param {any} value - 字段值
         * @returns {string} 格式化后的值
         */
        formatValue(value) {
            if (value === null || value === undefined || value === '') {
                return '--';
            }
            return value;
        },
        
        /**
         * 格式化时间戳
         * 将Unix时间戳转换为可读的日期时间格式
         * @param {number} timestamp - Unix时间戳
         * @returns {string} 格式化后的日期时间
         */
        formatTimestamp(timestamp) {
            if (!timestamp) {
                return '--';
            }
            try {
                const date = new Date(timestamp * 1000);
                const year = date.getFullYear();
                const month = String(date.getMonth() + 1).padStart(2, '0');
                const day = String(date.getDate()).padStart(2, '0');
                const hours = String(date.getHours()).padStart(2, '0');
                const minutes = String(date.getMinutes()).padStart(2, '0');
                const seconds = String(date.getSeconds()).padStart(2, '0');
                return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
            } catch (e) {
                return '--';
            }
        },
        
        /**
         * 获取作业状态的CSS类名
         * @param {string} status - 作业状态
         * @returns {string} CSS类名
         */
        getWorkStatusClass(status) {
            if (!status) return '';
            if (status === '进行中') return 'status-active';
            if (status === '已完成') return 'status-completed';
            return '';
        },
        
        /**
         * 格式化日期时间字符串
         * 将ISO格式(2026-01-12T20:00:47)转换为标准格式(2026-01-12 20:00:47)
         * @param {string} dateTimeStr - 日期时间字符串
         * @returns {string} 格式化后的日期时间
         */
        formatDateTime(dateTimeStr) {
            if (!dateTimeStr || dateTimeStr === '') {
                return '--';
            }
            // 将T替换为空格
            return dateTimeStr.replace('T', ' ');
        },
        
        /**
         * 获取气体数据值
         * @param {string} gasType - 气体类型 (C3H8/C2H2/CO2/TEMP/RH)
         * @returns {string} 气体数据值
         */
        getGasValue(gasType) {
          const deviceId = this.selectedDeviceId;
          // 优先使用本地获取的数据，其次使用props传入的数据
          const deviceGasData = this.localGasData[deviceId]
              || this.localGasData[String(deviceId)]
              || this.gasData[deviceId]
              || this.gasData[String(deviceId)];

          if (!deviceGasData) {
            return '--';
          }
          let value = deviceGasData[gasType];
          if (value === undefined || value === null || value === '') {
            return '--';
          }
          // 去除数据中可能包含的单位符号
          if (typeof value === 'string') {
            value = value.replace(/[℃°C%ppm]/g, '').trim();
          }
          return value;
        },

        
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

        /**
         * 判断气体是否超过阈值
         * @param {string} gasType - 气体类型
         * @returns {boolean} 是否超阈值
         */
        isGasOverThreshold(gasType) {
          const deviceId = this.selectedDeviceId;
          // 优先使用本地数据
          const deviceGasData = this.localGasData[deviceId]
              || this.localGasData[String(deviceId)]
              || this.gasData[deviceId]
              || this.gasData[String(deviceId)];
          const deviceThreshold = this.localGasThreshold[deviceId]
              || this.localGasThreshold[String(deviceId)]
              || this.gasThreshold[deviceId]
              || this.gasThreshold[String(deviceId)];

          if (!deviceGasData || !deviceThreshold) {
            return false;
          }
          const value = parseFloat(deviceGasData[gasType]);
          const threshold = parseFloat(deviceThreshold[gasType]);

          if (isNaN(value) || isNaN(threshold) || threshold === 0) {
            return false;
          }

          return value > threshold;
        }
    }
};
</script>


<style scoped>
.alarm-modal-overlay {
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

.alarm-modal-content {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border-radius: 12px;
  width: 90vw;
  max-width: 800px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(79, 195, 247, 0.3);
  transition: all 0.3s ease;
}

/* 全屏模式 */
.alarm-modal-content.fullscreen {
  width: 98vw;
  max-width: none;
  height: 98vh;
  max-height: none;
  border-radius: 8px;
}

.alarm-modal-video {
  display: flex;
  justify-content: center;
  align-items: stretch;          /* 让子元素纵向撑满 */
  background: #000;
  cursor: pointer;
  position: relative;
  flex: 1 1 auto;
  width: 100%;
  height: 50vh;                  /* 固定高度，确保有足够空间显示视频 */
  min-height: 360px;
  overflow: hidden;
  box-sizing: border-box;
}

.alarm-modal-video img {
  width: 100%;
  height: 100%;
  object-fit: contain;           /* 保持比例完整显示，不裁剪 */
  /* 旋转由 prop 控制，通过 :style 动态绑定 */
}

/* WebRTC 实时视频流样式 */
.alarm-modal-video .alarm-webrtc-cell {
  width: 100%;
  height: 100%;                  /* 撑满父级 .alarm-modal-video */
  max-height: none;
  border: none;
  border-radius: 0;
  aspect-ratio: auto;
  display: block;
}

.alarm-modal-content.fullscreen .alarm-modal-video {
  height: auto;                  /* 全屏由 flex:1 自动撑满剩余高度 */
  max-height: none;
  flex: 1 1 auto;
}

.alarm-modal-content.fullscreen .alarm-modal-video .alarm-webrtc-cell {
  width: 100%;
  height: 100%;
  max-height: none;
}

.alarm-modal-content.fullscreen .alarm-modal-video img {
  width: 100%;
  height: 100%;
  object-fit: contain;           /* 保持比例完整显示 */
  /* 旋转由 prop 控制，通过 :style 动态绑定 */
}

/* 视频叠字（左下角），与 VideoGrid.vue 完全一致 */
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

/* 点击提示 */
.click-hint {
  position: absolute;
  bottom: 15px;
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

.alarm-modal-video:hover .click-hint {
  opacity: 1;
}

.alarm-modal-status {
  padding: 15px 20px;
  background: rgba(0, 0, 0, 0.3);
}

.alarm-status-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
}

.alarm-status-title {
  color: #72cfff;
  font-size: 16px;
  font-weight: bold;
}

.alarm-device-info {
  color: #ffb74d;
  font-size: 14px;
}

.alarm-status-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 15px;
  background: rgba(129, 199, 132, 0.15);
  border-radius: 8px;
  border: 2px solid rgba(129, 199, 132, 0.4);
}

.alarm-status-indicator .status-icon {
  font-size: 24px;
  margin-right: 10px;
}

.alarm-status-indicator .status-text {
  font-size: 18px;
  font-weight: bold;
  color: #81c784;
}

.alarm-status-indicator.alarming {
  background: rgba(255, 82, 82, 0.2);
  border-color: rgba(255, 82, 82, 0.6);
  animation: alarm-blink 1s infinite;
}

.alarm-status-indicator.alarming .status-text {
  color: #ff5252;
}

@keyframes alarm-blink {
  0%, 100% { box-shadow: 0 0 10px rgba(255, 82, 82, 0.3); }
  50% { box-shadow: 0 0 25px rgba(255, 82, 82, 0.7); }
}

.alarm-modal-controls {
  display: flex;
}

.alarm-modal-controls button {
  flex: 1;
  padding: 12px;
  border: none;
  font-size: 14px;
  font-weight: bold;
  cursor: pointer;
}

/* 半透明按钮样式 */
.btn-clear { 
  background: rgba(76, 175, 80, 0.25); 
  color: #81c784;
  border: 1px solid rgba(76, 175, 80, 0.4);
  transition: all 0.2s ease;
}
.btn-trigger { 
  background: rgba(244, 67, 54, 0.25); 
  color: #ef5350;
  border: 1px solid rgba(244, 67, 54, 0.4);
  transition: all 0.2s ease;
}
.btn-info { 
  background: rgba(33, 150, 243, 0.25); 
  color: #64b5f6;
  border: 1px solid rgba(33, 150, 243, 0.4);
  transition: all 0.2s ease;
}
.btn-close { 
  background: rgba(100, 100, 100, 0.25); 
  color: #aaa;
  border: 1px solid rgba(100, 100, 100, 0.4);
  transition: all 0.2s ease;
}

.btn-clear:hover { 
  background: rgba(76, 175, 80, 0.4); 
  border-color: rgba(76, 175, 80, 0.6);
}
.btn-trigger:hover { 
  background: rgba(244, 67, 54, 0.4); 
  border-color: rgba(244, 67, 54, 0.6);
}
.btn-info:hover { 
  background: rgba(33, 150, 243, 0.4); 
  border-color: rgba(33, 150, 243, 0.6);
}
.btn-close:hover { 
  background: rgba(100, 100, 100, 0.4); 
  border-color: rgba(100, 100, 100, 0.6);
}

/* ========== 设备信息弹窗样式 ========== */

/* 弹窗遮罩层 - Requirements: 2.1, 2.4 */
.device-info-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 1920px;
  height: 1080px;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2100;
}

/* 弹窗内容容器 - Requirements: 2.1 */
.device-info-content {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border-radius: 12px;
  width: 90vw;
  max-width: 700px;
  max-height: 85vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(79, 195, 247, 0.3);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

/* 弹窗头部 - Requirements: 2.2, 2.3 */
.device-info-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: rgba(0, 0, 0, 0.3);
  border-bottom: 1px solid rgba(79, 195, 247, 0.2);
}

.device-info-title {
  color: #72cfff;
  font-size: 18px;
  font-weight: bold;
}

.close-btn {
  background: transparent;
  border: none;
  color: #888;
  font-size: 24px;
  cursor: pointer;
  padding: 0 8px;
  line-height: 1;
  transition: color 0.3s ease;
}

.close-btn:hover {
  color: #fff;
}

/* 弹窗主体 */
.device-info-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

/* 加载状态样式 - Requirements: 5.2 */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #7ec8e3;
}

.loading-icon {
  font-size: 36px;
  margin-bottom: 12px;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.loading-text {
  font-size: 16px;
}

/* 错误状态样式 - Requirements: 5.3 */
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #f56c6c;
}

.error-icon {
  font-size: 36px;
  margin-bottom: 12px;
}

.error-text {
  font-size: 16px;
  text-align: center;
}

/* 信息区块容器 */
.info-sections {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 信息区块样式 - Requirements: 3.1, 3.2 */
.info-section {
  background: rgba(30, 40, 60, 0.5);
  border: 1px solid rgba(126, 200, 227, 0.2);
  border-radius: 8px;
  padding: 16px;
}

.section-title {
  color: #7ec8e3;
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 16px 0;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(126, 200, 227, 0.2);
  letter-spacing: 0.5px;
}

/* 信息网格布局 - Requirements: 3.4 */
.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}

/* 单个信息项样式 - Requirements: 3.4 */
.info-item {
  display: flex;
  flex-direction: column;
  padding: 12px 14px;
  background: rgba(20, 30, 50, 0.5);
  border: 1px solid rgba(100, 120, 150, 0.2);
  border-radius: 6px;
  transition: all 0.2s ease;
}

.info-item:hover {
  background: rgba(30, 40, 60, 0.6);
  border-color: rgba(100, 120, 150, 0.4);
}

.label {
  color: #7ec8e3;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 8px;
  letter-spacing: 0.3px;
}

.value {
  color: #fff;
  font-size: 15px;
  word-break: break-all;
  line-height: 1.4;
}

/* 在线/离线状态样式 */
.value.online {
  color: #67c23a;
}

.value.offline {
  color: #f56c6c;
}

/* 作业状态样式 */
.value.status-active {
  color: #67c23a;
}

.value.status-completed {
  color: #909399;
}

/* 滚动条样式 */
.device-info-body::-webkit-scrollbar {
  width: 6px;
}

.device-info-body::-webkit-scrollbar-track {
  background: transparent;
}

.device-info-body::-webkit-scrollbar-thumb {
  background-color: rgba(255, 255, 255, 0.3);
  border-radius: 3px;
}

.device-info-body::-webkit-scrollbar-thumb:hover {
  background-color: rgba(255, 255, 255, 0.5);
}

/* 响应式布局 - 小屏幕单列显示 */
@media (max-width: 600px) {
  .info-grid {
    grid-template-columns: 1fr;
  }
  
  .device-info-content {
    width: 95vw;
    max-height: 90vh;
  }
}

/* ========== 工作环境数据信息样式 ========== */

/* 气体数据网格布局 */
.gas-data-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* 气体数据卡片 */
.gas-card {
  display: flex;
  align-items: center;
  padding: 12px 14px;
  border-radius: 6px;
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
  font-size: 14px;
  font-weight: 500;
  min-width: 110px;
}

.gas-value {
  color: #fff;
  font-size: 16px;
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
  font-size: 13px;
  margin-left: 4px;
}


/* 语音按钮样式 */
.btn-voice { 
  background: rgba(156, 39, 176, 0.25); /* 紫色背景 */
  color: #ba68c8;
  border: 1px solid rgba(156, 39, 176, 0.4);
  transition: all 0.2s ease;
  user-select: none; /* 防止一直按着时选中文本 */
  display: flex; /* 确保内容居中 */
  align-items: center;
  justify-content: center;
  overflow: hidden; /* [新增] 防止内部元素溢出 */
}

.btn-voice:hover { 
  background: rgba(156, 39, 176, 0.4); 
  border-color: rgba(156, 39, 176, 0.6);
}

/* 通话时的激活状态：闪烁动画 */
.btn-voice.talking {
  background: rgba(156, 39, 176, 0.8);
  color: white;
  animation: voice-pulse 1.5s infinite;
}

@keyframes voice-pulse {
  0% { box-shadow: 0 0 0 0 rgba(186, 104, 200, 0.7); }
  70% { box-shadow: 0 0 0 10px rgba(186, 104, 200, 0); }
  100% { box-shadow: 0 0 0 0 rgba(186, 104, 200, 0); }
}

/* 声波容器 */
.voice-wave {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 24px; /* 容器高度 */
  gap: 4px;     /* 柱子间距 */
}

/* 声波柱子 */
.voice-wave .bar {
  width: 4px;
  background-color: #fff;
  border-radius: 2px;
  /* 关键：使用 transition 实现平滑过渡，去掉 animation */
  transition: height 0.05s ease;
  box-shadow: 0 0 4px rgba(255, 255, 255, 0.5);
}

</style>
