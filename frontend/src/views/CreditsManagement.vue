<template>
  <div class="space-y-6 bg-transparent text-foreground">
    <!-- Header Block -->
    <div class="border border-border rounded-lg p-4 bg-card text-card-foreground shadow-sm space-y-1" v-if="user">
      <p class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Account Balance</p>
      <h2 class="text-2xl font-bold text-foreground">Credits Management</h2>
      <p class="text-xs text-muted-foreground">Monitor your current credits and organization status from one place.</p>
    </div>

    <!-- Stats Grid -->
    <div class="grid gap-4 grid-cols-2 md:grid-cols-4" v-if="user">
      <Card>
        <CardHeader class="pb-1">
          <CardDescription class="text-[10px] uppercase font-bold tracking-wider">Available Credits</CardDescription>
        </CardHeader>
        <CardContent>
          <p class="text-3xl font-extrabold">{{ user.credits }}</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader class="pb-1">
          <CardDescription class="text-[10px] uppercase font-bold tracking-wider">Organizations</CardDescription>
        </CardHeader>
        <CardContent>
          <p class="text-3xl font-extrabold">{{ organizations.length }}</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader class="pb-1">
          <CardDescription class="text-[10px] uppercase font-bold tracking-wider">Active</CardDescription>
        </CardHeader>
        <CardContent>
          <p class="text-3xl font-extrabold text-green-600">{{ activeOrganizations }}</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader class="pb-1">
          <CardDescription class="text-[10px] uppercase font-bold tracking-wider">Inactive</CardDescription>
        </CardHeader>
        <CardContent>
          <p class="text-3xl font-extrabold text-red-600">{{ inactiveOrganizations }}</p>
        </CardContent>
      </Card>
    </div>

    <!-- Credit Impact details -->
    <Card v-if="user">
      <CardHeader>
        <CardTitle class="text-sm">Organization Credit Impact</CardTitle>
        <CardDescription>
          Organizations become inactive when owner credits drop below 100.
        </CardDescription>
      </CardHeader>
      
      <CardContent class="p-0 border-t border-neutral-200">
        <div v-if="organizations.length === 0" class="text-center py-12 text-sm text-neutral-400">
          No organizations found.
        </div>
        <div v-else class="divide-y divide-neutral-200">
          <div v-for="org in organizations" :key="org.id" class="p-4 flex items-center justify-between text-sm hover:bg-neutral-50/50 transition-colors">
            <div>
              <p class="font-bold text-neutral-900">{{ org.brand_name || org.name }}</p>
              <p class="text-xs text-neutral-500">Role: {{ org.role }}</p>
            </div>
            <Badge :variant="org.is_active ? 'success' : 'destructive'">
              {{ org.is_active ? 'Active' : 'Inactive' }}
            </Badge>
          </div>
        </div>
      </CardContent>

      <CardFooter class="border-t border-neutral-100 pt-4 mt-2 flex justify-start">
        <Button @click="router.push('/billing')">
          Top Up Credits
        </Button>
      </CardFooter>
    </Card>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import Card from '../components/ui/Card.vue';
import CardHeader from '../components/ui/CardHeader.vue';
import CardTitle from '../components/ui/CardTitle.vue';
import CardDescription from '../components/ui/CardDescription.vue';
import CardContent from '../components/ui/CardContent.vue';
import CardFooter from '../components/ui/CardFooter.vue';
import Button from '../components/ui/Button.vue';
import Badge from '../components/ui/Badge.vue';

const router = useRouter();
const auth = useAuthStore();

const user = computed(() => auth.user);
const organizations = computed(() => auth.user?.organizations || []);
const activeOrganizations = computed(() => organizations.value.filter((org) => org.is_active).length);
const inactiveOrganizations = computed(() => organizations.value.filter((org) => !org.is_active).length);

onMounted(async () => {
  if (!auth.user) {
    await auth.fetchMe();
  }
});
</script>
