<template>
  <div class="sys-settings-page">
    <div class="ss-header">
      <div class="ss-title">
        <span class="ss-icon">⚙</span>
        系统配置
      </div>
      <div class="ss-meta">
        <span class="ss-badge" :class="saved ? 'badge-ok' : ''">
          {{ saved ? '✔ 已保存' : '' }}
        </span>
      </div>
    </div>

    <!-- 加载中 -->
    <div class="ss-loading" v-if="loading">
      <span>加载配置中…</span>
    </div>

    <!-- 错误提示 -->
    <div class="ss-error" v-if="errorMsg">
      <span>{{ errorMsg }}</span>
      <button class="ss-retry-btn" @click="fetchConfig">重试</button>
    </div>

    <!-- 配置表单 -->
    <div class="ss-card" v-if="!loading && !errorMsg">
      <div class="ss-card-title">服务端参数</div>

      <!-- 解码器模式 -->
      <div class="ss-row">
        <span class="ss-label">H.264 解码器</span>
        <div class="ss-select-group">
          <button
            class="ss-option-btn"
            :class="{ active: form.decoder_hardware_accel === 'cpu' }"
            :disabled="saving"
            @click="form.decoder_hardware_accel = 'cpu'"
          >
            CPU 软解
          </button>
          <button
            class="ss-option-btn"
            :class="{ active: form.decoder_hardware_accel === 'gpu' }"
            :disabled="saving"
            @click="form.decoder_hardware_accel = 'gpu'"
          >
            GPU 硬解
          </button>
        </div>
        <span class="ss-hint">切换后新建的解码会话生效，已有会话需重连设备</span>
      </div>

      <!-- UDP Worker 数 -->
      <div class="ss-row">
        <span class="ss-label">UDP Worker 线程数</span>
        <div class="ss-input-group">
          <button class="ss-adj-btn" :disabled="saving || form.udp_worker_count <= 1" @click="form.udp_worker_count--">−</button>
          <input
            class="ss-input"
            type="number"
            min="1"
            max="32"
            v-model.number="form.udp_worker_count"
            :disabled="saving"
          />
          <button class="ss-adj-btn" :disabled="saving || form.udp_worker_count >= 32" @click="form.udp_worker_count++">+</button>
        </div>
        <span class="ss-hint">建议值：CPU 核数的一半，范围 1-16，重启服务后生效</span>
      </div>

      <!-- 操作按钮 -->
      <div class="ss-actions">
        <button class="ss-btn cancel" :disabled="saving || !dirty" @click="resetForm">还原</button>
        <button class="ss-btn save" :disabled="saving || !dirty" @click="saveConfig">
          {{ saving ? '保存中…' : '保存配置' }}
        </button>
      </div>
    </div>

    <!-- 摄像头旋转配置 -->
    <div class="ss-card" v-if="!loading && !errorMsg">
      <div class="ss-card-title">摄像头方向配置</div>
      <div class="ss-hint" style="margin-bottom: 12px;">配置摄像头物理安装方向，影响视频画面显示旋转角度</div>

      <div v-if="deviceLoading" class="ss-loading">加载设备列表…</div>
      <div v-else-if="deviceList.length === 0" class="ss-hint">暂无设备</div>
      <div v-else class="device-rotation-list">
        <div v-for="device in deviceList" :key="device.id" class="device-rotation-row">
          <div class="device-info">
            <span class="device-name">{{ device.name || device.device_id }}</span>
            <span class="device-id">{{ device.device_id }}</span>
            <span v-if="device.location" class="device-location">{{ device.location }}</span>
          </div>
          <div class="rotation-options">
            <button
              class="ss-option-btn small"
              :class="{ active: (deviceRotation[device.id] ?? 0) === 0 }"
              :disabled="deviceSaving === device.id"
              @click="setDeviceRotation(device, 0)"
            >
              正常
            </button>
            <button
              class="ss-option-btn small"
              :class="{ active: (deviceRotation[device.id] ?? 0) === 180 }"
              :disabled="deviceSaving === device.id"
              @click="setDeviceRotation(device, 180)"
            >
              倒装 180°
            </button>
          </div>
        </div>
      </div>

      <div v-if="deviceSaved" class="ss-badge-row">
        <span class="ss-badge badge-ok">✔ 已保存</span>
      </div>
    </div>
  </div>
</template>

<script>
import { systemConfigApi, deviceApi } from '@/services/api';

export default {
  name: 'SystemSettingsPage',

  data() {
    return {
      loading: false,
      saving: false,
      saved: false,
      errorMsg: '',
      form: {
        decoder_hardware_accel: 'cpu',
        udp_worker_count: 4,
      },
      original: {
        decoder_hardware_accel: 'cpu',
        udp_worker_count: 4,
      },
      // 设备旋转配置
      deviceList: [],
      deviceRotation: {},  // { [devicePk]: rotation }
      deviceLoading: false,
      deviceSaving: null,  // 正在保存的设备PK
      deviceSaved: false,
    };
  },

  computed: {
    dirty() {
      return (
        this.form.decoder_hardware_accel !== this.original.decoder_hardware_accel ||
        this.form.udp_worker_count !== this.original.udp_worker_count
      );
    },
  },

  mounted() {
    this.fetchConfig();
    this.fetchDevices();
  },

  methods: {
    async fetchConfig() {
      this.loading = true;
      this.errorMsg = '';
      const res = await systemConfigApi.getConfig();
      this.loading = false;
      if (res.error) {
        this.errorMsg = res.message || '加载配置失败';
        return;
      }
      this.form.decoder_hardware_accel = res.data.decoder_hardware_accel || 'cpu';
      this.form.udp_worker_count = res.data.udp_worker_count ?? 4;
      this.original = { ...this.form };
    },

    async saveConfig() {
      this.saving = true;
      this.saved = false;
      this.errorMsg = '';
      const res = await systemConfigApi.updateConfig({
        decoder_hardware_accel: this.form.decoder_hardware_accel,
        udp_worker_count: this.form.udp_worker_count,
      });
      this.saving = false;
      if (res.error) {
        this.errorMsg = res.message || '保存失败';
        return;
      }
      this.original = { ...this.form };
      this.saved = true;
      setTimeout(() => { window.location.reload(); }, 800);
    },

    resetForm() {
      this.form = { ...this.original };
    },

    async fetchDevices() {
      this.deviceLoading = true;
      const res = await deviceApi.listDevices(1, 200);
      this.deviceLoading = false;
      if (res.error) return;
      const items = res.data?.items || [];
      this.deviceList = items;
      // 初始化旋转角度映射
      const map = {};
      items.forEach(d => { map[d.id] = d.camera_rotation ?? 0; });
      this.deviceRotation = map;
    },

    async setDeviceRotation(device, rotation) {
      this.deviceSaving = device.id;
      this.deviceSaved = false;
      const res = await deviceApi.updateDevice(device.id, { camera_rotation: rotation });
      this.deviceSaving = null;
      if (res.error) return;
      this.deviceRotation[device.id] = rotation;
      this.deviceSaved = true;
      setTimeout(() => { window.location.reload(); }, 800);
    },
  },
};
</script>

<style scoped>
.sys-settings-page {
  width: 100%;
  height: 100%;
  padding: 20px 28px;
  color: #dbe8f0;
  overflow-y: auto;
  font-family: 'Microsoft YaHei', '微软雅黑', sans-serif;
}

.ss-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.ss-title {
  font-size: 20px;
  font-weight: 700;
  color: #e0f7fa;
  display: flex;
  align-items: center;
  gap: 8px;
}

.ss-icon {
  font-size: 22px;
}

.ss-badge.badge-ok {
  color: #4caf50;
  font-size: 14px;
  font-weight: 600;
}

.ss-badge-row {
  margin-top: 12px;
}

/* 设备旋转配置列表 */
.device-rotation-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.device-rotation-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.device-info {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.device-name {
  font-size: 14px;
  color: #e0f7fa;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.device-id {
  font-size: 12px;
  color: #7a9bb5;
  font-family: monospace;
}

.device-location {
  font-size: 12px;
  color: #7a9bb5;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.rotation-options {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.ss-option-btn.small {
  padding: 4px 12px;
  font-size: 12px;
}

.ss-loading,
.ss-error {
  text-align: center;
  padding: 40px 0;
  font-size: 15px;
  color: #b8d8e8;
}

.ss-error {
  color: #ff6b6b;
}

.ss-retry-btn {
  margin-left: 12px;
  padding: 4px 16px;
  border: 1px solid rgba(255, 107, 107, 0.5);
  border-radius: 6px;
  background: rgba(255, 107, 107, 0.15);
  color: #ff6b6b;
  cursor: pointer;
}

.ss-card {
  background: rgba(20, 30, 50, 0.45);
  border: 1px solid rgba(126, 200, 227, 0.2);
  border-radius: 10px;
  padding: 20px 24px;
  max-width: 460px;
}

.ss-card-title {
  font-size: 15px;
  font-weight: 700;
  color: #7ee0f0;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(, , , 0.35);
}

.ss-row {
  margin-bottom: 18px;
}

.ss-label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #dbe8f0;
  margin-bottom: 8px;
}

.ss-hint {
  display: block;
  font-size: 12px;
  color: rgba(184, 216, 232, 0.6);
  margin-top: 6px;
}

/* 解码器选择按钮组 */
.ss-select-group {
  display: flex;
  gap: 0;
}

.ss-option-btn {
  padding: 8px 22px;
  border: 1px solid rgba(126, 200, 227, 0.3);
  background: rgba(255, 255, 255, 0.06);
  color: #b8d8e8;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.ss-option-btn:first-child {
  border-radius: 6px 0 0 6px;
}

.ss-option-btn:last-child {
  border-radius: 0 6px 6px 0;
  border-left: none;
}

.ss-option-btn.active {
  background: rgba(64, 158, 255, 0.35);
  border-color: rgba(64, 158, 255, 0.7);
  color: #fff;
  font-weight: 700;
}

.ss-option-btn:hover:not(:disabled):not(.active) {
  background: rgba(255, 255, 255, 0.12);
}

.ss-option-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Worker 数输入组 */
.ss-input-group {
  display: flex;
  align-items: center;
  gap: 0;
}

.ss-adj-btn {
  width: 34px;
  height: 34px;
  border: 1px solid rgba(126, 200, 227, 0.3);
  background: rgba(255, 255, 255, 0.08);
  color: #dbe8f0;
  font-size: 18px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.15s;
}

.ss-adj-btn:first-child {
  border-radius: 6px 0 0 6px;
}

.ss-adj-btn:last-child {
  border-radius: 0 6px 6px 0;
}

.ss-adj-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.18);
}

.ss-adj-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.ss-input {
  width: 72px;
  height: 34px;
  border: 1px solid rgba(126, 200, 227, 0.3);
  border-left: none;
  border-right: none;
  background: rgba(0, 0, 0, 0.25);
  color: #fff;
  text-align: center;
  font-size: 15px;
  font-weight: 600;
  -moz-appearance: textfield;
  appearance: textfield;
}

.ss-input::-webkit-outer-spin-button,
.ss-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

/* 操作按钮 */
.ss-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
  padding-top: 14px;
  border-top: 1px solid rgba(, , , 0.35);
}

.ss-btn {
  min-width: 100px;
  height: 36px;
  border-radius: 6px;
  border: 1px solid transparent;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  cursor: pointer;
  transition: all 0.15s;
}

.ss-btn.cancel {
  background: rgba(100, 100, 100, 0.35);
  border-color: rgba(100, 100, 100, 0.5);
}

.ss-btn.save {
  background: rgba(64, 158, 255, 0.45);
  border-color: rgba(64, 158, 255, 0.65);
}

.ss-btn:hover:not(:disabled) {
  filter: brightness(1.12);
}

.ss-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
