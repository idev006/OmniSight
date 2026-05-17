import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: () => import('@/layouts/AppLayout.vue'),
    children: [
      {
        path: '',
        redirect: '/scan',
      },
      {
        path: 'scan',
        name: 'Scan',
        component: () => import('@/views/ScanView.vue'),
        meta: { title: 'Live Scan' },
      },
      {
        path: 'employees',
        name: 'Employees',
        component: () => import('@/views/EmployeesView.vue'),
        meta: { title: 'Employees' },
      },
      {
        path: 'employees/:id/enroll',
        name: 'Enrollment',
        component: () => import('@/views/EnrollmentView.vue'),
        meta: { title: 'Face Enrollment' },
      },
      {
        path: 'departments',
        name: 'Departments',
        component: () => import('@/views/DepartmentsView.vue'),
        meta: { title: 'Departments' },
      },
      {
        path: 'stations',
        name: 'Stations',
        component: () => import('@/views/StationsView.vue'),
        meta: { title: 'Stations' },
      },
      {
        path: 'attendance',
        name: 'Attendance',
        component: () => import('@/views/AttendanceView.vue'),
        meta: { title: 'Attendance Logs' },
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/UsersView.vue'),
        meta: { title: 'User Management', role: 'ADMIN' },
      },
      {
        path: 'cameras',
        name: 'Cameras',
        component: () => import('@/views/CamerasView.vue'),
        meta: { title: 'Cameras' },
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/SettingsView.vue'),
        meta: { title: 'System Settings', role: 'ADMIN' },
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
  if (!to.meta.public && !auth.token) {
    return { name: 'Login' }
  }
  // Role-guard: redirect if user lacks required role
  if (to.meta.role && auth.user?.role !== to.meta.role) {
    return { name: 'Scan' }
  }
})

export default router
