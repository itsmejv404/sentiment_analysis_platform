import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import Dashboard from '@/views/Dashboard.vue';
import Register from '@/views/Register.vue';
import Login from '@/views/Login.vue';
import ResetPassword from '@/views/ResetPassword.vue';
import Organizations from '@/views/Organizations.vue';
import DeleteAccount from '@/views/DeleteAccount.vue';
import Billing from '@/views/Billing.vue';
import CreditsManagement from '@/views/CreditsManagement.vue';
import DashboardLayout from '@/components/DashboardLayout.vue';
import ForgotPassword from '@/views/ForgotPassword.vue';

const routes = [
  { path: "/", component: HomeView },
  { path: "/login", component: Login },
  { path: "/forgot-password", component: ForgotPassword },
  { path: "/reset-password", component: ResetPassword },
  { path: "/register", component: Register },
  {
    path: "/",
    component: DashboardLayout,
    meta: { requiresAuth: true },
    children: [
      { path: "dashboard", component: Dashboard },
      { path: "organizations", component: Organizations },
      { path: "organization", redirect: "/organizations" },
      { path: "billing", component: Billing },
      { path: "credits", component: CreditsManagement },
      { path: "delete-account", component: DeleteAccount },
    ],
  },
];
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: routes
})
import { useAuthStore } from "@/stores/auth";

router.beforeEach(async (to) => {
  const auth = useAuthStore();
  const token = localStorage.getItem("token");

  if (token && !auth.user) {
    try {
      await auth.fetchMe();
    } catch (error) {
      console.error("Failed to fetch user:", error);
      auth.logout();
      return "/login";
    }
  }

  if (to.meta.requiresAuth && !token) {
    return "/login";
  }

  if (to.meta.requiresAdmin && auth.user?.role !== "admin") {
    return "/dashboard";
  }

  return true;
});
export default router
