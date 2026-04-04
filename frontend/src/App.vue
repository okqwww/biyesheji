<script setup>
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const isHome = () => route.name === 'home'
</script>

<template>
  <div class="app-shell">
    <!-- Apple-style top navigation bar -->
    <nav class="nav-bar" v-if="!isHome()">
      <div class="nav-bar__inner">
        <div class="nav-bar__brand">
          <span class="brand-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
              <path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
              <path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
            </svg>
          </span>
          IQGS 智能出题
        </div>
        <div class="nav-bar__actions">
          <button class="nav-btn" @click="$router.push('/')" title="返回首页">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M3 9L12 2L21 9V20C21 20.5304 20.7893 21.0391 20.4142 21.4142C20.0391 21.7893 19.5304 22 19 22H5C4.46957 22 3.96086 21.7893 3.58579 21.4142C3.21071 21.0391 3 20.5304 3 20V9Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M9 22V12H15V22" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            首页
          </button>
        </div>
      </div>
    </nav>

    <router-view />
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  background: var(--color-bg);
}

.nav-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
  transition: background var(--transition-fast), color var(--transition-fast);
}

.nav-btn:hover {
  background: var(--color-bg-secondary);
  color: var(--color-text);
}

.brand-icon {
  display: inline-flex;
  align-items: center;
  color: var(--color-primary);
}
</style>
