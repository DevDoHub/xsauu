<template>
  <div class="cockpit-page">
    <div class="dashboard-grid">
      <!-- 左栏：设备概览 + 报警统计 -->
      <aside class="col-left">
        <div class="panel-card">
          <div class="panel-title">区域报警概览</div>
          <div class="area-alarm-list">
            <div v-if="activeAreaAlarms.length === 0" class="area-no-alarm">
              <span class="area-ok-icon">✓</span> 当前无区域报警
            </div>
            <div
              v-for="(item, idx) in activeAreaAlarms"
              :key="item.area"
              class="area-alarm-row"
            >
              <span class="area-rank">#{{ idx + 1 }}</span>
              <span class="area-name">{{ item.area }}</span>
              <span class="area-count">{{ item.count }} 台报警</span>
            </div>
          </div>
        </div>
        <div class="panel-card flex-grow">
          <div class="panel-title-row">
            <span class="panel-title">报警类别统计</span>
            <div class="range-tabs">
              <button
                v-for="tab in rangeTabs"
                :key="tab.value"
                class="range-tab"
                :class="{ active: alarmTypeRange === tab.value }"
                @click="setAlarmTypeRange(tab.value)"
              >{{ tab.label }}</button>
            </div>
          </div>
          <div class="chart-wrapper">
            <div v-if="alarmTypeStatsError" class="stats-error-tip">{{ alarmTypeStatsError }}</div>
            <DashboardChart v-else :option="localAlarmTypeChartOption" height="100%" />
          </div>
        </div>
        <div class="panel-card flex-grow">
          <div class="panel-title">报警趋势分析</div>
          <div class="chart-wrapper">
            <DashboardChart :option="alarmTrendChartOption" height="100%" />
          </div>
        </div>
      </aside>

      <!-- 中栏：全局趋势 + 运行时长 -->
      <main class="col-center">
        <section class="kpi-strip">
          <div class="kpi-card">
            <span class="kpi-label">设备总数</span>
            <strong class="kpi-value">{{ totalDeviceCount }}</strong>
          </div>
          <div class="kpi-card highlight">
            <span class="kpi-label">在线设备</span>
            <strong class="kpi-value">{{ onlineDeviceCount }}</strong>
          </div>
          <div class="kpi-card">
            <span class="kpi-label">离线设备</span>
            <strong class="kpi-value">{{ offlineDeviceCount }}</strong>
          </div>
          <div class="kpi-card warning">
            <span class="kpi-label">报警设备</span>
            <strong class="kpi-value">{{ activeAlarmCount }}</strong>
          </div>
          <div class="kpi-card">
            <span class="kpi-label">气体异常{{ selectedGasDeviceId ? '(已筛选)' : '' }}</span>
            <strong class="kpi-value">{{ localGasAlertCount }}</strong>
          </div>
        </section>

        <div class="panel-card flex-grow">
          <div class="panel-title">在线设备趋势（实时）</div>
          <div class="chart-wrapper">
            <DashboardChart :option="onlineTrendOption" height="100%" />
          </div>
        </div>

        <div class="panel-card flex-grow">
          <div class="panel-title">设备运行时长</div>
          <div class="chart-wrapper" v-if="runtimeDevices.length">
            <DashboardChart :option="runtimeChartOption" height="100%" />
          </div>
          <div v-else class="empty-state">暂无运行时长数据</div>
        </div>
      </main>

      <!-- 右栏：环境风险与实时预警 -->
      <aside class="col-right">
        <div class="panel-card">
          <div class="panel-title">各区域设备数量</div>
          <DashboardChart :option="areaDeviceCountChartOption" height="260px" />
        </div>
        <div class="panel-card flex-grow">
          <div class="panel-title">气体超限设备</div>
          <div class="rank-list">
            <div v-if="gasOverLimitDevices.length === 0" class="empty-text">暂无超限设备</div>
            <div
              v-for="(item, idx) in gasOverLimitDevices"
              :key="`gas-rank-${idx}`"
              class="rank-row clickable"
              @click="locateDevice(item.deviceId)"
            >
              <span class="rank-index">#{{ idx + 1 }}</span>
              <span class="rank-name">{{ item.label }}</span>
              <span class="rank-value">{{ item.count }}项</span>
            </div>
          </div>
        </div>
        <div class="panel-card flex-grow">
          <div class="panel-title">高频报警设备 TOP</div>
          <div class="rank-list">
            <div v-if="topAlarmDevices.length === 0" class="empty-text">暂无报警数据</div>
            <div
              v-for="(item, idx) in topAlarmDevices"
              :key="`alarm-rank-${idx}`"
              class="rank-row clickable"
              @click="openTopAlarmModal(item)"
            >
              <span class="rank-index">#{{ idx + 1 }}</span>
              <span class="rank-name">{{ item.label }}</span>
              <span class="rank-value">{{ item.count }}次</span>
            </div>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script>
import DashboardChart from './DashboardChart.vue';
import { alarmReviewApi, gasApi } from '@/services/api';
export default {
  name: 'CockpitOverviewPage',
  components: { DashboardChart },
  props: {
    totalDeviceCount: { type: Number, default: 0 },
    onlineDeviceCount: { type: Number, default: 0 },
    activeAlarmCount: { type: Number, default: 0 },
    gasAlertCount: { type: Number, default: 0 },
    areaDevices: { type: Object, default: () => ({}) },
    alarmList: { type: Array, default: () => [] },
    alarmStatus: { type: Object, default: () => ({}) },
    realtimeGasData: { type: Object, default: () => ({}) },
    gasThreshold: { type: Object, default: () => ({}) },
    gasRegistry: { type: Array, default: () => [] },
    deviceStatusChartOption: { type: Object, default: () => ({}) },
    alarmTypeChartOption: { type: Object, default: () => ({}) },
    gasChartOption: { type: Object, default: () => ({}) },
    alarmTrendChartOption: { type: Object, default: () => ({}) },
    trendSamples: { type: Array, default: () => [] }
  },
  data() {
    return {
      alarmTypeRange: 'today',
      alarmTypeStatsData: [],
      alarmTypeStatsError: null,
      rangeTabs: [
        { label: '今日', value: 'today' },
        { label: '本周', value: 'week' },
        { label: '本月', value: 'month' },
      ],
      selectedGasDeviceId: null,
      localGasRealtime: {},
      localGasThreshold: {},
      localGasRegistry: [],
      // 运行时长本地增量（秒），用于实时更新在线设备的运行时长
      runtimeOffset: 0,
      runtimeTimer: null,
    };
  },
  mounted() {
    this.fetchAlarmTypeStats();
    // 初始化本地气体数据
    this.syncGasFromProps();
    // 启动运行时长本地计时器（每秒+1）
    this.runtimeTimer = setInterval(() => {
      this.runtimeOffset += 1;
    }, 1000);
  },
  beforeUnmount() {
    if (this.runtimeTimer) {
      clearInterval(this.runtimeTimer);
      this.runtimeTimer = null;
    }
  },

  watch: {
    // 监听父组件传入的实时气体数据变化（父组件已用 spread 创建新引用，无需 deep watch）
    realtimeGasData() {
      this.syncGasFromProps();
    },
    gasThreshold() {
      this.syncGasFromProps();
    },
    gasRegistry() {
      this.syncGasFromProps();
    },
  },

  computed: {
    offlineDeviceCount() {
      return Math.max(this.totalDeviceCount - this.onlineDeviceCount, 0);
    },

    activeAreaAlarms() {
      // 按"场地（workshop）"分组统计正在报警的设备数
      // 注意：areaDevices 外层 key 是"区域负责人"，但这里要改用每个设备的 workshop 字段重新分组
      const counter = {};  // { workshop: count }
      Object.values(this.areaDevices || {}).forEach(devicesMap => {
        Object.values(devicesMap || {}).forEach(device => {
          if (!device || typeof device !== 'object') return;
          const devNum = String(device.device_id ?? '');
          if (!devNum || !this.alarmStatus[devNum]?.alarm_active) return;
          const workshop = (device.workshop && String(device.workshop).trim()) || '未指定场地';
          counter[workshop] = (counter[workshop] || 0) + 1;
        });
      });
      return Object.keys(counter)
        .map(area => ({ area, count: counter[area] }))
        .sort((a, b) => b.count - a.count);
    },

    areaDeviceCountChartOption() {
      // 按"场地（workshop）"统计设备数量，忽略 areaDevices 外层的"区域负责人"分组
      const counter = {};  // { workshop: count }
      Object.values(this.areaDevices || {}).forEach(devicesMap => {
        Object.values(devicesMap || {}).forEach(device => {
          if (!device || typeof device !== 'object') return;
          const workshop = (device.workshop && String(device.workshop).trim()) || '未指定场地';
          counter[workshop] = (counter[workshop] || 0) + 1;
        });
      });
      const areas = Object.keys(counter);
      if (!areas.length) {
        return {
          grid: { left: 10, right: 12, top: 22, bottom: 32, containLabel: true },
          xAxis: { type: 'category', data: ['暂无场地'], axisLabel: { color: '#b8d8e8', fontSize: 10 }, axisLine: { lineStyle: { color: 'rgba(, , , 0.35)' } } },
          yAxis: { type: 'value', minInterval: 1, axisLabel: { color: '#b8d8e8' }, splitLine: { lineStyle: { color: 'rgba(, , , 0.35)' } } },
          series: [{ type: 'bar', data: [0], itemStyle: { color: '#1a4060', borderRadius: [6,6,0,0] } }]
        };
      }
      const counts = areas.map(area => counter[area]);
      const maxVal = Math.max(...counts, 1);
      return {
        tooltip: { trigger: 'axis', formatter: (p) => `${p[0]?.name}：${p[0]?.value} 台设备` },
        grid: { left: 10, right: 12, top: 22, bottom: 36, containLabel: true },
        xAxis: {
          type: 'category',
          data: areas,
          axisLabel: { color: '#b8d8e8', fontSize: 10, interval: 0, rotate: areas.length > 4 ? 28 : 0 },
          axisLine: { lineStyle: { color: 'rgba(, , , 0.35)' } }
        },
        yAxis: {
          type: 'value',
          minInterval: 1,
          max: maxVal + 1,
          axisLabel: { color: '#b8d8e8' },
          splitLine: { lineStyle: { color: 'rgba(, , , 0.35)' } }
        },
        series: [{
          type: 'bar',
          barWidth: 18,
          data: counts.map(v => ({ value: v, itemStyle: { color: '#4bb8ff', borderRadius: [6,6,0,0] } })),
          label: { show: true, position: 'top', color: '#d0f4ff', fontSize: 11 }
        }]
      };
    },

    localAlarmTypeChartOption() {
      const names = this.alarmTypeStatsData.map(item => item.name);
      const values = this.alarmTypeStatsData.map(item => item.value);
      return {
        color: ['#ffb84d'],
        tooltip: { trigger: 'axis' },
        grid: { left: 36, right: 12, top: 22, bottom: 32 },
        xAxis: {
          type: 'category',
          data: names.length ? names : ['暂无'],
          axisLabel: { color: '#b8d8e8', fontSize: 10, interval: 0 },
          axisLine: { lineStyle: { color: 'rgba(, , , 0.35)' } }
        },
        yAxis: {
          type: 'value',
          minInterval: 1,
          axisLabel: { color: '#b8d8e8' },
          splitLine: { lineStyle: { color: 'rgba(, , , 0.35)' } }
        },
        series: [{
          type: 'bar',
          barWidth: 14,
          data: values.length ? values : [0],
          itemStyle: { borderRadius: [8, 8, 0, 0] }
        }]
      };
    },


    deviceNameMap() {
      const map = {};
      // areaDevices 结构: { "区域负责人": { "设备名": DeviceRespVO } }
      Object.keys(this.areaDevices || {}).forEach((areaName) => {
        const devicesMap = this.areaDevices[areaName] || {};
        Object.keys(devicesMap).forEach((deviceName) => {
          const device = devicesMap[deviceName];
          if (device && typeof device === 'object') {
            const key = String(device.device_id ?? '');
            if (key) map[key] = device.name || key;
          }
        });
      });
      return map;
    },

    allDevices() {
      const output = [];
      // areaDevices 结构: { "区域负责人": { "设备名": DeviceRespVO } }
      Object.keys(this.areaDevices || {}).forEach((areaName) => {
        const devicesMap = this.areaDevices[areaName] || {};
        Object.keys(devicesMap).forEach((deviceName) => {
          const device = devicesMap[deviceName];
          if (device && typeof device === 'object' && !Array.isArray(device)) {
            output.push({
              ...device,
              areaName,
              label: device.name || device.device_id || `设备#${device.id ?? '--'}`
            });
          }
        });
      });
      return output;
    },

    topAlarmDevices() {
      const stats = {};
      (this.alarmList || []).forEach((alarm) => {
        const deviceKey = String(alarm.index ?? 'unknown');
        if (!stats[deviceKey]) {
          stats[deviceKey] = {
            count: 0,
            latestAlarm: alarm
          };
        }
        stats[deviceKey].count += 1;
      });
      return Object.keys(stats)
        .map((key) => ({
          key,
          count: stats[key].count,
          latestAlarm: stats[key].latestAlarm || null,
          label: this.deviceNameMap[key] || `设备#${key}`
        }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 6);
    },

    gasKeys() {
      const keys = (this.gasRegistry || []).map((item) => item.key).filter(Boolean);
      return keys.length ? keys : ['C3H8', 'C2H2', 'CO2', 'HCN', 'O2', 'AR', 'H2S'];
    },

    gasDeviceOptions() {
      return Object.keys(this.localGasRealtime).map(id => {
        const d = this.localGasRealtime[id];
        const name = (d && d.device_name) || this.deviceNameMap[String(id)] || `设备${id}`;
        return { id, name };
      });
    },

    localGasChartOption() {
      const gasKeys = this.gasKeys;
      const allMap = this.localGasRealtime || {};
      const thresholds = this.localGasThreshold || {};

      // 单设备：条形图展示实时值 vs 阈值
      if (this.selectedGasDeviceId && allMap[this.selectedGasDeviceId]) {
        const row = allMap[this.selectedGasDeviceId];
        const thr = thresholds[this.selectedGasDeviceId] || {};
        const actuals = gasKeys.map(k => { const v = parseFloat(row[k]); return isNaN(v) ? 0 : parseFloat(v.toFixed(1)); });
        const thrVals = gasKeys.map(k => { const v = parseFloat(thr[k]); return isNaN(v) ? null : v; });
        return {
          color: ['#4bb8ff', '#ff6b6b'],
          tooltip: { trigger: 'axis' },
          legend: { bottom: 0, itemWidth: 12, itemHeight: 6, textStyle: { color: '#b8d8e8', fontSize: 9 } },
          grid: { left: 36, right: 12, top: 18, bottom: 42 },
          xAxis: { type: 'category', data: gasKeys, axisLabel: { color: '#d9fbff', fontSize: 10 }, axisLine: { lineStyle: { color: 'rgba(, , , 0.35)' } } },
          yAxis: { type: 'value', axisLabel: { color: '#b8d8e8' }, splitLine: { lineStyle: { color: 'rgba(, , , 0.35)' } } },
          series: [
            { name: '实时值', type: 'bar', data: actuals, barWidth: 14, itemStyle: { borderRadius: [4, 4, 0, 0] } },
            { name: '阈值', type: 'line', data: thrVals, lineStyle: { color: '#ff6b6b', type: 'dashed' }, symbolSize: 6, itemStyle: { color: '#ff6b6b' } }
          ]
        };
      }

      // 全部设备：雷达图（max/P95/中位数）
      const rows = Object.values(allMap);
      const valuesByKey = {};
      const maxValues = {};
      const p95Values = {};
      const medianValues = {};
      gasKeys.forEach(k => { valuesByKey[k] = []; });
      rows.forEach(row => {
        gasKeys.forEach(k => { const v = parseFloat(row && row[k]); if (!isNaN(v)) valuesByKey[k].push(v); });
      });
      gasKeys.forEach(k => {
        const sorted = valuesByKey[k].slice().sort((a, b) => a - b);
        const n = sorted.length;
        maxValues[k] = n ? sorted[n - 1] : 0;
        p95Values[k] = n ? sorted[Math.floor((n - 1) * 0.95)] : 0;
        medianValues[k] = n ? sorted[Math.floor((n - 1) * 0.5)] : 0;
      });
      const thresholdRows = Object.values(thresholds);
      const indicatorMaxes = gasKeys.reduce((acc, k) => {
        let tMax = 0;
        thresholdRows.forEach(r => { const v = parseFloat(r && r[k]); if (!isNaN(v)) tMax = Math.max(tMax, v); });
        acc[k] = Math.max(Math.max(tMax, maxValues[k]) * 1.2, 10);
        return acc;
      }, {});
      return {
        color: ['#ff6b6b', '#ffd166', '#4bb8ff'],
        tooltip: {},
        legend: { bottom: 0, itemWidth: 12, itemHeight: 6, textStyle: { color: '#b8d8e8', fontSize: 9 } },
        radar: {
          radius: '62%',
          indicator: gasKeys.map(k => ({ name: k, max: indicatorMaxes[k] })),
          axisName: { color: '#d9fbff' },
          splitLine: { lineStyle: { color: 'rgba(, , , 0.35)' } },
          splitArea: { areaStyle: { color: ['rgba(, , , 0.35)', 'rgba(, , , 0.35)'] } },
          axisLine: { lineStyle: { color: 'rgba(, , , 0.35)' } }
        },
        series: [{ type: 'radar', data: [
          { value: gasKeys.map(k => maxValues[k]), name: '最大值', lineStyle: { color: '#ff6b6b', width: 2 }, itemStyle: { color: '#ff6b6b' }, areaStyle: { color: 'rgba(255,107,107,0.14)' } },
          { value: gasKeys.map(k => p95Values[k]), name: 'P95', lineStyle: { color: '#ffd166', width: 2 }, itemStyle: { color: '#ffd166' }, areaStyle: { color: 'rgba(255,209,102,0.12)' } },
          { value: gasKeys.map(k => medianValues[k]), name: '中位数', lineStyle: { color: '#4bb8ff', width: 2 }, itemStyle: { color: '#4bb8ff' }, areaStyle: { color: 'rgba(, , , 0.35)' } }
        ]}]
      };
    },


    normalizedRealtimeGasMap() {
      const raw = this.realtimeGasData || {};
      if (raw && typeof raw === 'object' && raw.data && typeof raw.data === 'object' && !Array.isArray(raw.data)) {
        return raw.data;
      }
      return raw && typeof raw === 'object' ? raw : {};
    },

    normalizedGasThresholdMap() {
      const raw = this.gasThreshold || {};
      if (raw && typeof raw === 'object' && raw.data && typeof raw.data === 'object' && !Array.isArray(raw.data)) {
        return raw.data;
      }
      return raw && typeof raw === 'object' ? raw : {};
    },

    gasOverLimitDevices() {
      const output = [];
      const allMap = this.localGasRealtime || {};
      const threshold = this.localGasThreshold || {};
      const targetIds = this.selectedGasDeviceId
        ? (allMap[this.selectedGasDeviceId] ? [this.selectedGasDeviceId] : [])
        : Object.keys(allMap);

      targetIds.forEach((deviceId) => {
        const row = allMap[deviceId] || {};
        const limit = threshold[deviceId] || threshold[String(deviceId)] || {};
        let count = 0;
        this.gasKeys.forEach((key) => {
          const value = parseFloat(row[key]);
          if (Number.isNaN(value)) return;
          // O2 使用 O2_max 和 O2_min 判断
          if (key === 'O2') {
            const o2Max = parseFloat(limit['O2_max']);
            const o2Min = parseFloat(limit['O2_min']);
            if (!Number.isNaN(o2Max) && value > o2Max) count += 1;
            if (!Number.isNaN(o2Min) && value < o2Min) count += 1;
          } else {
            const target = parseFloat(limit[key]);
            if (Number.isNaN(target)) return;
            if (value > target) count += 1;
          }
        });
        if (count > 0) {
          output.push({
            deviceId,
            count,
            label: (row.device_name) || this.deviceNameMap[String(deviceId)] || `设备#${deviceId}`
          });
        }
      });

      return output.sort((a, b) => b.count - a.count).slice(0, 6);
    },

    localGasAlertCount() {
      const allMap = this.localGasRealtime || {};
      const threshold = this.localGasThreshold || {};
      const targetIds = this.selectedGasDeviceId
        ? (allMap[this.selectedGasDeviceId] ? [this.selectedGasDeviceId] : [])
        : Object.keys(allMap);
      let count = 0;
      targetIds.forEach((deviceId) => {
        const row = allMap[deviceId] || {};
        const limit = threshold[deviceId] || threshold[String(deviceId)] || {};
        this.gasKeys.forEach((key) => {
          const value = parseFloat(row[key]);
          if (Number.isNaN(value)) return;
          // O2 使用 O2_max 和 O2_min 判断
          if (key === 'O2') {
            const o2Max = parseFloat(limit['O2_max']);
            const o2Min = parseFloat(limit['O2_min']);
            if (!Number.isNaN(o2Max) && value > o2Max) count += 1;
            if (!Number.isNaN(o2Min) && value < o2Min) count += 1;
          } else {
            const target = parseFloat(limit[key]);
            if (Number.isNaN(target)) return;
            if (value > target) count += 1;
          }
        });
      });
      return count;
    },

    runtimeDevices() {
      // runtimeOffset 每秒+1，仅作为触发 computed 重新求值的驱动力
      // eslint-disable-next-line no-unused-vars
      const _tick = this.runtimeOffset;
      const now = Date.now();
      return this.allDevices
        .filter((device) => device.is_online)
        .map((device) => {
          const id = String(device.device_id ?? '');
          // 用 online_since 计算本次在线时长（秒），而非累计值
          const onlineSince = device.online_since ? new Date(device.online_since).getTime() : 0;
          const seconds = onlineSince > 0 ? Math.floor((now - onlineSince) / 1000) : 0;
          return {
            id,
            label: device.label,
            seconds: Math.max(0, seconds)
          };
        })
        .filter((item) => item.id && item.seconds > 0)
        .sort((a, b) => b.seconds - a.seconds)
        .slice(0, 12);
    },

    runtimeChartOption() {
      const labels = this.runtimeDevices.map((item) => item.label);
      const values = this.runtimeDevices.map((item) => Math.max(1, Math.round(item.seconds / 60)));

      return {
        color: ['#72cfff'],
        tooltip: {
          trigger: 'axis',
          formatter: (params) => {
            const item = params && params[0];
            const row = this.runtimeDevices[item?.dataIndex ?? -1];
            return row ? `${row.label}<br/>运行时长：${this.formatRuntime(row.seconds)}` : '';
          }
        },
        grid: { left: 70, right: 30, top: 18, bottom: 26 },
        xAxis: {
          type: 'value',
          minInterval: 1,
          axisLabel: { color: '#b7dcf7', formatter: '{value}分' },
          splitLine: { lineStyle: { color: 'rgba(, , , 0.35)' } }
        },
        yAxis: {
          type: 'category',
          data: labels,
          axisLabel: { color: '#b8d8e8', fontSize: 10 },
          axisLine: { lineStyle: { color: 'rgba(, , , 0.35)' } }
        },
        series: [{
          type: 'bar',
          barWidth: 12,
          data: values,
          itemStyle: {
            borderRadius: [0, 8, 8, 0],
            color: '#4bb8ff'
          },
          label: {
            show: true,
            position: 'right',
            color: '#eaf7ff',
            formatter: (params) => {
              const row = this.runtimeDevices[params.dataIndex];
              return row ? this.formatRuntime(row.seconds) : '';
            }
          }
        }]
      };
    },

    onlineTrendOption() {
      const labels = this.trendSamples.map((item) => item.time);
      const online = this.trendSamples.map((item) => item.online);
      const total = this.trendSamples.map((item) => item.total);

      return {
        color: ['#4bb8ff', '#6b7f95'],
        tooltip: { trigger: 'axis' },
        legend: {
          bottom: 4,
          itemWidth: 12,
          itemHeight: 6,
          textStyle: { color: '#b8d8e8', fontSize: 10 }
        },
        grid: { left: 34, right: 10, top: 20, bottom: 56 },
        xAxis: {
          type: 'category',
          data: labels.length ? labels : ['--'],
          axisLabel: { color: '#b7dcf7', fontSize: 10, margin: 14 },
          axisLine: { lineStyle: { color: 'rgba(, , , 0.35)' } }
        },
        yAxis: {
          type: 'value',
          min: 0,
          minInterval: 1,
          axisLabel: { color: '#b7dcf7', fontSize: 10 },
          splitLine: { lineStyle: { color: 'rgba(, , , 0.35)' } }
        },
        series: [
          {
            name: '在线设备',
            type: 'line',
            smooth: true,
            symbolSize: 5,
            areaStyle: { color: 'rgba(, , , 0.35)' },
            data: online.length ? online : [0]
          },
          {
            name: '设备总数',
            type: 'line',
            smooth: true,
            symbolSize: 4,
            lineStyle: { type: 'dashed' },
            data: total.length ? total : [0]
          }
        ]
      };
    }
  },
  methods: {
    /** 从父组件 props 同步气体数据到本地 */
    syncGasFromProps() {
      if (this.realtimeGasData && typeof this.realtimeGasData === 'object') {
        this.localGasRealtime = { ...this.realtimeGasData };
      }
      if (this.gasThreshold && typeof this.gasThreshold === 'object') {
        this.localGasThreshold = { ...this.gasThreshold };
      }
      if (this.gasRegistry && this.gasRegistry.length > 0) {
        this.localGasRegistry = [...this.gasRegistry];
      }
    },

    async fetchAlarmTypeStats() {
      this.alarmTypeStatsError = null;
      const result = await alarmReviewApi.getTypeStats(this.alarmTypeRange);
      console.log('[CockpitOverviewPage] type_stats result:', JSON.stringify(result));
      if (!result.error && result.data && Array.isArray(result.data.data)) {
        this.alarmTypeStatsData = result.data.data;
      } else {
        console.error('[CockpitOverviewPage] type_stats failed:', result);
        this.alarmTypeStatsError = result.message || (result.error ? '接口请求失败' : '数据格式异常');
        this.alarmTypeStatsData = [];
      }
    },

    setAlarmTypeRange(range) {
      this.alarmTypeRange = range;
      this.fetchAlarmTypeStats();
    },


    formatRuntime(seconds) {
      const safeSeconds = Math.max(0, Number(seconds) || 0);
      const hours = Math.floor(safeSeconds / 3600);
      const minutes = Math.floor((safeSeconds % 3600) / 60);
      if (hours > 0) return `${hours}小时${minutes}分`;
      return `${Math.max(1, minutes)}分钟`;
    },

    openTopAlarmModal(item) {
      const normalizedId = String(item?.key ?? '').trim();
      if (!normalizedId) return;
      this.$emit('open-alarm-modal', {
        deviceId: normalizedId,
        alarm: item?.latestAlarm || null
      });
    },

    locateDevice(deviceId) {
      const normalizedId = String(deviceId ?? '').trim();
      if (!normalizedId) return;
      this.$emit('locate-device', normalizedId);
    }
  }
};
</script>

<style scoped>
.cockpit-page {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 8px 12px 12px; /* Adding some padding to the outer shell */
  box-sizing: border-box;
}

.dashboard-grid {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 25% 1fr 25%;
  gap: 20px;
}

.col-left,
.col-right {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: 0;
}

.col-center {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: 0;
}

.kpi-strip {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 20px;
  flex-shrink: 0;
}

.kpi-card {
  border: 1px solid rgba(186, 230, 253, 0.48);
  background: linear-gradient(180deg, rgba(52, 118, 173, 0.76), rgba(31, 86, 136, 0.82));
  box-shadow: inset 0 0 20px rgba(46, 168, 255, 0.18);
  padding: 16px 20px;
  border-radius: 8px; /* Cohere style sm radius */
}

.kpi-card.highlight {
  border-color: rgba(102, 199, 255, 0.92);
}

.kpi-card.warning {
  border-color: rgba(255, 184, 77, 0.45);
}

.kpi-label {
  display: block;
  color: #7ea7bb; /* Softer text color */
  font-size: 13px;
}

.kpi-value {
  display: block;
  margin-top: 6px;
  color: #e8fbff;
  font-size: 32px;
  font-weight: 300; /* Lighter font weight for modern look */
  line-height: 1.1;
}

.sub-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.panel-card {
  min-height: 0;
  border: 1px solid rgba(186, 230, 253, 0.42);
  background: linear-gradient(180deg, rgba(44, 103, 156, 0.80), rgba(25, 74, 121, 0.86));
  box-shadow: inset 0 0 16px rgba(46, 168, 255, 0.16);
  padding: 20px; /* Increased padding */
  border-radius: 8px; /* Cohere style sm radius */
  display: flex;
  flex-direction: column;
}

.chart-wrapper {
  flex: 1;
  min-height: 0;
  width: 100%;
}

.flex-grow {
  flex: 1;
}

.panel-title {
  color: #eaf7ff;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 1px;
  margin-bottom: 16px; /* Increased margin */
  flex-shrink: 0;
}

.rank-list {
  display: flex;
  flex-direction: column;
  gap: 10px; /* Increased gap */
  flex: 1;
  overflow: auto;
}

.rank-row {
  display: grid;
  grid-template-columns: 46px 1fr auto;
  gap: 12px;
  align-items: center;
  padding: 10px 12px; /* Increased padding */
  border: 1px solid rgba(186, 230, 253, 0.42); /* Softer border */
  background: rgba(32, 90, 142, 0.42); /* Softer background */
  border-radius: 6px;
}

.rank-row.clickable {
  cursor: pointer;
  transition: border-color 0.2s ease, transform 0.2s ease, background 0.2s ease;
}

.rank-row.clickable:hover {
  border-color: rgba(114, 207, 255, 0.95);
  background: rgba(78, 182, 245, 0.30);
  transform: translateX(2px);
}

.rank-index {
  color: #4bb8ff;
  font-family: 'Courier New', Courier, monospace;
  font-size: 14px;
}

.rank-name {
  color: #cde7f2;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
}

.rank-value {
  color: #ffcf7a;
  font-size: 14px;
}

.empty-text {
  color: #7ea7bb;
  font-size: 13px;
  padding: 8px 0;
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #7ea7bb;
  border: 1px dashed rgba(186, 230, 253, 0.42);
  background: rgba(36, 95, 146, 0.30);
  font-size: 14px;
  border-radius: 6px;
}

/* media query 已移除 — 使用 scale 方案后页面始终按 1920×1080 渲染 */

/* ========== 场地报警概览 ========== */
.area-alarm-card {
  height: 280px;
  flex-shrink: 0;
}

.area-alarm-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.area-no-alarm {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #00dc78;
  font-size: 14px;
  gap: 8px;
}

.area-ok-icon {
  font-size: 18px;
  font-weight: 700;
}

.area-alarm-row {
  display: grid;
  grid-template-columns: 36px 1fr auto;
  gap: 10px;
  align-items: center;
  padding: 10px 12px;
  background: rgba(255, 80, 80, 0.08);
  border: 1px solid rgba(255, 80, 80, 0.35);
  border-radius: 6px;
  animation: area-alarm-pulse 2s ease-in-out infinite;
}

@keyframes area-alarm-pulse {
  0%, 100% { border-color: rgba(255, 80, 80, 0.30); }
  50%       { border-color: rgba(255, 80, 80, 0.70); }
}

.area-rank  { color: #ff7070; font-family: 'Courier New', monospace; font-size: 13px; }
.area-name  { color: #e8f6ff; font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.area-count { color: #ff9090; font-size: 14px; font-weight: 600; white-space: nowrap; }
/* ========== 报警类别统计标题行 ========== */
.panel-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  flex-shrink: 0;
}

.panel-title-row .panel-title {
  margin-bottom: 0;
}

.range-tabs {
  display: flex;
  gap: 4px;
}

.range-tab {
  padding: 3px 10px;
  font-size: 12px;
  font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
  border: 1px solid rgba(186, 230, 253, 0.46);
  border-radius: 4px;
  background: rgba(42, 102, 154, 0.20);
  color: #7ea7bb;
  cursor: pointer;
  transition: all 0.2s;
}

.range-tab:hover {
  border-color: rgba(102, 199, 255, 0.92);
  color: #b8d8e8;
}

.range-tab.active {
  background: rgba(75, 184, 255, 0.26);
  border-color: #72cfff;
  color: #d9f3ff;
}

.stats-error-tip {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #ff8080;
  font-size: 12px;
  padding: 8px;
  text-align: center;
}

/* ========== 气体设备选择器 ========== */
.gas-dev-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.gas-dev-tab {
  padding: 2px 9px;
  font-size: 11px;
  font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
  border: 1px solid rgba(186, 230, 253, 0.46);
  border-radius: 12px;
  background: rgba(42, 102, 154, 0.20);
  color: #7ea7bb;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.gas-dev-tab:hover {
  border-color: rgba(102, 199, 255, 0.92);
  color: #b8d8e8;
}

.gas-dev-tab.active {
  background: rgba(75, 184, 255, 0.26);
  border-color: #72cfff;
  color: #d9f3ff;
  font-weight: 600;
}

</style>

