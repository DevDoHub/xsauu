<template>
  <div class="dashboard-chart" :style="{ height }" ref="chartRef"></div>
</template>

<script>
import * as echarts from 'echarts/core';
import { BarChart, LineChart, PieChart, RadarChart } from 'echarts/charts';
import { GridComponent, LegendComponent, RadarComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([
  BarChart, LineChart, PieChart, RadarChart,
  GridComponent, LegendComponent, RadarComponent, TooltipComponent,
  CanvasRenderer,
]);

export default {
  name: 'DashboardChart',
  props: {
    option: { type: Object, required: true, default: () => ({}) },
    height: { type: String, default: '180px' },
  },
  data() {
    return { chart: null };
  },
  watch: {
    // 不用 deep: true — 父组件 computed 已返回新对象引用，浅比较即可触发
    option() { this.renderChart(); },
  },
  mounted() {
    this.$nextTick(() => {
      const dpr = Math.max(window.devicePixelRatio || 1, 2);
      this.chart = echarts.init(this.$refs.chartRef, null, {
        devicePixelRatio: dpr,
        renderer: 'canvas',
      });
      this.renderChart();
      window.addEventListener('resize', this.resizeChart);
    });
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.resizeChart);
    if (this.chart) { this.chart.dispose(); this.chart = null; }
  },
  methods: {
    renderChart() {
      if (!this.chart || !this.option) return;
      // false = merge 模式，增量更新而非全量重绘，大幅减少渲染开销
      this.chart.setOption(this.option, false);
    },
    resizeChart() {
      if (this.chart) this.chart.resize();
    },
  },
};
</script>

<style scoped>
.dashboard-chart { width: 100%; min-height: 120px; }
</style>
