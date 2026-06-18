<template>
  <div class="min-h-screen bg-background text-foreground font-sans flex flex-col">
    <!-- Top Navigation Bar -->
    <header class="sticky top-0 z-40 w-full border-b border-border bg-background/95 backdrop-blur">
      <div class="flex h-14 items-center justify-between px-4 sm:px-6">
        <div class="flex items-center gap-3">
          <!-- Mobile Menu Trigger -->
          <Button variant="ghost" size="icon" class="md:hidden" @click="isMobileMenuOpen = !isMobileMenuOpen" aria-label="Toggle menu">
            <MenuIcon class="h-5 w-5" />
          </Button>

          <!-- Brand Logo -->
          <div class="flex items-center gap-2 cursor-pointer" @click="router.push('/dashboard')">
            <span class="font-extrabold text-sm tracking-tight uppercase border border-foreground px-1.5 py-0.5 rounded bg-foreground text-background">BrandPulse</span>
          </div>

          <span class="text-neutral-300 dark:text-neutral-700 hidden sm:inline">/</span>

          <span class="text-xs font-semibold uppercase tracking-wider text-neutral-500 hidden sm:inline">Console</span>
        </div>

        <!-- Right Side Nav Actions -->
        <div class="flex items-center gap-3">
          <div v-if="user" class="hidden md:flex items-center gap-1.5 text-xs text-neutral-500">
            <span class="h-2 w-2 rounded-full bg-green-500"></span>
            <span>{{ user.username }}</span>
          </div>

          <!-- Theme Mode Toggle Button -->
          <Button variant="ghost" size="icon" @click="toggleTheme" class="h-9 w-9 text-neutral-500 hover:text-foreground" aria-label="Toggle theme">
            <SunIcon v-if="isDark" class="h-4 w-4" />
            <MoonIcon v-else class="h-4 w-4" />
          </Button>

          <Button variant="outline" size="sm" @click="logout" class="gap-2 text-xs">
            <LogOutIcon class="h-3.5 w-3.5" />
            <span class="hidden sm:inline">Logout</span>
          </Button>
        </div>
      </div>
    </header>

    <div class="flex flex-1">
      <!-- Desktop Sidebar -->
      <aside
        :class="[
          'hidden md:flex flex-col border-r border-border bg-background transition-all duration-200',
          isSidebarCollapsed ? 'w-16' : 'w-64'
        ]"
      >
        <!-- Toggle Button Row -->
        <div class="flex p-3 border-b border-border justify-end">
          <Button variant="ghost" size="icon" @click="toggleSidebar" class="h-7 w-7 text-neutral-500">
            <ChevronLeftIcon v-if="!isSidebarCollapsed" class="h-4 w-4" />
            <ChevronRightIcon v-else class="h-4 w-4" />
          </Button>
        </div>

        <nav class="flex-1 space-y-1 p-3">
          <button
            v-for="link in navLinks"
            :key="link.path"
            @click="router.push(link.path)"
            :class="[
              'w-full flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors text-left',
              route.path === link.path
                ? 'bg-secondary text-secondary-foreground'
                : 'text-neutral-500 hover:bg-secondary/50 hover:text-foreground'
            ]"
          >
            <component :is="link.icon" class="h-4 w-4 shrink-0" />
            <span v-if="!isSidebarCollapsed" class="truncate">{{ link.label }}</span>
          </button>
        </nav>
      </aside>

      <!-- Mobile Dropdown Navigation -->
      <div
        v-if="isMobileMenuOpen"
        class="fixed inset-0 top-14 z-30 bg-black/60 md:hidden"
        @click="isMobileMenuOpen = false"
      />
      
      <aside
        v-if="isMobileMenuOpen"
        class="fixed inset-y-0 left-0 top-14 z-40 w-64 border-r border-border bg-background p-4 shadow-lg md:hidden animate-in slide-in-from-left duration-200"
      >
        <nav class="space-y-1">
          <button
            v-for="link in navLinks"
            :key="link.path"
            @click="navigateMobile(link.path)"
            :class="[
              'w-full flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors text-left',
              route.path === link.path
                ? 'bg-secondary text-secondary-foreground'
                : 'text-neutral-500 hover:bg-secondary/50 hover:text-foreground'
            ]"
          >
            <component :is="link.icon" class="h-4.5 w-4.5 shrink-0" />
            <span>{{ link.label }}</span>
          </button>
        </nav>
      </aside>

      <!-- Responsive Content Area -->
      <main class="flex-1 bg-background min-w-0 p-4 sm:p-6 lg:p-8">
        <div class="max-w-6xl mx-auto space-y-6">
          <RouterView />
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { RouterView, useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import Button from './ui/Button.vue';
import {
  LayoutDashboard as DashboardIcon,
  Building2 as OrganizationsIcon,
  CreditCard as BillingIcon,
  Coins as CreditsIcon,
  Trash2 as DeleteIcon,
  LogOut as LogOutIcon,
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
  Menu as MenuIcon,
  Sun as SunIcon,
  Moon as MoonIcon
} from 'lucide-vue-next';

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();

const isSidebarCollapsed = ref(false);
const isMobileMenuOpen = ref(false);

const user = computed(() => auth.user);
const isDark = computed(() => auth.theme === 'dark');

const navLinks = [
  { path: '/dashboard', label: 'Dashboard', icon: DashboardIcon },
  { path: '/organizations', label: 'Organizations', icon: OrganizationsIcon },
  { path: '/billing', label: 'Billing', icon: BillingIcon },
  { path: '/credits', label: 'Credits', icon: CreditsIcon },
  { path: '/delete-account', label: 'Delete Account', icon: DeleteIcon },
];

const toggleSidebar = () => {
  isSidebarCollapsed.value = !isSidebarCollapsed.value;
};

const toggleTheme = () => {
  const newTheme = auth.theme === 'dark' ? 'light' : 'dark';
  auth.setTheme(newTheme);
};

const navigateMobile = (path) => {
  isMobileMenuOpen.value = false;
  router.push(path);
};

const logout = () => {
  auth.logout();
  router.push('/');
};
</script>
