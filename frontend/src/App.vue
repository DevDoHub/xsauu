// App.vue
<template>
  <div>
    <!-- 如果未登录，则显示登录表单 -->
    <LoginForm v-if="!loggedIn" @login-success="handleLoginSuccess" />
    <!-- 如果已登录，则显示 HelloWorld 组件 -->
    <VedioMain v-else />
  </div>
</template>

<script>
import VedioMain from './components/VedioMain.vue';
import LoginForm from './components/UserLogin.vue';

export default {
  name: 'App',
  components: {
    VedioMain,
    LoginForm
  },
  data() {
    return {
      loggedIn: sessionStorage.getItem('loggedIn') === 'true'
    };
  },
  methods: {
    // 处理登录成功事件
    handleLoginSuccess() {
      this.loggedIn = true;
      sessionStorage.setItem('loggedIn', 'true');
    }
  }
};
</script>

<style>
#app {
  overflow: hidden;
}
</style>