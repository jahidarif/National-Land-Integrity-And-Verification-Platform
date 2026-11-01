import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';
import store from '@/store';
const dashboard: RouteRecordRaw = {
  path: '/dashboard', component: () => import('@/layouts/DashboardLayout.vue'), meta: { requiresAuth: true },
  children: [
    { path: 'admin', redirect: '/dashboard/admin/officers' },
    { path: 'landofficer', redirect: '/dashboard/landofficer/lands' },
    { path: 'user', redirect: '/dashboard/user/lands' },
    { path: 'admin/officers', name: 'admin-officers', component: () => import('@/views/admin/OfficersView.vue'), meta: { roles: ['Admin'] } },
    { path: 'admin/areas', name: 'admin-areas', component: () => import('@/views/admin/AreasView.vue'), meta: { roles: ['Admin'] } },
    { path: 'landofficer/lands', name: 'officer-lands', component: () => import('@/views/officer/LandsView.vue'), meta: { roles: ['LandOfficer'] } },
    { path: 'landofficer/drafts/:kind(updates|creates)', name: 'officer-drafts', component: () => import('@/views/officer/DraftsView.vue'), meta: { roles: ['LandOfficer'] } },
    { path: 'landofficer/drafts/:kind(updates|creates)/:id', name: 'officer-draft-form', component: () => import('@/views/officer/LandDraftForm.vue'), meta: { roles: ['LandOfficer'] } },
    { path: 'user/lands', name: 'user-lands', component: () => import('@/views/user/LandsView.vue'), meta: { roles: ['User'] } },
    { path: 'user/documents', name: 'user-documents', component: () => import('@/views/user/DocumentsView.vue'), meta: { roles: ['User'] } },
  ],
};
const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/dashboard' },
  { path: '/auth/login', component: () => import('@/views/AuthView.vue'), meta: { public: true } },
  { path: '/auth/register', component: () => import('@/views/AuthView.vue'), meta: { public: true } },
  { path: '/chat', component: () => import('@/layouts/DashboardLayout.vue'), meta: { requiresAuth: true, roles: ['LandOfficer', 'User'] } },
  dashboard,
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
];
const router = createRouter({ history: createWebHistory(), routes, scrollBehavior: () => ({ top: 0 }) });
const ROLE_HOME: Record<string,string> = { Admin: '/dashboard/admin', LandOfficer: '/dashboard/landofficer', User: '/dashboard/user' };
router.beforeEach(async (to) => {
  if (!store.getters['auth/bootstrapped']) { try { await store.dispatch('auth/fetchCurrentUser'); } catch { /* anonymous */ } }
  const user = store.getters['auth/user'];
  if (to.path === "/chat" && user) { const home = ROLE_HOME[user.role] || "/auth/login"; return user.role === "Admin" ? home : { path: home, query: { openChat: "1" } }; }
  if (to.meta.requiresAuth && !user) return { path: '/auth/login', query: { from: to.fullPath } };
  if (to.meta.public && user) return ROLE_HOME[user.role] || '/auth/login';
  if (to.path === '/dashboard' && user) return ROLE_HOME[user.role] || '/auth/login';
  const roles = to.meta.roles as string[] | undefined;
  if (roles && user && !roles.includes(user.role)) return ROLE_HOME[user.role] || '/auth/login';
  return true;
});
export default router;
