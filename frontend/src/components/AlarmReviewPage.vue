<template>
  <div class="alarm-review-page">
    <!-- 全屏图片查看 -->
    <div v-if="fullscreenImage" class="fullscreen-overlay" @click="fullscreenImage = null">
      <img :src="fullscreenImage" alt="全屏查看" :style="fullscreenImageStyle" />
    </div>

    <!-- 放大弹窗 -->
    <div v-if="zoomedItem" class="zoom-overlay" @click.self="zoomedItem = null">
      <div
        class="zoom-card"
        :class="{
          'status-false-alarm': zoomedItem.review_status === 1,
          'status-real-alarm': zoomedItem.review_status === 2
        }"
      >
        <button class="zoom-close" @click="zoomedItem = null">✕</button>
        <div class="zoom-image">
          <img
            v-if="zoomedItem.image"
            :src="zoomedItem.image"
            alt="报警截图"
            :style="alarmImageStyle(zoomedItem)"
            style="cursor: pointer"
            @click="fullscreenImage = zoomedItem.image"
          />
          <div v-else class="image-placeholder">无图片</div>
        </div>
        <div class="zoom-summary">
          {{ zoomedItem.note }} | {{ zoomedItem.type2 }} | {{ zoomedItem.type }}
        </div>
        <div class="zoom-actions">
          <button
            class="action-btn btn-false"
            :class="{ active: zoomedItem.review_status === 1 }"
            @click="handleMark(zoomedItem, 1)"
            :disabled="zoomedItem._updating"
          >
            误报警
          </button>
          <button
            class="action-btn btn-real"
            :class="{ active: zoomedItem.review_status === 2 }"
            @click="handleMark(zoomedItem, 2)"
            :disabled="zoomedItem._updating"
          >
            确定报警
          </button>
        </div>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="review-loading">
      <span>加载中...</span>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="review-error">
      <span>{{ error }}</span>
      <button class="retry-btn" @click="fetchData">重试</button>
    </div>

    <!-- 空数据 -->
    <div v-else-if="records.length === 0" class="review-empty">
      <span>当天暂无报警记录</span>
    </div>

    <!-- 分类筛选 Tab -->
    <div v-if="!loading && !error && records.length > 0" class="review-filter-tabs">
      <button
        v-for="tab in filterTabs"
        :key="tab.value"
        class="filter-tab"
        :class="{ active: activeFilter === tab.value }"
        @click="activeFilter = tab.value"
      >
        {{ tab.label }}
        <span class="filter-count">{{ tab.count }}</span>
      </button>
    </div>

    <!-- 实时统计提示条 -->
    <div v-if="!loading && !error && records.length > 0" class="review-stats-bar">
      <span class="stats-label">实时统计</span>
      <span class="stats-item stats-real">
        <span class="stats-dot dot-real"></span>
        确定报警 <strong>{{ confirmedCount }}</strong> 条
      </span>
      <span class="stats-divider">|</span>
      <span class="stats-item stats-false">
        <span class="stats-dot dot-false"></span>
        误报警 <strong>{{ falseCount }}</strong> 条
      </span>
      <span class="stats-divider">|</span>
      <span class="stats-item stats-pending">
        <span class="stats-dot dot-pending"></span>
        未处理 <strong>{{ unhandledCount }}</strong> 条
      </span>
      <span class="stats-total">共 {{ records.length }} 条</span>
    </div>

    <!-- 卡片网格 -->
    <div v-if="!loading && !error && records.length > 0" class="review-grid">
      <div
        v-for="item in filteredRecords"
        :key="item.review_key"
        class="review-card"
        :class="{
          'status-false-alarm': item.review_status === 1,
          'status-real-alarm': item.review_status === 2
        }"
        @dblclick="zoomedItem = item"
      >
        <!-- 报警截图 -->
        <div class="card-image">
          <img
            v-if="item.image"
            :src="item.image"
            alt="报警截图"
            :style="alarmImageStyle(item)"
            @error="item.image = null"
          />
          <div v-else class="image-placeholder">无图片</div>
        </div>

        <!-- 摘要：报警大类 | 报警小类 + 时间 -->
        <div class="card-summary">
          <div class="summary-row">
            <span class="summary-type">{{ item.type2 || '未知类别' }}</span>
            <span class="summary-sep">|</span>
            <span class="summary-subtype">{{ item.type || '--' }}</span>
          </div>
          <div class="summary-meta">
            <span class="summary-note" :title="item.note">{{ item.note || '--' }}</span>
            <span class="summary-time">{{ item.alarm_time || '' }}</span>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="card-actions">
          <button
            class="action-btn btn-false"
            :class="{ active: item.review_status === 1 }"
            @click="handleMark(item, 1)"
            :disabled="item._updating"
          >
            误报警
          </button>
          <button
            class="action-btn btn-real"
            :class="{ active: item.review_status === 2 }"
            @click="handleMark(item, 2)"
            :disabled="item._updating"
          >
            确定报警
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { alarmReviewApi } from '@/services/api';

export default {
  name: 'AlarmReviewPage',

  props: {
    refreshKey: {
      type: Number,
      default: 0,
    },
  },

  data() {
    return {
      records: [],
      loading: false,
      error: null,
      zoomedItem: null,
      fullscreenImage: null,
      activeFilter: 'all',
    };
  },
  computed: {
    confirmedCount() {
      return this.records.filter(r => r.review_status === 2).length;
    },
    falseCount() {
      return this.records.filter(r => r.review_status === 1).length;
    },
    unhandledCount() {
      return this.records.filter(r => !r.review_status || r.review_status === 0).length;
    },
    filterTabs() {
      return [
        { label: '全部',     value: 'all',     count: this.records.length },
        { label: '确定报警', value: 'real',    count: this.confirmedCount },
        { label: '误报警',   value: 'false',   count: this.falseCount },
        { label: '未处理',   value: 'pending', count: this.unhandledCount },
      ];
    },
    filteredRecords() {
      if (this.activeFilter === 'real')    return this.records.filter(r => r.review_status === 2);
      if (this.activeFilter === 'false')   return this.records.filter(r => r.review_status === 1);
      if (this.activeFilter === 'pending') return this.records.filter(r => !r.review_status || r.review_status === 0);
      return this.records;
    },
    /**
     * 全屏图片样式（复用 zoomedItem 的旋转）
     */
    fullscreenImageStyle() {
      if (this.zoomedItem) {
        return this.alarmImageStyle(this.zoomedItem);
      }
      return {};
    },
    /**
     * 设备旋转角度映射 { device_id: rotation }
     */
    deviceRotationMap() {
      const map = {};
      const areaDevices = this.$store.state.devices.areaDevices || {};
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
    },
  },

  mounted() {
    this.fetchData();
  },
  watch: {
    refreshKey() {
      this.fetchData(true);
    },
  },

  methods: {
    /**
     * 告警图片的 CSS 样式
     * 截图已在 captureSnapshot 中根据设备旋转角度做了180度翻转，
     * 保存的图片本身已经是正向的，展示时不再需要旋转。
     */
    alarmImageStyle(item) {
      return {};
    },

    async fetchData(silent = false) {
      if (!silent) {
        this.loading = true;
      }
      this.error = null;
    
      const result = await alarmReviewApi.getToday();
    
      if (result.error) {
        this.error = result.message || '获取数据失败';
      } else {
        this.records = (result.data.data || []).map(r => ({ ...r, _updating: false }));
      }
    
      this.loading = false;
    },

    async handleMark(item, targetStatus) {
      if (item._updating) return;

      // Toggle 逻辑：再次点击同一按钮则回退为 0
      const newStatus = item.review_status === targetStatus ? 0 : targetStatus;
      const oldStatus = item.review_status;

      // 乐观更新
      item.review_status = newStatus;
      item._updating = true;

      const result = await alarmReviewApi.updateStatus(item.review_key, newStatus);

      if (result.error) {
        // 回滚
        item.review_status = oldStatus;
        alert(`标注失败: ${result.message}`);
            } else {
        // 通知父组件刷新待处理数量
        this.$emit('alarm-reviewed');
      }

      item._updating = false;
    },
  }
};
</script>

<style scoped>
.alarm-review-page {
  width: 100%;
  height: 100%;
  padding: 16px;
  overflow-y: auto;
  box-sizing: border-box;
  font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
  color: #eef9ff;
  font-weight: 500;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.review-loading,
.review-error,
.review-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: #e7f6ff;
  font-weight: 600;
  font-size: 16px;
  gap: 12px;
}

.retry-btn {
  padding: 6px 16px;
  background: rgba(75, 184, 255, 0.18);
  border: 1px solid #4bb8ff;
  color: #eaf7ff;
  font-weight: 600;
  border-radius: 4px;
  cursor: pointer;
}

/* ========== 实时统计条 ========== */
.review-stats-bar {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 8px 14px;
  margin-bottom: 12px;
  background: rgba(96, 170, 224, 0.28);
  border: 1px solid rgba(146, 196, 255, 0.35);
  border-radius: 6px;
  font-size: 13px;
  flex-wrap: wrap;
}

.stats-label {
  color: #7ee0f0;
  font-weight: 600;
  letter-spacing: 1px;
  margin-right: 4px;
}

.stats-item {
  display: flex;
  align-items: center;
  gap: 5px;
}

.stats-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
  animation: dot-pulse 1.4s infinite;
}

.dot-real  { background: #50ff78; box-shadow: 0 0 5px #50ff78; }
.dot-false { background: #ff5050; box-shadow: 0 0 5px #ff5050; animation-delay: 0.2s; }
.dot-pending { background: #f0c040; box-shadow: 0 0 5px #f0c040; animation-delay: 0.4s; }

@keyframes dot-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.35; }
}

.stats-real   strong { color: #50ff78; }
.stats-false  strong { color: #ff5050; }
.stats-pending strong { color: #f0c040; }

.stats-item { color: #b8d8e8; }
.stats-item { color: #e8f6ff; font-weight: 600; }

.stats-divider {
  color: rgba(184, 216, 232, 0.55);
  user-select: none;
}

.stats-total {
  margin-left: auto;
  color: #dff4ff;
  opacity: 0.85;
  font-weight: 600;
  font-size: 12px;
}

/* ========== 分类筛选 Tab ========== */
.review-filter-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.filter-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 14px;
  background: rgba(96, 170, 224, 0.30);
  border: 1px solid rgba(146, 196, 255, 0.42);
  border-radius: 4px;
  color: #eaf7ff;
  font-weight: 600;
  font-size: 13px;
  font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-tab:hover {
  border-color: rgba(75, 184, 255, 0.75);
  color: #eaf7ff;
}

.filter-tab.active {
  background: rgba(75, 184, 255, 0.24);
  border-color: #4bb8ff;
  color: #4bb8ff;
  box-shadow: 0 0 8px rgba(75, 184, 255, 0.32);
}

.filter-count {
  min-width: 18px;
  height: 18px;
  border-radius: 9px;
  background: rgba(75, 184, 255, 0.18);
  color: #eaf7ff;
  font-weight: 700;
  font-size: 11px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 5px;
}

.filter-tab.active .filter-count {
  background: rgba(75, 184, 255, 0.32);
  color: #d9fbff;
}


.review-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.review-card {
  background: rgba(96, 170, 224, 0.30);
  border: 2px solid rgba(146, 196, 255, 0.35);
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: border-color 0.3s;
}

/* 误报警 - 绿色闪烁 */
.review-card.status-false-alarm {
  animation: blink-green 1.2s infinite;
}

/* 确定报警 - 红色闪烁 */
.review-card.status-real-alarm {
  animation: blink-red 1.2s infinite;
}

@keyframes blink-green {
  0%, 100% { border-color: rgba(80, 255, 120, 0.9); }
  50% { border-color: rgba(80, 255, 120, 0.3); }
}

@keyframes blink-red {
  0%, 100% { border-color: rgba(255, 80, 80, 0.9); }
  50% { border-color: rgba(255, 80, 80, 0.3); }
}

.card-image {
  width: 100%;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  background: #5f97c5;
}

.card-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #d7efff;
  font-size: 13px;
}

.card-summary {
  padding: 7px 10px;
  border-top: 1px solid rgba(146, 196, 255, 0.35);
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.summary-row {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  font-weight: 700;
  color: #d9fbff;
  white-space: nowrap;
  overflow: hidden;
}

.summary-type {
  color: #7ee0f0;
  flex-shrink: 0;
}

.summary-sep {
  color: rgba(184, 216, 232, 0.6);
  flex-shrink: 0;
}

.summary-subtype {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.summary-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 6px;
}

.summary-note {
  font-size: 11px;
  color: #eef9ff;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.summary-time {
  font-size: 11px;
  color: #d5edff;
  font-weight: 600;
  flex-shrink: 0;
  white-space: nowrap;
}

.card-actions {
  display: flex;
  gap: 6px;
  padding: 8px 10px;
  border-top: 1px solid rgba(146, 196, 255, 0.35);
}

.action-btn {
  flex: 1;
  padding: 6px 0;
  border: 1px solid rgba(146, 196, 255, 0.42);
  border-radius: 4px;
  background: transparent;
  color: #eef9ff;
  font-size: 13px;
  font-weight: 700;
  font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:hover {
  background: rgba(75, 184, 255, 0.24);
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-false.active {
  background: rgba(80, 255, 120, 0.25);
  border-color: #50ff78;
  color: #50ff78;
}

.btn-real.active {
  background: rgba(255, 80, 80, 0.25);
  border-color: #ff5050;
  color: #ff5050;
}


/* ========== 放大弹窗 ========== */
.zoom-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 1920px;
  height: 1080px;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.zoom-card {
  position: relative;
  width: 600px;
  max-width: 90vw;
  max-height: 90vh;
  background: rgba(96, 170, 224, 0.94);
  border: 2px solid rgba(146, 196, 255, 0.45);
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.zoom-card.status-false-alarm {
  animation: blink-green 1.2s infinite;
}
 
.zoom-card.status-real-alarm {
  animation: blink-red 1.2s infinite;
}

.zoom-close {
  position: absolute;
  top: 8px;
  right: 12px;
  background: rgba(0, 0, 0, 0.5);
  border: none;
  color: #fff;
  font-size: 18px;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  cursor: pointer;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.zoom-close:hover {
  background: rgba(255, 80, 80, 0.6);
}

.zoom-image {
  width: 100%;
  max-height: 60vh;
  overflow: hidden;
  background: #5f97c5;
}

.zoom-image img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.zoom-summary {
  padding: 12px 16px;
  color: #f1fbff;
  font-size: 15px;
  font-weight: 700;
  line-height: 1.5;
  border-top: 1px solid rgba(146, 196, 255, 0.35);
}

.zoom-actions {
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  border-top: 1px solid rgba(146, 196, 255, 0.35);
}

.zoom-actions .action-btn {
  padding: 10px 0;
  font-size: 15px;
}

/* ========== 全屏图片查看 ========== */
.fullscreen-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 1920px;
  height: 1080px;
  background: rgba(0, 0, 0, 0.92);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  cursor: zoom-out;
}

.fullscreen-overlay img {
  max-width: 1800px;
  max-height: 1000px;
  object-fit: contain;
}
</style>
