<template>
  <div class="gas-monitor-page">
    <!-- 顶部标题栏 -->
    <div class="gm-header">
      <div class="gm-title">
        <span class="gm-icon">⬡</span>
        气体实时监控
      </div>
      <div class="gm-meta">
        <span class="gm-badge" :class="connected ? 'badge-online' : 'badge-offline'">
          {{ connected ? '● 已连接' : '○ 未连接' }}
        </span>
        <span class="gm-update-time">更新时间：{{ displayTime || '—' }}</span>
        <button class="gm-refresh-btn" @click="fetchMonitorData" :disabled="loading">
          {{ loading ? '刷新中…' : '立即刷新' }}
        </button>
      </div>
    </div>

    <!-- 播报横幅：有报警时滚动显示 -->
    <div class="gm-broadcast" v-if="alarmMessages.length">
      <span class="broadcast-icon">🔔</span>
      <div class="broadcast-ticker">
        <span class="broadcast-text">{{ alarmMessages.join(' | ') }}</span>
      </div>
    </div>


    <!-- 加载中状态 -->
    <div class="gm-loading" v-if="loading">
      <div class="loading-spinner"></div>
      <div class="loading-text">正在连接气体监控…</div>
    </div>

    <!-- 无设备提示（仅在非加载状态且确实无数据时显示） -->
    <div class="gm-empty" v-else-if="deviceIds.length === 0 && !_isFirstLoad">
      <div class="empty-icon">📡</div>
      <div class="empty-text">暂无在线气体监测设备</div>
      <div class="empty-sub">等待边缘端设备接入并上报数据…</div>
    </div>

    <!-- 设备卡片列表 -->
    <div class="gm-grid" v-else-if="deviceIds.length > 0">
      <div
        class="gm-device-card"
        v-for="devId in deviceIds"
        :key="devId"
        :class="{ 'card-alarm': hasAnyAlarm(devId) }"
      >
        <!-- 卡片头 -->
        <div class="card-header">
          <div class="card-device-name">
            <span class="device-dot" :class="hasAnyAlarm(devId) ? 'dot-alarm' : 'dot-normal'"></span>
            {{ getDeviceName(devId) }}
          </div>
          <div class="card-device-id">ID: {{ devId }}</div>
          <div class="card-time">{{ getUpdateTime(devId) }}</div>
        </div>

        <!-- 气体数值网格 -->
        <div class="card-gas-grid">
          <div
            class="gas-item"
            v-for="reg in registry"
            :key="reg.key"
            :class="isAlarm(devId, reg.key) ? 'gas-alarm' : 'gas-normal'"
          >
            <div class="gas-label">{{ reg.display }}</div>
            <div class="gas-value">
              <span class="gas-num">{{ formatValue(devId, reg.key) }}</span>
              <span class="gas-unit">{{ reg.unit }}</span>
            </div>
            <div class="gas-threshold" v-if="reg.has_threshold">
              阈值 {{ getThreshold(devId, reg.key) }}
            </div>
            <div class="alarm-tag" v-if="isAlarm(devId, reg.key)">⚠ 超限</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { gasApi } from '@/services/api';
import { useGasDataSSE } from '@/composables/useSSE';

export default {
  name: 'GasMonitorPage',

  data() {
    return {
      loading: true,  // 初始化为加载中，避免闪烁显示"暂无设备"
      realtime: {},      // { device_id: { C3H8: "100", ... } }
      threshold: {},     // { device_id: { C3H8: 9999, ... } }
      registry: [],      // [ { key, display, unit, has_threshold, threshold_default } ]
      lastUpdateTime: '', // 数据真正更新的时间
      displayTime: '',    // 页面上显示的时钟时间（每秒更新）
      connected: false,
      gasDataSSE: null,
      initTimer: null,
      _gasBuffer: {},
      _gasFlushTimer: null,
      _clockTimer: null,   // 时钟定时器
      _isFirstLoad: true,  // 标记是否首次加载
    };
  },

  computed: {
    deviceIds() {
      // 过滤掉掉线的设备（超过30秒无数据更新视为离线）
      const now = new Date();
      return Object.keys(this.realtime).filter(devId => {
        const data = this.realtime[devId];
        if (!data || !data.update_time) return false;
        
        // 解析 update_time 字符串（兼容两种格式：YYYY-MM-DD HH:MM:SS 或 HH:MM:SS）
        let updateTime;
        const timeStr = data.update_time;
        
        if (timeStr.includes('-') && timeStr.includes(' ')) {
          // 格式：YYYY-MM-DD HH:MM:SS
          updateTime = new Date(timeStr);
        } else {
          // 格式：HH:MM:SS
          const [hours, minutes, seconds] = timeStr.split(':').map(Number);
          updateTime = new Date();
          updateTime.setHours(hours, minutes, seconds, 0);
        }
        
        // 检查日期是否有效
        if (isNaN(updateTime.getTime())) return false;
        
        // 计算时间差（秒）
        const diffSeconds = (now - updateTime) / 1000;
        
        // 超过30秒无数据更新视为离线，不显示
        // 注意：如果是负数（跨天情况），说明数据是昨天的，也视为离线
        return diffSeconds >= 0 && diffSeconds <= 30;
      });
    },


    // 生成播报文字列表（所有超限项）
    alarmMessages() {
      const msgs = [];
      for (const devId of this.deviceIds) {
        for (const reg of this.registry) {
          if (this.isAlarm(devId, reg.key)) {
            const val = this.formatValue(devId, reg.key);
            const thr = this.getThreshold(devId, reg.key);
            msgs.push(`${this.getDeviceName(devId)} ${reg.display} ${val}${reg.unit}(\u9608\u503c${thr})`);
          }
        }
      }
      return msgs;
    },
  },

  async mounted() {
    // 立即启动时钟（每秒更新显示时间）
    this._startClock();
    // 立即创建 SSE 连接（优先建立连接）
    this._initSSE();
    // 并行拉取完整的监控数据（含 registry/threshold + 历史快照）
    await this.fetchMonitorData();
  },

  beforeUnmount() {
    if (this.gasDataSSE) {
      this.gasDataSSE.disconnect();
      this.gasDataSSE = null;
    }
    if (this.initTimer) {
      clearTimeout(this.initTimer);
      this.initTimer = null;
    }
    if (this._gasFlushTimer) {
      clearTimeout(this._gasFlushTimer);
      this._gasFlushTimer = null;
    }
    if (this._clockTimer) {
      clearInterval(this._clockTimer);
      this._clockTimer = null;
    }
  },

  methods: {
    /** 初始化 SSE 气体数据订阅（SSE 是真正的推送，不堵塞） */
    _initSSE() {
      this.gasDataSSE = useGasDataSSE({
        onMessage: (data) => {
          if (data.device_id) {
            // 首次数据到达时立即更新（避免等待缓冲）
            const isFirstData = this._isFirstLoad;
            
            this._gasBuffer[data.device_id] = {
              ...data,
              update_time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
            };
            this.connected = true;
            
            // 首次数据立即显示，后续再批量缓冲
            if (isFirstData) {
              this._flushGasBuffer();
            } else if (!this._gasFlushTimer) {
              // 非首次数据使用较短缓冲（500ms，更流畅）
              this._gasFlushTimer = setTimeout(() => {
                this._flushGasBuffer();
              }, 500);
            }
          }
        },
        onError: () => {
          this.connected = false;
        },
      });
      this.gasDataSSE.connect();
    },

    /** 刷新气体数据缓冲 */
    _flushGasBuffer() {
      this._gasFlushTimer = null;
      const batch = this._gasBuffer;
      this._gasBuffer = {};
      this.realtime = { ...this.realtime, ...batch };
      // lastUpdateTime 仅用于记录真实数据更新时间，不影响显示
      this.lastUpdateTime = new Date().toLocaleTimeString('zh-CN', { hour12: false });
    },

    /** 拉取完整监控数据（registry + threshold + realtime 初始快照） */
    async fetchMonitorData() {
      // 超时保护：3秒后强制结束加载状态，避免一直显示加载中
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => reject(new Error('timeout')), 3000);
      });

      try {
        const res = await Promise.race([gasApi.getMonitorData(), timeoutPromise]);
        if (!res.error && res.data) {
          this._applyPayload(res.data);
        }
      } catch (e) {
        if (e.message !== 'timeout') {
          console.error('获取气体监控数据失败:', e);
        }
        // 超时或失败也结束加载，由 SSE 后续推送数据
      } finally {
        // 数据到达后才关闭 loading，避免闪烁显示"暂无设备"
        this.loading = false;
      }
    },

    /** 将服务端数据应用到本地 state */
    _applyPayload(payload) {
      // 确保数据一次性全部应用，避免部分更新导致UI闪烁
      const updates = {};
      if (payload.realtime !== undefined) updates.realtime = payload.realtime;
      if (payload.threshold !== undefined) updates.threshold = payload.threshold;
      if (payload.registry && payload.registry.length > 0) updates.registry = payload.registry;
      
      // 批量应用更新
      Object.assign(this, updates);
      
      // 标记已有数据到达（不修改 displayTime，保持时钟流畅）
      this._isFirstLoad = false;
      this.lastUpdateTime = new Date().toLocaleTimeString('zh-CN', { hour12: false });
    },

    /** 启动时钟：每秒更新显示时间，独立于数据更新 */
    _startClock() {
      // 立即设置一次
      this._updateClock();
      // 每秒更新
      this._clockTimer = setInterval(() => {
        this._updateClock();
      }, 1000);
    },

    /** 更新时钟显示 */
    _updateClock() {
      this.displayTime = new Date().toLocaleTimeString('zh-CN', { hour12: false });
    },

    getDeviceName(devId) {
      const d = this.realtime[devId];
      return (d && d.device_name) ? d.device_name : `设备 ${devId}`;
    },

    getUpdateTime(devId) {
      const d = this.realtime[devId];
      return (d && d.update_time) ? d.update_time : '';
    },

    formatValue(devId, key) {
      const d = this.realtime[devId];
      if (!d) return '—';
      const v = d[key];
      if (v === undefined || v === null || v === '') return '—';
      const num = parseFloat(v);
      return isNaN(num) ? v : num.toFixed(1);
    },

    getThreshold(devId, key) {
      // 优先设备自己上报的阈值，找不到则用注册表默认值
      const thr = this.threshold[devId];
      if (thr && thr[key] !== undefined && thr[key] !== null) return thr[key];
      const reg = this.registry.find(r => r.key === key);
      return reg ? (reg.threshold_default ?? '—') : '—';
    },

    isAlarm(devId, key) {
      const reg = this.registry.find(r => r.key === key);
      if (!reg || !reg.has_threshold) return false;
      const val = parseFloat(this.realtime[devId]?.[key]);
      if (isNaN(val)) return false;
      const thr = parseFloat(this.getThreshold(devId, key));
      if (isNaN(thr)) return false;
      return val > thr;
    },

    hasAnyAlarm(devId) {
      return this.registry.some(r => this.isAlarm(devId, r.key));
    },
  },
};
</script>

<style scoped>
.gas-monitor-page {
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow-y: auto;
  background: linear-gradient(135deg, #173a59 0%, #24557c 52%, #1a4263 100%);
  color: #eef8ff;
  padding: 18px 24px;
  box-sizing: border-box;
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

/* ===== 顶部标题栏 ===== */
.gm-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
  border-bottom: 1px solid #bde6ff;
  padding-bottom: 12px;
}
.gm-title {
  font-size: 18px;
  font-weight: 700;
  color: #eef9ff;
  letter-spacing: 2px;
}
.gm-icon {
  margin-right: 8px;
  color: #88d4ff;
}
.gm-meta {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 12px;
}
.gm-badge {
  padding: 2px 10px;
  border-radius: 20px;
  font-weight: 600;
}
.badge-online  { background: rgba(0,220,120,0.15); color: #00dc78; border: 1px solid #00dc7860; }
.badge-offline { background: rgba(180,60,60,0.15); color: #f06060; border: 1px solid #f0606060; }
.gm-update-time { color: #f5fcff; }
.gm-refresh-btn {
  background: #3f86bd;
  border: 1px solid #b8def8;
  color: #eef9ff;
  border-radius: 4px;
  padding: 3px 12px;
  cursor: pointer;
  font-size: 12px;
  transition: background 0.2s, border-color 0.2s;
}
.gm-refresh-btn:hover:not(:disabled) { background: #4d96ce; border-color: #d7eeff; }
.gm-refresh-btn:disabled { opacity: 0.5; cursor: not-allowed; }



/* ===== 播报横幅 ===== */
.gm-broadcast {
  display: flex;
  align-items: center;
  background: rgba(255, 80, 80, 0.12);
  border: 1px solid rgba(255, 80, 80, 0.4);
  border-radius: 6px;
  padding: 8px 14px;
  margin-bottom: 14px;
  overflow: hidden;
}
.broadcast-icon { font-size: 16px; margin-right: 10px; flex-shrink: 0; }
.broadcast-ticker {
  flex: 1;
  overflow: hidden;
  white-space: nowrap;
}
.broadcast-text {
  display: inline-block;
  color: #ff8080;
  font-size: 13px;
  animation: ticker 18s linear infinite;
}
@keyframes ticker {
  0%   { transform: translateX(100%); }
  100% { transform: translateX(-100%); }
}

/* ===== 加载中状态 ===== */
.gm-loading {
  text-align: center;
  margin-top: 100px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}
.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(170, 215, 255, 0.3);
  border-top-color: #aad7ff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.loading-text {
  font-size: 14px;
  color: #d6edff;
}

/* ===== 空状态 ===== */
.gm-empty {
  text-align: center;
  margin-top: 80px;
}
.empty-icon { font-size: 48px; margin-bottom: 12px; opacity: 0.5; }
.empty-text { font-size: 16px; color: #eff9ff; margin-bottom: 6px; }
.empty-sub  { font-size: 12px; color: #e0f1fd; }

/* ===== 设备卡片网格 ===== */
.gm-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 20px;
}

.gm-device-card {
  background: #285a85;
  border: 1px solid #a9d0ec;
  border-radius: 10px;
  padding: 18px 20px 20px;
  transition: border-color 0.3s, box-shadow 0.3s;
  box-shadow: inset 0 0 14px rgba(180, 220, 245, 0.22);
}
.gm-device-card.card-alarm {
  border-color: rgba(255, 80, 80, 0.6);
  box-shadow: 0 0 14px rgba(255, 60, 60, 0.2);
  animation: card-pulse 2s ease-in-out infinite;
}
@keyframes card-pulse {
  0%, 100% { box-shadow: 0 0 10px rgba(255,60,60,0.15); }
  50%       { box-shadow: 0 0 22px rgba(255,60,60,0.40); }
}

/* 卡片头 */
.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid #c5e7ff;
}
.card-device-name {
  font-size: 14px;
  font-weight: 600;
  color: #f1f9ff;
  flex: 1;
  display: flex;
  align-items: center;
  gap: 6px;
}
.device-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dot-normal { background: #00dc78; box-shadow: 0 0 6px #00dc78; }
.dot-alarm  { background: #ff5050; box-shadow: 0 0 6px #ff5050; animation: dot-blink 1s step-end infinite; }
@keyframes dot-blink { 0%,100%{opacity:1} 50%{opacity:0.2} }

.card-device-id { font-size: 11px; color: #e1f1ff; }
.card-time { font-size: 11px; color: #e1f1ff; margin-left: auto; }

/* 气体数值网格 */
.card-gas-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
  gap: 10px;
}
.gas-item {
  background: #214f76;
  border: 1px solid #9ec7e6;
  border-radius: 6px;
  padding: 12px 8px 10px;
  text-align: center;
  position: relative;
  transition: border-color 0.3s;
}
.gas-item.gas-alarm {
  background: rgba(255, 60, 60, 0.08);
  border-color: rgba(255, 80, 80, 0.5);
}
.gas-label {
  font-size: 13px;
  color: #f3fbff;
  margin-bottom: 6px;
  letter-spacing: 0.5px;
}
.gas-value {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 2px;
  margin-bottom: 3px;
}
.gas-num {
  font-size: 22px;
  font-weight: 700;
  color: #ffffff;
  line-height: 1;
}
.gas-item.gas-alarm .gas-num { color: #ff7070; }
.gas-unit {
  font-size: 12px;
  color: #ecf7ff;
}
.gas-threshold {
  font-size: 12px;
  color: #e5f4ff;
}
.alarm-tag {
  font-size: 12px;
  color: #ff5050;
  font-weight: 600;
  margin-top: 4px;
}
</style>
