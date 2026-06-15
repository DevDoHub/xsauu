<template>
  <div v-if="visible" class="violation-modal-overlay" @click.self="$emit('cancel')">
    <div class="violation-modal">
      <div class="modal-header">
        <h3>远程报警</h3>
        <button type="button" class="close-btn" @click="$emit('cancel')">×</button>
      </div>

      <!-- 报警类型选择（仅选择，不触发报警） -->
      <div class="section">
        <label class="section-label">选择报警类型</label>
        <div class="type-grid">
          <button
            type="button"
            v-for="item in alarmTypes"
            :key="item.key"
            :class="['type-btn', { active: selectedType === item.key }]"
            @click.stop.prevent="selectType(item.key)"
          >
            <span class="type-icon">{{ item.icon }}</span>
            <span class="type-name">{{ item.label }}</span>
          </button>
        </div>
      </div>

      <!-- 严重级别（仅选择，不触发报警） -->
      <div class="section">
        <label class="section-label">严重级别</label>
        <div class="severity-row">
          <button
            type="button"
            v-for="s in severities"
            :key="s.value"
            :class="['sev-btn', s.value, { active: selectedSeverity === s.value }]"
            @click.stop.prevent="selectSeverity(s.value)"
          >{{ s.label }}</button>
        </div>
      </div>

      <!-- 补充描述 -->
      <div class="section">
        <label class="section-label">补充描述（可选）</label>
        <textarea v-model="description" placeholder="请输入违规详情..." rows="3"></textarea>
      </div>

      <!-- 操作按钮：只有这里的「确认报警」才会真正触发报警 -->
      <div class="actions">
        <button type="button" class="btn-cancel" @click="$emit('cancel')">取消</button>
        <button type="button" class="btn-confirm" :disabled="!selectedType" @click="handleConfirm">确认报警</button>
      </div>
    </div>
  </div>
</template>

<script>
const ALARM_TYPES = [
  { key: 'no_helmet',   label: '未戴安全帽',   icon: '⛑️' },
  { key: 'no_uniform',  label: '未穿工作服',   icon: '🦺' },
  { key: 'fire',        label: '火焰',         icon: '🔥' },
  { key: 'smoke',       label: '烟雾',         icon: '💨' },
  { key: 'fall',        label: '跌倒',         icon: '⚠️' },
  { key: 'phone',       label: '使用手机',     icon: '📱' },
  { key: 'no_glove',    label: '未戴手套',     icon: '🧤' },
  { key: 'intrusion',   label: '区域入侵',     icon: '🚧' },
  { key: 'gas_leak',    label: '气体泄漏',     icon: '☁️' },
  { key: 'other',       label: '其他',         icon: '📋' },
];

const SEVERITIES = [
  { value: 'low',      label: '低' },
  { value: 'medium',   label: '中' },
  { value: 'high',     label: '高' },
  { value: 'critical', label: '紧急' },
];

export default {
  name: 'ViolationInputModal',
  props: {
    visible: { type: Boolean, default: false },
  },
  emits: ['confirm', 'cancel'],
  data() {
    return {
      selectedType: '',
      selectedSeverity: 'medium',
      description: '',
      alarmTypes: ALARM_TYPES,
      severities: SEVERITIES,
    };
  },
  watch: {
    visible(val) {
      if (val) {
        this.selectedType = '';
        this.selectedSeverity = 'medium';
        this.description = '';
      }
    },
  },
  methods: {
    /** 仅选择报警类型，不触发报警 */
    selectType(key) {
      this.selectedType = key;
    },
    /** 仅选择严重级别，不触发报警 */
    selectSeverity(value) {
      this.selectedSeverity = value;
    },
    /** 唯一的报警入口：用户点击「确认报警」时才 emit */
    handleConfirm() {
      if (!this.selectedType) return;
      const typeObj = this.alarmTypes.find(t => t.key === this.selectedType);
      this.$emit('confirm', {
        alarmType: this.selectedType,
        alarmTypeLabel: typeObj ? typeObj.label : this.selectedType,
        severity: this.selectedSeverity,
        description: this.description || typeObj?.label || '手动报警',
      });
    },
  },
};
</script>

<style scoped>
.violation-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1200;
}
.violation-modal {
  background: linear-gradient(180deg, #0f1e30, #0a1628);
  border: 1px solid rgba(100, 180, 255, 0.3);
  border-radius: 12px;
  padding: 24px;
  min-width: 460px;
  max-width: 520px;
  color: #e6f6ff;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.modal-header h3 { margin: 0; font-size: 18px; color: #fff; }
.close-btn {
  background: none;
  border: none;
  color: #8b949e;
  font-size: 24px;
  cursor: pointer;
  line-height: 1;
}
.close-btn:hover { color: #fff; }

.section { margin-bottom: 16px; }
.section-label {
  display: block;
  font-size: 13px;
  color: #8b949e;
  margin-bottom: 8px;
}

.type-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
}
.type-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 10px 4px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(100, 180, 255, 0.15);
  border-radius: 8px;
  color: #b8d8e8;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 12px;
}
.type-btn:hover {
  background: rgba(100, 180, 255, 0.12);
  border-color: rgba(100, 180, 255, 0.4);
}
.type-btn.active {
  background: rgba(31, 111, 235, 0.3);
  border-color: #1f6feb;
  color: #fff;
  box-shadow: 0 0 8px rgba(31, 111, 235, 0.3);
}
.type-icon { font-size: 22px; }
.type-name { white-space: nowrap; }

.severity-row { display: flex; gap: 8px; }
.sev-btn {
  flex: 1;
  padding: 6px 0;
  border: 1px solid rgba(100, 180, 255, 0.2);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.04);
  color: #b8d8e8;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}
.sev-btn:hover { background: rgba(100, 180, 255, 0.1); }
.sev-btn.active.low { background: rgba(63, 185, 80, 0.25); border-color: #3fb950; color: #3fb950; }
.sev-btn.active.medium { background: rgba(210, 153, 34, 0.25); border-color: #d29922; color: #d29922; }
.sev-btn.active.high { background: rgba(248, 81, 73, 0.25); border-color: #f85149; color: #f85149; }
.sev-btn.active.critical { background: rgba(255, 0, 0, 0.25); border-color: #ff0000; color: #ff4444; }

textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid rgba(100, 180, 255, 0.2);
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.3);
  color: #e6f6ff;
  resize: vertical;
  font-size: 14px;
  outline: none;
  box-sizing: border-box;
}
textarea:focus { border-color: rgba(100, 180, 255, 0.5); }

.actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 20px;
}
.btn-cancel {
  padding: 8px 24px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(100, 180, 255, 0.2);
  border-radius: 6px;
  color: #b8d8e8;
  cursor: pointer;
  font-size: 14px;
}
.btn-cancel:hover { background: rgba(255, 255, 255, 0.12); }
.btn-confirm {
  padding: 8px 24px;
  background: linear-gradient(180deg, #238636, #196c2e);
  border: 1px solid rgba(63, 185, 80, 0.4);
  border-radius: 6px;
  color: #fff;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
}
.btn-confirm:hover:not(:disabled) { background: linear-gradient(180deg, #2ea043, #238636); }
.btn-confirm:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
