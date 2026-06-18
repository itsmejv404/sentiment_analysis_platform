<template>
  <div class="space-y-6 bg-transparent text-foreground">
    <!-- Header Block -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border border-border rounded-lg p-4 bg-card text-card-foreground shadow-sm">
      <div class="space-y-1">
        <p class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Workspace</p>
        <h2 class="text-2xl font-bold text-foreground">Organizations</h2>
        <p class="text-xs text-muted-foreground">Create and manage multiple organizations from one place.</p>
      </div>

      <div class="flex items-center gap-4" v-if="user">
        <div class="grid gap-1.5">
          <label class="text-[10px] font-bold uppercase tracking-wider text-neutral-500">Active Organization</label>
          <Select v-model="activeTenantIdModel" class="w-48 font-medium">
            <option v-for="org in organizations" :key="org.id" :value="org.id">
              {{ org.brand_name || org.name }}
            </option>
          </Select>
        </div>
        <div class="h-10 border-r border-neutral-200" />
        <div class="text-right">
          <p class="text-[10px] font-bold uppercase tracking-wider text-neutral-500">Balance</p>
          <p class="text-lg font-bold">{{ user.credits }} Credits</p>
        </div>
      </div>
    </div>

    <!-- Active Organizations Panel -->
    <Card>
      <CardHeader>
        <CardTitle class="text-sm">Your Organizations</CardTitle>
        <CardDescription>{{ organizations.length }} configured brand workspace(s)</CardDescription>
      </CardHeader>
      
      <CardContent class="p-0 border-t border-neutral-200">
        <div v-if="organizations.length === 0" class="text-center py-12 text-sm text-neutral-400">
          No organizations yet. Create your first one below.
        </div>
        <div v-else class="divide-y divide-neutral-200">
          <div v-for="org in organizations" :key="org.id" class="p-4 sm:p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-neutral-50/50 transition-colors">
            <div class="space-y-1.5">
              <div class="flex items-center gap-2">
                <h4 class="font-bold text-neutral-900">{{ org.brand_name || org.name }}</h4>
                <Badge :variant="org.is_active ? 'success' : 'destructive'">
                  {{ org.is_active ? 'Active' : 'Suspended' }}
                </Badge>
              </div>
              <div class="grid gap-0.5 text-xs text-neutral-500">
                <p>System Key: <code class="font-mono text-[10px] bg-neutral-100 px-1 py-0.5 rounded">{{ org.name }}</code></p>
                <p>Your Role: <span class="capitalize font-medium text-neutral-700">{{ org.role }}</span> <span v-if="isOwner(org)" class="text-neutral-400 text-[10px]">| Owner</span></p>
                <p v-if="org.keywords">Keywords: <span class="text-neutral-700 font-medium">{{ org.keywords }}</span></p>
                <p v-else class="text-neutral-400">No keywords configured</p>
              </div>
            </div>

            <div class="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                v-if="isOwner(org)"
                @click="toggleOrganizationStatus(org)"
              >
                {{ org.is_active ? 'Suspend' : 'Activate' }}
              </Button>
              <Button
                variant="destructive"
                size="sm"
                v-if="isOwner(org)"
                @click="deleteOrganization(org)"
                :disabled="loadingDelete"
              >
                {{ loadingDelete ? 'Deleting...' : 'Delete' }}
              </Button>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- Invite Section -->
    <Card v-if="canInvite && selectedInviteOrg">
      <CardHeader>
        <CardTitle class="text-sm">Invite Users</CardTitle>
        <CardDescription>
          Send collaboration invites. Selected: <strong>{{ selectedInviteOrg.brand_name || selectedInviteOrg.name }}</strong>
        </CardDescription>
      </CardHeader>
      
      <CardContent class="space-y-4">
        <!-- Target Organization Picker Buttons -->
        <div class="space-y-1.5">
          <label class="text-xs font-semibold text-neutral-500">Target Organization</label>
          <div class="flex flex-wrap gap-2">
            <Button
              v-for="org in adminOrganizations"
              :key="org.id"
              :variant="selectedInviteTenantId === org.id || (!selectedInviteTenantId && adminOrganizations[0].id === org.id) ? 'default' : 'outline'"
              size="sm"
              @click="selectedInviteTenantId = org.id"
            >
              {{ org.brand_name || org.name }}
            </Button>
          </div>
        </div>

        <div class="grid gap-4 sm:grid-cols-2">
          <div class="grid gap-1.5">
            <label class="text-xs font-semibold text-neutral-500">User Email</label>
            <Input v-model="inviteForm.email" type="email" placeholder="teammate@company.com" />
          </div>

          <div class="grid gap-1.5">
            <label class="text-xs font-semibold text-neutral-500">Role</label>
            <Select v-model="inviteForm.role">
              <option value="analyst">Analyst</option>
              <option value="manager">Manager</option>
              <option value="admin">Admin</option>
            </Select>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <Button @click="inviteUser" :disabled="loadingInvite">
            {{ loadingInvite ? 'Inviting...' : 'Send Invite' }}
          </Button>
        </div>

        <p v-if="inviteError" class="text-xs text-red-600 bg-red-50 border border-red-200 rounded-md p-3">
          {{ inviteError }}
        </p>
        <p v-if="inviteSuccess" class="text-xs text-green-600 bg-green-50 border border-green-200 rounded-md p-3">
          {{ inviteSuccess }}
        </p>
      </CardContent>
    </Card>

    <!-- Create Organization Section -->
    <Card>
      <CardHeader>
        <CardTitle class="text-sm">Create Organization</CardTitle>
        <CardDescription>Establish a new brand profile. Cost: <strong>100 credits</strong></CardDescription>
      </CardHeader>
      
      <CardContent class="space-y-4">
        <div class="grid gap-4 sm:grid-cols-2">
          <div class="grid gap-1.5">
            <label class="text-xs font-semibold text-neutral-500">System Name (unique key)</label>
            <Input v-model="form.name" placeholder="acme_corp" />
          </div>

          <div class="grid gap-1.5">
            <label class="text-xs font-semibold text-neutral-500">Brand Name (display name)</label>
            <Input v-model="form.brand_name" placeholder="Acme" />
          </div>
        </div>

        <div class="grid gap-1.5">
          <label class="text-xs font-semibold text-neutral-500">Keywords (comma separated)</label>
          <Input v-model="form.keywords" placeholder="Acme, delivery, support" />
        </div>

        <div class="flex items-center gap-2">
          <Button @click="createOrganization" :disabled="loading">
            {{ loading ? 'Creating...' : 'Create Organization' }}
          </Button>
          <Button variant="ghost" @click="router.push('/dashboard')">
            Back to Dashboard
          </Button>
        </div>

        <p v-if="error" class="text-xs text-red-600 bg-red-50 border border-red-200 rounded-md p-3">
          {{ error }}
        </p>
        <p v-if="success" class="text-xs text-green-600 bg-green-50 border border-green-200 rounded-md p-3">
          {{ success }}
        </p>
      </CardContent>
    </Card>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import api from '../api/api';
import Card from '../components/ui/Card.vue';
import CardHeader from '../components/ui/CardHeader.vue';
import CardTitle from '../components/ui/CardTitle.vue';
import CardDescription from '../components/ui/CardDescription.vue';
import CardContent from '../components/ui/CardContent.vue';
import Button from '../components/ui/Button.vue';
import Input from '../components/ui/Input.vue';
import Select from '../components/ui/Select.vue';
import Badge from '../components/ui/Badge.vue';

const router = useRouter();
const auth = useAuthStore();

const loading = ref(false);
const loadingInvite = ref(false);
const loadingDelete = ref(false);
const error = ref('');
const success = ref('');
const inviteError = ref('');
const inviteSuccess = ref('');

const form = reactive({
  name: '',
  brand_name: '',
  keywords: '',
});

const inviteForm = reactive({
  email: '',
  role: 'analyst',
});

const user = computed(() => auth.user);
const organizations = computed(() => auth.user?.organizations || []);
const activeTenantId = computed(() => auth.activeTenantId ? Number(auth.activeTenantId) : null);

const activeTenantIdModel = computed({
  get: () => activeTenantId.value,
  set: (tenantId) => {
    if (tenantId && Number(tenantId) !== activeTenantId.value) {
      auth.setActiveTenant(Number(tenantId));
    }
  },
});

const selectedInviteTenantId = ref(null);

const adminOrganizations = computed(() => organizations.value.filter((org) => org.role === 'admin'));
const canInvite = computed(() => adminOrganizations.value.length > 0);

const selectedInviteOrg = computed(() => {
  if (!selectedInviteTenantId.value) {
    return adminOrganizations.value[0] || null;
  }
  return adminOrganizations.value.find((org) => org.id === selectedInviteTenantId.value) || adminOrganizations.value[0] || null;
});

const isOwner = (org) => Number(org.owner_id) === Number(user.value?.id);

const createOrganization = async () => {
  error.value = '';
  success.value = '';
  loading.value = true;
  try {
    const res = await api.post('/organization', form);
    success.value = res.data.msg || 'Organization created successfully!';
    form.name = '';
    form.brand_name = '';
    form.keywords = '';
    await auth.fetchMe();
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to create organization.';
  } finally {
    loading.value = false;
  }
};

const inviteUser = async () => {
  inviteError.value = '';
  inviteSuccess.value = '';
  const targetOrg = selectedInviteOrg.value;
  if (!targetOrg) {
    inviteError.value = 'Please select an organization to invite the user into.';
    return;
  }

  loadingInvite.value = true;
  try {
    const res = await api.post('/admin/users', {
      email: inviteForm.email,
      role: inviteForm.role,
      tenant_id: targetOrg.id,
    });
    inviteSuccess.value = res.data.msg || 'User invited successfully!';
    inviteForm.email = '';
  } catch (err) {
    inviteError.value = err.response?.data?.detail || 'Failed to invite user.';
  } finally {
    loadingInvite.value = false;
  }
};

const toggleOrganizationStatus = async (org) => {
  try {
    const action = org.is_active ? 'suspend' : 'activate';
    const res = await api.post(`/organization/${org.id}/${action}`);
    await auth.fetchMe();
  } catch (err) {
    console.error(err);
  }
};

const deleteOrganization = async (org) => {
  if (!confirm(`Are you sure you want to delete organization ${org.brand_name || org.name}?`)) {
    return;
  }

  loadingDelete.value = true;
  try {
    await api.delete(`/organization/${org.id}`);
    await auth.fetchMe();
  } catch (err) {
    console.error(err);
  } finally {
    loadingDelete.value = false;
  }
};

onMounted(async () => {
  if (!auth.user) {
    await auth.fetchMe();
  }
  if (adminOrganizations.value.length > 0) {
    selectedInviteTenantId.value = adminOrganizations.value[0].id;
  }
});
</script>
