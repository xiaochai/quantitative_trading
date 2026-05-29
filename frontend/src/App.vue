<template>
  <div id="app">
    <div class="bg-grid"></div>
    <div class="bg-gradient"></div>
    <router-view />
  </div>
</template>

<script setup>
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  background: #0a0f1a;
  min-height: 100vh;
  color: white;
  overflow-x: hidden;
}

#app {
  width: 100%;
  min-height: 100vh;
  position: relative;
  z-index: 1;
}

/* 背景网格 */
.bg-grid {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    linear-gradient(rgba(0,212,255,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,212,255,0.03) 1px, transparent 1px);
  background-size: 50px 50px;
  pointer-events: none;
  z-index: 0;
}

/* 背景渐变光晕 */
.bg-gradient {
  position: fixed;
  top: -50%;
  left: -50%;
  right: -50%;
  bottom: -50%;
  background: radial-gradient(circle at 20% 80%, rgba(0,212,255,0.08) 0%, transparent 50%),
              radial-gradient(circle at 80% 20%, rgba(0,255,136,0.06) 0%, transparent 50%);
  animation: bgMove 20s ease-in-out infinite;
  pointer-events: none;
  z-index: 0;
}

@keyframes bgMove {
  0%, 100% { transform: translate(0,0) rotate(0deg); }
  33% { transform: translate(30px,-30px) rotate(120deg); }
  66% { transform: translate(-30px,30px) rotate(240deg); }
}
</style>
