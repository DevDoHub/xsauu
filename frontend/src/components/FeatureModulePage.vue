<template>
  <div class="feature-module-page">
    <!-- Header -->
    <div class="page-header">
      <h2 class="page-title">功能模块</h2>
    </div>

    <!-- Accordion List -->
    <div class="list-wrapper">
      <div
        v-for="category in categories"
        :key="category.id"
        class="accordion-item"
        :class="{ 'is-active': activeCategory === category.id }"
      >
        <!-- Category Header -->
        <div class="category-header" @click="toggleCategory(category.id)">
          <div class="header-left">
            <span class="category-name">{{ category.name }}</span>
            <span class="category-count">{{ category.targets.length }} ITEMS</span>
          </div>
          <div class="header-right">
            <span class="toggle-icon">{{ activeCategory === category.id ? '−' : '+' }}</span>
          </div>
        </div>

        <!-- Expandable Content -->
        <transition
          name="accordion"
          @enter="onEnter"
          @after-enter="onAfterEnter"
          @leave="onLeave"
        >
          <div v-show="activeCategory === category.id" class="category-content">
            <div class="content-inner">
              <div class="inner-header">
                <div class="col-target">检测目标</div>
                <div class="col-content">具体内容</div>
              </div>
              <div class="inner-body">
                <div v-for="(target, tIdx) in category.targets" :key="tIdx" class="target-group">
                  <div class="col-target" :class="{ 'is-placeholder': target.name === '/' }">
                    <span class="target-name">{{ target.name }}</span>
                  </div>
                  <div class="target-contents">
                    <div
                      v-for="(content, cIdx) in target.contents"
                      :key="`${tIdx}-${cIdx}`"
                      class="content-row"
                    >
                      <div class="col-content" :class="{ 'is-empty': !content }">
                        <span class="content-text">{{ content || '—' }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </transition>
      </div>
    </div>
  </div>
</template>

<script>
import { FEATURE_CATEGORIES } from '../utils/featureModuleData.js'

export default {
  name: 'FeatureModulePage',

  data() {
    return {
      activeCategory: null
    }
  },

  computed: {
    categories() {
      return FEATURE_CATEGORIES
    }
  },

  mounted() {
    if (this.categories && this.categories.length > 0) {
      this.activeCategory = this.categories[0].id
    }
  },

  methods: {
    toggleCategory(id) {
      this.activeCategory = this.activeCategory === id ? null : id
    },
    onEnter(el) {
      el.style.height = '0'
      // 强制重绘
      void el.offsetHeight
      el.style.height = el.scrollHeight + 'px'
    },
    onAfterEnter(el) {
      el.style.height = 'auto'
    },
    onLeave(el) {
      el.style.height = el.scrollHeight + 'px'
      // 强制重绘
      void el.offsetHeight
      el.style.height = '0'
    }
  }
}
</script>

<style scoped>
.feature-module-page {
  width: 100%;
  height: 100%;
  box-sizing: border-box;
  padding: 40px 60px;
  background: linear-gradient(180deg, rgba(58, 124, 178, 0.76), rgba(32, 88, 136, 0.84));
  font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
  -webkit-font-smoothing: antialiased;
  color: #e8fbff;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.page-header {
  margin-bottom: 40px;
}

.page-title {
  font-size: 32px;
  font-weight: 400;
  color: #f2fbff;
  letter-spacing: 2px;
  margin: 0;
}

.list-wrapper {
  width: 100%;
  max-width: 1200px;
  border-top: 1px solid rgba(186, 230, 253, 0.48);
}

.accordion-item {
  border-bottom: 1px solid rgba(186, 230, 253, 0.42);
  transition: background 0.3s ease;
}

.category-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 0;
  cursor: pointer;
  user-select: none;
}

.accordion-item:hover .category-header {
  color: #72cfff;
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: 24px;
}

.category-name {
  font-size: 24px;
  font-weight: 400;
  color: #f2fbff;
  letter-spacing: 1px;
  transition: color 0.3s;
}

.accordion-item.is-active .category-name {
  color: #72cfff;
}

.category-count {
  font-family: 'Consolas', 'Courier New', monospace;
  font-size: 14px;
  color: #b7dcf7;
  letter-spacing: 1px;
}

.header-right {
  display: flex;
  align-items: center;
}

.toggle-icon {
  font-family: monospace;
  font-size: 24px;
  color: #b7dcf7;
  font-weight: 300;
  width: 24px;
  text-align: right;
}

.accordion-item:hover .toggle-icon {
  color: #72cfff;
}

.category-content {
  overflow: hidden;
}

.content-inner {
  padding: 8px 0 40px 0;
}

.inner-header {
  display: flex;
  padding-bottom: 16px;
  border-bottom: 1px dashed rgba(186, 230, 253, 0.48);
}

.inner-header .col-target {
  border-right: none; /* Remove vertical line from header */
}

.inner-header .col-content {
  padding-left: 24px;
}

.target-group {
  display: flex;
  align-items: stretch;
  border-bottom: 1px dashed rgba(186, 230, 253, 0.42);
}

.target-group:last-child {
  border-bottom: none;
}

.col-target {
  width: 240px;
  flex-shrink: 0;
  font-size: 14px;
  color: #b7dcf7;
  padding-right: 24px;
  letter-spacing: 1px;
  display: flex;
  align-items: center; /* Vertically center the target name */
  border-right: 1px dashed rgba(186, 230, 253, 0.42); /* Vertical separator */
}

.target-contents {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding-left: 24px;
}

.col-content {
  flex: 1;
  font-size: 14px;
  color: #b7dcf7;
  letter-spacing: 1px;
}

.content-row {
  display: flex;
  padding: 16px 0;
}

.content-row:not(:last-child) {
  border-bottom: 1px dashed rgba(186, 230, 253, 0.38); /* Consistent dashed line between contents */
}

.target-group .col-target .target-name {
  font-size: 16px;
  color: #e8fbff;
  font-weight: 400;
  letter-spacing: 0.5px;
}

.target-group .col-target.is-placeholder .target-name {
  color: #8eb7d0;
  font-style: italic;
}

.content-row .col-content .content-text {
  font-size: 16px;
  color: #d7efff;
  line-height: 1.6;
}

.content-row .col-content.is-empty .content-text {
  color: #8eb7d0;
  font-style: italic;
}

/* Accordion transitions */
.accordion-enter-active,
.accordion-leave-active {
  transition: height 0.35s cubic-bezier(0.25, 0.8, 0.25, 1), opacity 0.35s ease;
  overflow: hidden;
}

.accordion-enter,
.accordion-leave-to {
  opacity: 0;
  height: 0;
}
</style>
