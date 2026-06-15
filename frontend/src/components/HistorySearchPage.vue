<template>
  <div class="history-page">
    <div class="history-page-header">
      <h2>历史记录查询</h2>
      <div class="header-tip">最近 24 小时已自动查询，可继续筛选</div>
    </div>

    <div class="search-form">
      <div class="form-row">
        <div class="form-group">
          <!-- 摄像头序号 = alarm.device_id -->
          <label>摄像头序号</label>
          <select v-model="searchParams.idx">
            <option value="">全部</option>
            <option v-for="id in filterOptions.idx" :key="id" :value="id">{{ id }}</option>
          </select>
        </div>

        <div class="form-group">
          <!-- 安全类别 = alarm.type2，例如"安全文明着装" -->
          <label>安全类别</label>
          <select v-model="searchParams.type2">
            <option value="">全部</option>
            <option v-for="cat in filterOptions.categories" :key="cat" :value="cat">{{ cat }}</option>
          </select>
        </div>

        <div class="form-group">
          <!-- 报警描述 = alarm.type，例如"没有安全帽" -->
          <label>报警描述</label>
          <select v-model="searchParams.type">
            <option value="">全部</option>
            <option v-for="desc in filterOptions.descriptions" :key="desc" :value="desc">{{ desc }}</option>
          </select>
        </div>

        <div class="form-group">
          <!-- 设备负责人 = device.responsible_person -->
          <label>设备负责人</label>
          <select v-model="searchParams.owner">
            <option value="">全部</option>
            <option v-for="owner in filterOptions.owners" :key="owner" :value="owner">{{ owner }}</option>
          </select>
        </div>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label>开始时间</label>
          <input type="datetime-local" v-model="searchParams.start_time" />
        </div>
        <div class="form-group">
          <label>结束时间</label>
          <input type="datetime-local" v-model="searchParams.end_time" />
        </div>
      </div>

      <div class="form-actions">
        <button class="btn btn-primary" @click="performSearch">查询</button>
        <button class="btn btn-secondary" @click="resetSearch">重置</button>
        <button class="btn btn-success" @click="exportResults" :disabled="results.length === 0">导出 CSV</button>
      </div>
    </div>

    <div class="search-results">
      <div class="results-header">
        <h3>查询结果（共 {{ totalCount }} 条）</h3>
        <div class="header-actions">
          <label class="select-all-label" v-if="results.length > 0">
            <input type="checkbox" :checked="isAllSelected" @change="toggleSelectAll" />
            全选
          </label>
          <button
            class="btn btn-danger btn-batch-delete"
            :disabled="selectedCount === 0"
            @click="batchDelete"
          >
            批量删除{{ selectedCount > 0 ? '(' + selectedCount + ')' : '' }}
          </button>
        </div>
      </div>

      <div class="results-container">
        <div v-if="loading" class="loading">加载中...</div>
        <div v-else-if="results.length === 0" class="no-data">暂无数据</div>
        <div v-else class="results-list">
          <div
            v-for="(item, index) in results"
            :key="index"
            class="result-item"
            @click="showDetail(item)"
          >
            <div class="item-checkbox" @click.stop>
              <input
                type="checkbox"
                :checked="isItemSelected(item)"
                @change="toggleSelectItem(item)"
              />
            </div>
            <div class="item-image" v-if="item.image">
              <img :src="item.image" alt="报警图片" :style="alarmImageStyle(item)" />
            </div>
            <div class="item-info">
              <!-- idx = alarm.device_id（摄像头序号） -->
              <p><strong>摄像头序号:</strong> {{ item.idx }}</p>
              <!-- note = alarm.note（边缘端上报，通常为作业场地名） -->
              <p><strong>作业场地:</strong> {{ item.note }}</p>
              <!-- type2 = alarm.type2（安全类别） -->
              <p><strong>安全类别:</strong> {{ item.type2 }}</p>
              <!-- type = alarm.type（具体报警描述） -->
              <p><strong>报警描述:</strong> {{ item.type }}</p>
              <!-- device_manager = device.responsible_person（设备负责人） -->
              <p><strong>设备负责人:</strong> {{ item.device_manager }}</p>
              <!-- area_manager = device.area_manager（区域负责人） -->
              <p><strong>区域负责人:</strong> {{ item.area_manager }}</p>
              <p><strong>负责人电话:</strong> {{ item.area_manager_phone }}</p>
              <p><strong>报警时间:</strong> {{ item.alarm_time }}</p>
              <p>
                <strong>复核状态:</strong>
                <span :class="['review-badge', reviewStatusClass(item.review_status)]">
                  {{ reviewStatusLabel(item.review_status) }}
                </span>
              </p>
            </div>
            <div class="item-actions" @click.stop>
              <button class="btn btn-danger btn-inline-delete" @click="deleteItemDirect(item)">删除</button>

            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 分页器 -->
    <div class="pagination-bar" v-if="totalPages > 1">
      <button class="page-btn" :disabled="currentPage <= 1" @click="goToPage(1)">首页</button>
      <button class="page-btn" :disabled="currentPage <= 1" @click="goToPage(currentPage - 1)">上一页</button>
      <template v-for="p in visiblePages" :key="p">
        <span v-if="p === '...'" class="page-ellipsis">...</span>
        <button
          v-else
          class="page-btn"
          :class="{ active: p === currentPage }"
          @click="goToPage(p)"
        >{{ p }}</button>
      </template>
      <button class="page-btn" :disabled="currentPage >= totalPages" @click="goToPage(currentPage + 1)">下一页</button>
      <button class="page-btn" :disabled="currentPage >= totalPages" @click="goToPage(totalPages)">末页</button>
      <span class="page-info">第 {{ currentPage }}/{{ totalPages }} 页</span>
    </div>

    <div v-if="showDetailModal" class="detail-modal" @click.self="closeDetailModal">
      <div class="detail-content">
        <button class="close-btn" @click="closeDetailModal">&times;</button>
        <div class="detail-image" v-if="selectedItem.image">
          <img :src="selectedItem.image" alt="报警图片" :style="alarmImageStyle(selectedItem)" />
        </div>
        <div class="detail-info">
          <p><strong>摄像头序号:</strong> {{ selectedItem.idx }}</p>
          <p><strong>作业场地:</strong> {{ selectedItem.note }}</p>
          <p><strong>安全类别:</strong> {{ selectedItem.type2 }}</p>
          <p><strong>报警描述:</strong> {{ selectedItem.type }}</p>
          <p><strong>设备负责人:</strong> {{ selectedItem.device_manager }}</p>
          <p><strong>区域负责人:</strong> {{ selectedItem.area_manager }}</p>
          <p><strong>负责人电话:</strong> {{ selectedItem.area_manager_phone }}</p>
          <p><strong>报警时间:</strong> {{ selectedItem.alarm_time }}</p>
          <p>
            <strong>复核状态:</strong>
            <span :class="['review-badge', reviewStatusClass(selectedItem.review_status)]">
              {{ reviewStatusLabel(selectedItem.review_status) }}
            </span>
          </p>
        </div>
        <div class="detail-actions">
          <button class="btn btn-warning" @click="reportIssue">报错检索信息</button>
          <button class="btn btn-danger" @click="deleteRecord">删除记录</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import { getBaseUrl, alarmReviewApi } from '@/services/api';

export default {
  name: 'HistorySearchPage',
  props: {
    persons: {
      type: Array,
      default: () => []
    }
  },
  computed: {
    totalPages() {
      return Math.max(1, Math.ceil(this.totalCount / this.pageSize));
    },
    selectedCount() {
      return this.selectedIds.size;
    },
    isAllSelected() {
      return this.results.length > 0 && this.results.every(item => this.isItemSelected(item));
    },
    visiblePages() {
      const total = this.totalPages;
      const cur = this.currentPage;
      if (total <= 7) {
        return Array.from({ length: total }, (_, i) => i + 1);
      }
      const pages = [];
      pages.push(1);
      if (cur > 3) pages.push('...');
      const start = Math.max(2, cur - 1);
      const end = Math.min(total - 1, cur + 1);
      for (let i = start; i <= end; i++) pages.push(i);
      if (cur < total - 2) pages.push('...');
      pages.push(total);
      return pages;
    },
    /**
     * 设备旋转角度映射 { device_id: rotation }
     * 用于告警图片根据设备倒装配置旋转显示
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
  data() {
    return {
      searchParams: {
        idx: '',
        type: '',
        type2: '',
        owner: '',
        start_time: '',
        end_time: ''
      },
      results: [],
      totalCount: 0,
      loading: false,
      currentPage: 1,
      pageSize: 12,
      selectedIds: new Set(),
      showDetailModal: false,
      selectedItem: {},
      wifiIpAddress: window.location.hostname,
      refreshTimer: null,
      filterOptions: {
        idx: [],
        categories: [],
        descriptions: [],
        owners: [],
      },
    };
  },
  mounted() {
    this.loadFilterOptions();
    this.performSearch();
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

    async loadFilterOptions() {
      const result = await alarmReviewApi.getFilterOptions();
      if (!result.error && result.data) {
        this.filterOptions = {
          idx: result.data.idx || [],
          categories: result.data.categories || [],
          descriptions: result.data.descriptions || [],
          owners: result.data.owners || [],
        };
      }
    },

    toDatetimeLocal(date) {
      const y = date.getFullYear();
      const m = String(date.getMonth() + 1).padStart(2, '0');
      const d = String(date.getDate()).padStart(2, '0');
      const hh = String(date.getHours()).padStart(2, '0');
      const mm = String(date.getMinutes()).padStart(2, '0');
      return `${y}-${m}-${d}T${hh}:${mm}`;
    },

    applyLast24HoursWindow() {
      const now = new Date();
      const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
      this.searchParams.start_time = this.toDatetimeLocal(yesterday);
      this.searchParams.end_time = this.toDatetimeLocal(now);
    },

    itemKey(item) {
      return `${item.idx}|${item.alarm_time}`;
    },
    isItemSelected(item) {
      return this.selectedIds.has(this.itemKey(item));
    },
    toggleSelectItem(item) {
      const key = this.itemKey(item);
      if (this.selectedIds.has(key)) {
        this.selectedIds.delete(key);
      } else {
        this.selectedIds.add(key);
      }
      // 触发响应式
      this.selectedIds = new Set(this.selectedIds);
    },
    toggleSelectAll() {
      if (this.isAllSelected) {
        this.selectedIds = new Set();
      } else {
        this.selectedIds = new Set(this.results.map(item => this.itemKey(item)));
      }
    },
    goToPage(page) {
      if (page < 1 || page > this.totalPages) return;
      this.currentPage = page;
      this.selectedIds = new Set();
      this.performSearch(false);
    },
    resetSearch() {
      this.searchParams = {
        idx: '',
        type: '',
        type2: '',
        owner: '',
        start_time: '',
        end_time: ''
      };
      this.results = [];
      this.totalCount = 0;
      this.currentPage = 1;
      this.selectedIds = new Set();
    },


        async silentRefresh() {
      // 弹窗打开时跳过，避免干扰用户操作
      if (this.showDetailModal) return;
      try {
        const params = { page: this.currentPage, page_size: this.pageSize };
        if (this.searchParams.idx !== '') params.idx = this.searchParams.idx;
        if (this.searchParams.type) params.type = this.searchParams.type;
        if (this.searchParams.type2) params.type2 = this.searchParams.type2;
        if (this.searchParams.owner) params.owner = this.searchParams.owner;
        if (this.searchParams.start_time) {
          params.start_time = this.searchParams.start_time.replace('T', ' ') + ':00';
        }
        if (this.searchParams.end_time) {
          params.end_time = this.searchParams.end_time.replace('T', ' ') + ':00';
        }
        const response = await axios.get(
          `${getBaseUrl()}/alarms/search_history`,
          { params }
        );
        if (response.data && response.data.data) {
          this.results = response.data.data;
          this.totalCount = response.data.count;
          // 若当前页已超出总页数，回退到最后一页
          if (this.currentPage > this.totalPages) {
            this.currentPage = this.totalPages;
          }
        }
      } catch {
        // 静默刷新失败不弹提示
      }
    },


    async performSearch(resetPage = true) {
      this.loading = true;
      if (resetPage) {
        this.currentPage = 1;
        this.selectedIds = new Set();
      }
      try {
        const params = { page: this.currentPage, page_size: this.pageSize };
        if (this.searchParams.idx !== '') params.idx = this.searchParams.idx;
        if (this.searchParams.type) params.type = this.searchParams.type;
        if (this.searchParams.type2) params.type2 = this.searchParams.type2;
        if (this.searchParams.owner) params.owner = this.searchParams.owner;
        if (this.searchParams.start_time) {
          params.start_time = this.searchParams.start_time.replace('T', ' ') + ':00';
        }
        if (this.searchParams.end_time) {
          params.end_time = this.searchParams.end_time.replace('T', ' ') + ':00';
        }

        const response = await axios.get(
          `${getBaseUrl()}/alarms/search_history`,
          { params }
        );

        if (response.data && response.data.data) {
          this.results = response.data.data;
          this.totalCount = response.data.count;
          // page/page_size 来自服务端，同步本地
          if (response.data.page) this.currentPage = response.data.page;
          if (response.data.page_size) this.pageSize = response.data.page_size;
          // 若当前页超出总页数，回退
          if (this.currentPage > this.totalPages) {
            this.currentPage = this.totalPages;
            if (this.totalPages > 0) return this.performSearch(false);
          }
        } else {
          this.results = [];
          this.totalCount = 0;
        }
      } catch (error) {
        console.error('查询历史记录失败:', error);
        alert('查询失败，请稍后重试');
      } finally {
        this.loading = false;
      }
    },

    showDetail(item) {
      this.selectedItem = item;
      this.showDetailModal = true;
    },

    closeDetailModal() {
      this.showDetailModal = false;
      this.selectedItem = {};
    },

    async reportIssue() {
      const reason = prompt('请输入报错原因（可选）:');
      try {
        await axios.post(`${getBaseUrl()}/alarms/report_search_issue`, {
          record: this.selectedItem,
          reason: reason || ''
        });
        alert('报错信息已提交');
        this.closeDetailModal();
      } catch (error) {
        console.error('提交报错信息失败:', error);
        alert('提交失败，请稍后重试');
      }
    },


    async deleteItemDirect(item) {
      if (!confirm('确定要删除这条记录吗？\n删除后将无法恢复，包括对应的图片文件。')) return;
      try {
        const response = await axios.post(
          `${getBaseUrl()}/alarms/delete_history_record`,
          { alarm_id: item.alarm_id, idx: item.idx, alarm_time: item.alarm_time, img: item.img || '' }
        );
        if (response.data.status === 'success') {
          alert('删除成功');
          this.selectedIds.delete(this.itemKey(item));
          this.$emit('alarm-deleted');
          // 重新加载当前页
          await this.performSearch(false);
        } else if (response.data.status === 'not_found') {
          alert('记录未找到，可能已被删除');
          await this.performSearch(false);
        } else {
          alert(`删除失败: ${response.data.message || '未知错误'}`);
        }
      } catch (error) {
        console.error('删除记录失败:', error);
        alert('删除失败，请稍后重试');
      }
    },

        reviewStatusLabel(status) {
      if (status === 1) return '误报警';
      if (status === 2) return '确定报警';
      return '未复核';
    },

    reviewStatusClass(status) {
      if (status === 1) return 'badge-false-alarm';
      if (status === 2) return 'badge-real-alarm';
      return 'badge-pending';
    },

    async deleteRecord() {
      if (!confirm('确定要删除这条记录吗？\n删除后将无法恢复，包括对应的图片文件。')) {
        return;
      }

      try {
        const response = await axios.post(
          `${getBaseUrl()}/alarms/delete_history_record`,
          {
            alarm_id: this.selectedItem.alarm_id,
            idx: this.selectedItem.idx,
            alarm_time: this.selectedItem.alarm_time,
            img: this.selectedItem.img
          }
        );

        if (response.data.status === 'success') {
          alert('删除成功');
          this.selectedIds.delete(this.itemKey(this.selectedItem));
          this.closeDetailModal();
          // 重新加载当前页
          await this.performSearch(false);
        } else if (response.data.status === 'not_found') {
          alert('记录未找到，可能已被删除');
          this.closeDetailModal();
          await this.performSearch(false);
        } else {
          alert(`删除失败: ${response.data.message || '未知错误'}`);
        }
      } catch (error) {
        console.error('删除记录失败:', error);
        alert('删除失败，请稍后重试');
      }
    },

    async batchDelete() {
      if (this.selectedCount === 0) return;
      if (!confirm(`确定要删除选中的 ${this.selectedCount} 条记录吗？\n删除后将无法恢复，包括对应的图片文件。`)) return;

      // 从当前 results 中找出选中的记录
      const toDelete = this.results.filter(item => this.isItemSelected(item));
      const records = toDelete.map(item => ({
        alarm_id: item.alarm_id,
        idx: item.idx,
        alarm_time: item.alarm_time,
        img: item.img || ''
      }));

      try {
        const response = await axios.post(
          `${getBaseUrl()}/alarms/batch_delete_history_records`,
          { records }
        );
        if (response.data.status === 'success') {
          alert(`删除成功: ${response.data.deleted} 条记录，${response.data.images_deleted || 0} 张图片`);
          this.selectedIds = new Set();
          // 重新加载当前页
          await this.performSearch(false);
        } else {
          alert(`删除失败: ${response.data.message || '未知错误'}`);
        }
      } catch (error) {
        console.error('批量删除失败:', error);
        alert('批量删除失败，请稍后重试');
      }
    },

    async exportResults() {
      if (this.results.length === 0) {
        alert('没有可导出的数据');
        return;
      }

      try {
        const response = await axios.post(
          `${getBaseUrl()}/alarms/export_search_results_csv`,
          { records: this.results },
          { responseType: 'blob' }
        );

        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `历史记录_${new Date().getTime()}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      } catch (error) {
        console.error('导出CSV失败:', error);
        alert('导出失败，请稍后重试');
      }
    }
  }
};
</script>

<style scoped>
.history-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  border: 1px solid rgba(186, 230, 253, 0.46);
  background: linear-gradient(180deg, rgba(56, 122, 176, 0.76), rgba(32, 88, 136, 0.84));
  box-shadow: inset 0 0 24px rgba(46, 168, 255, 0.16), 0 0 16px rgba(0, 0, 0, 0.18);
}

.history-page-header {
  padding: 14px 18px 10px;
  border-bottom: 1px solid rgba(186, 230, 253, 0.38);
}

.history-page-header h2 {
  margin: 0;
  color: #e8fbff;
  font-size: 22px;
  letter-spacing: 1px;
}

.header-tip {
  margin-top: 6px;
  color: #b7dcf7;
  font-size: 12px;
}

.search-form {
  padding: 14px 16px;
  border-bottom: 1px solid rgba(186, 230, 253, 0.36);
  background: rgba(34, 92, 142, 0.34);
}

.form-row {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.form-row:last-child {
  margin-bottom: 0;
}

.form-group {
  flex: 1;
  min-width: 200px;
  display: flex;
  flex-direction: column;
}

.form-group label {
  margin-bottom: 6px;
  color: #b7dcf7;
  font-size: 13px;
}

.form-group select,
.form-group input {
  height: 36px;
  padding: 0 10px;
  color: #e8fbff;
  border: 1px solid rgba(186, 230, 253, 0.48);
  background: rgba(22, 66, 108, 0.72);
  border-radius: 4px;
}

.form-group select:focus,
.form-group input:focus {
  outline: none;
  border-color: rgba(102, 199, 255, 0.94);
  box-shadow: 0 0 0 2px rgba(102, 199, 255, 0.22);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.btn {
  padding: 8px 14px;
  border-radius: 4px;
  border: 1px solid transparent;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
}

.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.btn-primary {
  color: #e8fbff;
  border-color: rgba(102, 199, 255, 0.95);
  background: rgba(75, 184, 255, 0.28);
}

.btn-secondary {
  color: #d7ebf2;
  border-color: rgba(140, 164, 186, 0.35);
  background: rgba(56, 74, 92, 0.45);
}

.btn-success {
  color: #e8fbff;
  border-color: rgba(58, 255, 214, 0.5);
  background: rgba(0, 123, 112, 0.35);
}

.btn-warning {
  color: #fff4d6;
  border-color: rgba(255, 207, 122, 0.45);
  background: rgba(170, 120, 20, 0.35);
}

.btn-danger {
  color: #ffe2e2;
  border-color: rgba(255, 128, 128, 0.45);
  background: rgba(160, 43, 43, 0.38);
}

.search-results {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.results-header {
  padding: 12px 16px;
  border-bottom: 1px solid rgba(186, 230, 253, 0.34);
}

.results-header h3 {
  margin: 0;
  color: #eaf7ff;
  font-size: 16px;
  font-weight: 600;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.select-all-label {
  color: #b7dcf7;
  font-size: 13px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
}

.select-all-label input {
  cursor: pointer;
}

.btn-batch-delete {
  padding: 5px 12px;
  font-size: 12px;
}

.results-container {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 14px;
}

.loading,
.no-data {
  text-align: center;
  padding: 36px;
  color: #b7dcf7;
}

.results-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 12px;
}

.result-item {
  position: relative;
  border: 1px solid rgba(186, 230, 253, 0.46);
  border-radius: 6px;
  overflow: hidden;
  background: rgba(34, 92, 142, 0.46);
  cursor: pointer;
  transition: transform 0.2s ease, border-color 0.2s ease;
}

.result-item:hover {
  transform: translateY(-2px);
  border-color: rgba(102, 199, 255, 0.95);
}

.item-checkbox {
  position: absolute;
  top: 6px;
  left: 6px;
  z-index: 2;
  background: rgba(0, 0, 0, 0.45);
  border-radius: 3px;
  padding: 2px;
}

.item-checkbox input {
  cursor: pointer;
  width: 16px;
  height: 16px;
}

.item-image {
  width: 100%;
  height: 160px;
  background: rgba(20, 52, 84, 0.82);
}

.item-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.item-info {
  padding: 10px;
}

.item-info p {
  margin: 4px 0;
  color: #bdd9e6;
  font-size: 13px;
}

.item-info strong {
  color: #e8fbff;
}

.item-actions {
  padding: 8px 10px;
  border-top: 1px solid rgba(186, 230, 253, 0.34);
  display: flex;
  justify-content: flex-end;
}

.btn-inline-delete {
  padding: 5px 14px;
  font-size: 12px;
}

.review-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
  margin-left: 4px;
}

.badge-pending {
  background: rgba(126, 180, 200, 0.18);
  border: 1px solid rgba(126, 200, 220, 0.4);
  color: #b7dcf7;
}

.badge-false-alarm {
  background: rgba(255, 80, 80, 0.18);
  border: 1px solid rgba(255, 100, 100, 0.5);
  color: #ff9090;
}

.badge-real-alarm {
  background: rgba(80, 255, 120, 0.18);
  border: 1px solid rgba(80, 220, 100, 0.5);
  color: #60e880;
}

/* ── 分页器 ── */
.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 12px 16px;
  border-top: 1px solid rgba(186, 230, 253, 0.34);
  background: rgba(34, 92, 142, 0.28);
}

.page-btn {
  padding: 4px 10px;
  border: 1px solid rgba(186, 230, 253, 0.4);
  background: rgba(34, 92, 142, 0.5);
  color: #b7dcf7;
  border-radius: 3px;
  cursor: pointer;
  font-size: 13px;
}

.page-btn:hover:not(:disabled) {
  border-color: rgba(102, 199, 255, 0.85);
  background: rgba(75, 184, 255, 0.28);
}

.page-btn.active {
  border-color: rgba(102, 199, 255, 0.95);
  background: rgba(75, 184, 255, 0.38);
  color: #e8fbff;
  font-weight: 700;
}

.page-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.page-ellipsis {
  color: #6889a6;
  padding: 0 4px;
}

.page-info {
  margin-left: 10px;
  color: #8bb0cc;
  font-size: 12px;
}

/* ── 弹窗 ── */
.detail-modal {
  position: fixed;
  inset: 0;
  z-index: 1200;
  background: rgba(0, 0, 0, 0.65);
  display: flex;
  align-items: center;
  justify-content: center;
}

.detail-content {
  width: min(900px, 92vw);
  max-height: 88vh;
  overflow: auto;
  position: relative;
  border: 1px solid rgba(186, 230, 253, 0.48);
  border-radius: 8px;
  padding: 18px;
  background: linear-gradient(180deg, rgba(48, 110, 164, 0.92), rgba(28, 80, 128, 0.94));
}

.close-btn {
  position: absolute;
  top: 8px;
  right: 10px;
  border: none;
  background: transparent;
  color: #eaf7ff;
  font-size: 28px;
  cursor: pointer;
}

.detail-image {
  width: 100%;
  margin-bottom: 14px;
}

.detail-image img {
  width: 100%;
  border-radius: 6px;
}

.detail-info p {
  margin: 8px 0;
  color: #bdd9e6;
}

.detail-info strong {
  color: #e8fbff;
  display: inline-block;
  width: 100px;
}

.detail-actions {
  margin-top: 14px;
  display: flex;
  justify-content: center;
  gap: 10px;
}
</style>
