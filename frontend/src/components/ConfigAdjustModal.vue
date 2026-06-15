<template>
  <div v-if="visible" class="config-modal-overlay" @click.self="$emit('close')">
    <div class="config-modal">
      <h3>参数调整 - {{ deviceId }}</h3>
      <p>参数调整功能（待实现）</p>
      <button @click="$emit('close')">关闭</button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ConfigAdjustModal',
  props: {
    visible: { type: Boolean, default: false },
    deviceId: { type: String, default: '' },
    configData: { type: Object, default: () => ({}) },
    loading: { type: Boolean, default: false },
    saving: { type: Boolean, default: false },
    errorMessage: { type: String, default: '' },
  },
  emits: ['close', 'save'],
};
</script>

<style scoped>
.config-modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.config-modal { background: #1a2332; padding: 24px; border-radius: 8px; min-width: 400px; color: #fff; }
</style>
