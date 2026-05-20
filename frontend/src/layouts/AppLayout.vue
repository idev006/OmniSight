<template>
  <div class="drawer lg:drawer-open">
    <input id="sidebar-toggle" type="checkbox" class="drawer-toggle" />

    <div class="drawer-content flex flex-col min-h-screen bg-base-200/40">
      <!-- Mobile topbar -->
      <div class="navbar bg-base-100 border-b border-base-300 lg:hidden px-3">
        <label for="sidebar-toggle" class="btn btn-ghost btn-sm drawer-button">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </label>
        <span class="font-bold ml-2 tracking-widest text-primary">OMNISIGHT</span>
      </div>

      <!-- Page content -->
      <main class="flex-1 p-4 md:p-6 max-w-screen-xl w-full mx-auto">
        <RouterView />
      </main>
    </div>

    <!-- Sidebar -->
    <div class="drawer-side z-20">
      <label for="sidebar-toggle" class="drawer-overlay"></label>
      <aside class="bg-base-100 border-r border-base-300 w-60 min-h-full flex flex-col">

        <!-- Brand -->
        <div class="px-5 py-4 border-b border-base-300">
          <div class="font-bold tracking-[0.2em] text-primary text-lg">OMNISIGHT</div>
          <div class="text-[10px] text-base-content/30 tracking-widest uppercase mt-0.5">Face Recognition System</div>
        </div>

        <!-- User card -->
        <div class="mx-3 mt-3 mb-1 rounded-xl bg-base-200 px-3 py-2.5 flex items-center gap-2.5">
          <div class="avatar placeholder">
            <div class="rounded-full w-8 text-xs font-bold" :class="avatarBg">
              <span>{{ userInitial }}</span>
            </div>
          </div>
          <div class="min-w-0 flex-1">
            <div class="text-sm font-semibold truncate leading-tight">{{ auth.user?.username }}</div>
            <div class="badge badge-xs mt-0.5 leading-none" :class="roleBadge">{{ auth.user?.role }}</div>
          </div>
        </div>

        <!-- Nav -->
        <ul class="menu menu-sm flex-1 px-2 py-2 gap-0.5">

          <template v-if="auth.isHR">
            <li class="menu-title text-[10px] tracking-widest uppercase opacity-40 px-3 mb-0.5 mt-1">Overview</li>
            <li>
              <RouterLink to="/dashboard" active-class="active" class="gap-3 rounded-lg">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                </svg>
                Dashboard
              </RouterLink>
            </li>
          </template>

          <li class="menu-title text-[10px] tracking-widest uppercase opacity-40 px-3 mb-0.5 mt-1">Operations</li>
          <li>
            <RouterLink to="/scan" active-class="active" class="gap-3 rounded-lg">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.069A1 1 0 0121 8.882v6.236a1 1 0 01-1.447.894L15 14M3 8a2 2 0 012-2h10a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z" />
              </svg>
              Live Scan
            </RouterLink>
          </li>
          <li>
            <RouterLink to="/mobile-scan" active-class="active" class="gap-3 rounded-lg">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
              Mobile Scan
            </RouterLink>
          </li>
          <li>
            <RouterLink to="/attendance" active-class="active" class="gap-3 rounded-lg">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
              </svg>
              Attendance
            </RouterLink>
          </li>

          <template v-if="auth.isHR">
            <li class="menu-title text-[10px] tracking-widest uppercase opacity-40 px-3 mb-0.5 mt-3">HR</li>
            <li>
              <RouterLink to="/employees" active-class="active" class="gap-3 rounded-lg">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                Employees
              </RouterLink>
            </li>
            <li>
              <RouterLink to="/departments" active-class="active" class="gap-3 rounded-lg">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
                Departments
              </RouterLink>
            </li>
          </template>

          <template v-if="auth.isAdmin">
            <li class="menu-title text-[10px] tracking-widest uppercase opacity-40 px-3 mb-0.5 mt-3">System</li>
            <li>
              <RouterLink to="/console" active-class="active" class="gap-3 rounded-lg">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
                </svg>
                Pilot Console
              </RouterLink>
            </li>
            <li>
              <RouterLink to="/stations" active-class="active" class="gap-3 rounded-lg">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                </svg>
                Stations
              </RouterLink>
            </li>
            <li>
              <RouterLink to="/cameras" active-class="active" class="gap-3 rounded-lg">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7a1 1 0 011-1h3l2-2h6l2 2h3a1 1 0 011 1v11a1 1 0 01-1 1H4a1 1 0 01-1-1V7z" />
                  <circle cx="12" cy="13" r="3" stroke="currentColor" stroke-width="2" fill="none" />
                </svg>
                Cameras
              </RouterLink>
            </li>
            <li>
              <RouterLink to="/users" active-class="active" class="gap-3 rounded-lg">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
                Users
              </RouterLink>
            </li>
            <li>
              <RouterLink to="/settings" active-class="active" class="gap-3 rounded-lg">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                Settings
              </RouterLink>
            </li>
            <li>
              <RouterLink to="/system" active-class="active" class="gap-3 rounded-lg">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2v-4M9 21H5a2 2 0 01-2-2v-4m0 0h18" />
                </svg>
                System Info
              </RouterLink>
            </li>
          </template>

        </ul>

        <!-- Theme picker -->
        <div class="px-3 pb-2 border-t border-base-300 pt-3">
          <div class="text-[10px] tracking-widest uppercase opacity-40 px-1 mb-2">Theme</div>
          <div class="dropdown dropdown-top w-full">
            <div tabindex="0" role="button" class="btn btn-ghost btn-sm w-full justify-between border border-base-300">
              <span>{{ currentThemeLabel }}</span>
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </div>
            <ul tabindex="0" class="dropdown-content z-[100] menu p-1 shadow-2xl bg-base-100 rounded-box w-56 max-h-72 overflow-y-auto border border-base-300 flex-nowrap">
              <li v-for="t in themes" :key="t.name">
                <button
                  class="text-sm flex items-center gap-2 rounded-lg"
                  :class="{ 'active font-semibold': themeStore.current === t.name }"
                  @click="themeStore.setTheme(t.name)"
                >
                  <span>{{ t.icon }}</span>
                  <span>{{ t.label }}</span>
                  <span v-if="themeStore.current === t.name" class="ml-auto">✓</span>
                </button>
              </li>
            </ul>
          </div>
        </div>

        <!-- Logout -->
        <div class="px-3 pb-4">
          <button class="btn btn-ghost btn-sm w-full justify-start gap-2 text-error/80 hover:text-error hover:bg-error/10" @click="handleLogout()">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            Sign Out
          </button>
        </div>

      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore, THEMES } from '@/stores/theme'
import { useConfirm } from '@/composables/useConfirm'

const auth = useAuthStore()
const themeStore = useThemeStore()
const { confirm } = useConfirm()

async function handleLogout() {
  const ok = await confirm(
    `Sign out of OmniSight? You will need to log in again to continue.`,
    { title: 'Sign Out', confirmLabel: 'Sign Out', confirmClass: 'btn-error' }
  )
  if (ok) auth.logout()
}
const themes = THEMES

const userInitial = computed(() =>
  (auth.user?.username || '?')[0].toUpperCase()
)

const roleBadge = computed(() => {
  const r = auth.user?.role
  if (r === 'ADMIN') return 'badge-error'
  if (r === 'HR')    return 'badge-warning'
  return 'badge-info'
})

const avatarBg = computed(() => {
  const r = auth.user?.role
  if (r === 'ADMIN') return 'bg-error text-error-content'
  if (r === 'HR')    return 'bg-warning text-warning-content'
  return 'bg-primary text-primary-content'
})

const currentThemeLabel = computed(() => {
  const t = THEMES.find(t => t.name === themeStore.current)
  return t ? `${t.icon} ${t.label}` : themeStore.current
})
</script>
