<template>
  <div class="login-page">
    <div class="login-card">
      <!-- 顶部装饰线 -->
      <div class="card-accent"></div>

      <div class="card-body">
        <!-- 系统标识 -->
        <h1 class="login-title">核电建造安全智能监控系统</h1>
        <div class="title-divider"></div>

        <!-- 输入区 -->
        <div class="login-field">
          <label class="field-label">用户名</label>
          <div class="input-wrap">
            <span class="input-icon">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
            </span>
            <input
              type="text"
              placeholder="输入用户名"
              v-model="username"
              @keyup.enter="password ? login() : $refs.passwordInput.focus()"
              autocomplete="username"
            />
          </div>
        </div>
        <div class="login-field">
          <label class="field-label">密&emsp;码</label>
          <div class="password-wrap">
            <span class="input-icon">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
            </span>
            <input
              ref="passwordInput"
              :type="showPassword ? 'text' : 'password'"
              placeholder="输入密码"
              v-model="password"
              @keyup.enter="login"
              autocomplete="current-password"
            />
            <span class="eye-toggle" @click="showPassword = !showPassword">
              <svg v-if="showPassword" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              <svg v-else viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
                <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
                <path d="M14.12 14.12a3 3 0 1 1-4.24-4.24"/>
                <line x1="1" y1="1" x2="23" y2="23"/>
              </svg>
            </span>
          </div>
        </div>

        <p v-if="errorMsg" class="login-error">
          <span class="error-icon">⚠</span> {{ errorMsg }}
        </p>

        <button class="login-btn" @click="login" :disabled="loading">
          <span v-if="loading" class="btn-loading"></span>
          {{ loading ? '登录中...' : '进 入' }}
        </button>
      </div>
    </div>


  </div>
</template>

<script>
import axios from 'axios';

export default {
  data() {
    return {
      username: '',
      password: '',
      errorMsg: '',
      loading: false,
      showPassword: false
    };
  },
  methods: {
    async login() {
      this.errorMsg = '';
      if (!this.username || !this.password) {
        this.errorMsg = '请输入用户名和密码';
        return;
      }
      this.loading = true;
      try {
        const resp = await axios.post('/api/users/login', {
          username: this.username,
          password: this.password
        });
        if (resp.data.access_token) {
          // 保存 token 供后续请求使用
          localStorage.setItem('token', resp.data.access_token);
          this.$emit('login-success');
        }
      } catch (err) {
        if (err.response && err.response.status === 401) {
          this.errorMsg = '用户名或密码错误';
        } else {
          this.errorMsg = '网络错误，请重试';
        }
      } finally {
        this.loading = false;
      }
    }
  }
};
</script>

<style scoped>
/* 字体使用本地等宽栈，避免外部CDN加载慢 */

/* ── 页面容器 ── */
.login-page {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  width: 100%;
  background: url('../assets/img/login.jpg') center center / cover no-repeat;
  overflow: hidden;
}

/* 暗色遮罩：已移除，保持背景清晰 */

/* ── 登录卡片 ── */
.login-card {
  position: relative;
  z-index: 1;
  width: 440px;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 10px;
  animation: cardReveal 0.8s cubic-bezier(0.16, 1, 0.3, 1) both;
}

@keyframes cardReveal {
  from {
    opacity: 0;
    transform: translateY(20px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* 顶部装饰线 */
.card-accent {
  height: 3px;
  background: linear-gradient(90deg, transparent, #c9a96e, #7fb8c4, transparent);
  border-radius: 10px 10px 0 0;
}

.card-body {
  padding: 44px 40px 40px;
}

/* ── 系统标识 ── */
.sys-badge {
  font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 3px;
  color: #c9a96e;
  text-align: center;
  margin-bottom: 8px;
}

.login-title {
  font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
  font-size: 25px;
  font-weight: bold;
  color: #d1c4b0;
  text-align: center;
  margin: 0 0 0 0;
  letter-spacing: 2px;
  text-shadow: 0 2px 12px rgba(0, 0, 0, 0.6), 0 0 4px rgba(0, 0, 0, 0.4);
}

.title-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
  margin: 20px 0 28px;
}

.login-subtitle {
  font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
  font-size: 10px;
  letter-spacing: 4px;
  color: rgba(255, 255, 255, 0.25);
  text-align: center;
  margin: 0 0 36px 0;
}

/* ── 输入区 ── */
.login-field {
  margin-bottom: 20px;
}

.field-label {
  display: block;
  font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
  font-size: 15px;
  font-weight: 500;
  letter-spacing: 2px;
  color: #eee;
  margin-bottom: 8px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.6);
}

.password-wrap {
  position: relative;
}

.password-wrap input {
  padding-right: 44px;
}

.eye-toggle {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  cursor: pointer;
  font-size: 18px;
  user-select: none;
  color: #fff;
  opacity: 0.7;
  transition: opacity 0.2s;
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.3));
}

.eye-toggle:hover {
  opacity: 0.9;
}

.input-wrap {
  position: relative;
}

.input-icon {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: rgba(255, 255, 255, 0.8);
  display: flex;
  align-items: center;
  pointer-events: none;
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.3));
}

.input-wrap input,
.password-wrap input {
  padding-left: 44px !important;
}

.login-field input {
  width: 100%;
  padding: 12px 16px;
  background: rgba(0, 0, 0, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 8px;
  font-size: 15px;
  font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
  color: #fff;
  box-sizing: border-box;
  transition: all 0.25s ease;
}

.login-field input::placeholder {
  color: rgba(255, 255, 255, 0.6);
  font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
  font-size: 13px;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

.login-field input:focus {
  outline: none;
  border-color: #fff;
  background: rgba(255, 255, 255, 0.1);
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.3);
}

/* ── 错误提示 ── */
.login-error {
  font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
  font-size: 13px;
  color: #ff8a80;
  margin: 0 0 16px 0;
  padding: 8px 12px;
  background: rgba(255, 107, 107, 0.1);
  border-left: 2px solid #ff8a80;
  border-radius: 0 4px 4px 0;
  animation: shakeX 0.4s ease;
}

.error-icon {
  margin-right: 4px;
}

@keyframes shakeX {
  0%, 100% { transform: translateX(0); }
  20%      { transform: translateX(-6px); }
  40%      { transform: translateX(6px); }
  60%      { transform: translateX(-4px); }
  80%      { transform: translateX(4px); }
}

/* ── 登录按钮 ── */
.login-btn {
  width: 100%;
  padding: 14px 24px;
  margin-top: 8px;
  background: rgba(0, 0, 0, 0.45);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 8px;
  font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
  font-size: 14px;
  font-weight: bold;
  letter-spacing: 4px;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.4);
}

.login-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  transition: left 0.5s ease;
}

.login-btn:hover:not(:disabled) {
  border-color: #fff;
  background: rgba(255, 255, 255, 0.25);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2), 0 0 15px rgba(255, 255, 255, 0.3);
  transform: translateY(-1px);
}

.login-btn:hover:not(:disabled)::before {
  left: 100%;
}

.login-btn:active:not(:disabled) {
  transform: translateY(0);
}

.login-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* loading 旋转点 */
.btn-loading {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #c9a96e;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-right: 8px;
  vertical-align: middle;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ── 底部信息 ── */
.footer-info {
  position: absolute;
  bottom: 24px;
  font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
  font-size: 10px;
  letter-spacing: 3px;
  color: rgba(255, 255, 255, 0.15);
  z-index: 1;
}
</style>