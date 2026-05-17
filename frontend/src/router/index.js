/**
 * Router — navigation guards
 *
 * meta.roles  — array of allowed roles; if absent, any authenticated user can access.
 *               Route is blocked (→ Scan) if user's role is not in the array.
 *
 * Guard logic:
 *  1. Public routes (meta.public) → always allow
 *  2. Logged-in user visiting /login → redirect to /scan
 *  3. Not logged in → redirect to /login (with ?reason=expired if token exists but expired)
 *  4. Logged in but wrong role → redirect to /scan
 *
 * isLoggedIn already covers token expiry (user computed returns null when expired).
 */
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true },
  },

  // ── Mobile scanner — standalone full-screen, no sidebar ──────────────────
  // Designed for smartphones held by operators at entry gates.
  // Accessible via URL: http://<server>:5173/mobile-scan
  // All authenticated roles allowed (OPERATOR, HR, ADMIN).
  {
    path: '/mobile-scan',
    name: 'MobileScan',
    component: () => import('@/views/MobileScanView.vue'),
    meta: { title: 'Mobile Scan' },
  },

  {
    path: '/',
    component: () => import('@/layouts/AppLayout.vue'),
    children: [
      { path: '', redirect: '/scan' },

      // ── Operations (all authenticated users) ────────────────────────────
      {
        path: 'scan',
        name: 'Scan',
        component: () => import('@/views/ScanView.vue'),
        meta: { title: 'Live Scan' },
        // No roles restriction — OPERATOR, HR, ADMIN all allowed
      },

      // ── HR section (HR + ADMIN only) ──────────────────────────────────
      {
        path: 'attendance',
        name: 'Attendance',
        component: () => import('@/views/AttendanceView.vue'),
        meta: { title: 'Attendance Logs', roles: ['ADMIN', 'HR'] },
      },
      {
        path: 'employees',
        name: 'Employees',
        component: () => import('@/views/EmployeesView.vue'),
        meta: { title: 'Employees', roles: ['ADMIN', 'HR'] },
      },
      {
        path: 'employees/:id/enroll',
        name: 'Enrollment',
        component: () => import('@/views/EnrollmentView.vue'),
        meta: { title: 'Face Enrollment', roles: ['ADMIN', 'HR'] },
      },
      {
        path: 'departments',
        name: 'Departments',
        component: () => import('@/views/DepartmentsView.vue'),
        meta: { title: 'Departments', roles: ['ADMIN', 'HR'] },
      },

      // ── System / ADMIN only ────────────────────────────────────────────
      {
        path: 'console',
        name: 'PilotConsole',
        component: () => import('@/views/PilotConsoleView.vue'),
        meta: { title: 'Pilot Console', roles: ['ADMIN'] },
      },
      {
        path: 'stations',
        name: 'Stations',
        component: () => import('@/views/StationsView.vue'),
        meta: { title: 'Stations', roles: ['ADMIN'] },
      },
      {
        path: 'cameras',
        name: 'Cameras',
        component: () => import('@/views/CamerasView.vue'),
        meta: { title: 'Cameras', roles: ['ADMIN'] },
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/UsersView.vue'),
        meta: { title: 'User Management', roles: ['ADMIN'] },
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/SettingsView.vue'),
        meta: { title: 'System Settings', roles: ['ADMIN'] },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()

  // 1. Public routes — always allow
  if (to.meta.public) {
    // But if already logged in, bounce away from /login
    if (to.name === 'Login' && auth.isLoggedIn) {
      return { name: 'Scan' }
    }
    return
  }

  // 2. Not authenticated (covers expired token — isLoggedIn checks expiry)
  if (!auth.isLoggedIn) {
    // Pass reason so LoginView can show the right message
    const reason = auth.token ? 'expired' : undefined
    return { name: 'Login', query: reason ? { reason } : undefined }
  }

  // 3. Role guard — check against roles array
  const requiredRoles = to.meta.roles
  if (requiredRoles && !requiredRoles.includes(auth.user?.role)) {
    // User is authenticated but doesn't have permission
    return { name: 'Scan' }
  }
})

export default router
