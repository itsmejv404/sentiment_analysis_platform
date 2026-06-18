<template>
  <main class="min-h-[70vh] bg-transparent text-foreground flex flex-col justify-center items-center p-6">
    <Card class="w-full max-w-[500px]">
      <CardHeader class="space-y-1">
        <p class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Administration</p>
        <CardTitle class="text-2xl font-bold">Organization Settings</CardTitle>
        <CardDescription class="text-muted-foreground">
          Invite new members to collaborate
        </CardDescription>
      </CardHeader>

      <CardContent class="space-y-4">
        <div class="grid gap-1.5">
          <label class="text-xs font-semibold text-muted-foreground">User Email</label>
          <Input v-model="form.email" type="email" placeholder="teammate@company.com" />
        </div>

        <div class="grid gap-1.5">
          <label class="text-xs font-semibold text-muted-foreground">Role</label>
          <Select v-model="form.role">
            <option value="analyst">Analyst</option>
            <option value="manager">Manager</option>
          </Select>
        </div>

        <p v-if="error" class="text-xs text-red-600 bg-red-500/10 border border-red-500/20 rounded p-3">
          {{ error }}
        </p>
        <p v-if="success" class="text-xs text-green-600 bg-green-500/10 border border-green-500/20 rounded p-3">
          {{ success }}
        </p>
      </CardContent>

      <CardFooter class="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 border-t border-border pt-4 mt-2">
        <Button variant="outline" @click="router.push('/dashboard')">
          Back to Dashboard
        </Button>
        <Button @click="inviteUser">
          Send Invite
        </Button>
      </CardFooter>
    </Card>
  </main>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import api from "../api/api";
import Card from "../components/ui/Card.vue";
import CardHeader from "../components/ui/CardHeader.vue";
import CardTitle from "../components/ui/CardTitle.vue";
import CardDescription from "../components/ui/CardDescription.vue";
import CardContent from "../components/ui/CardContent.vue";
import CardFooter from "../components/ui/CardFooter.vue";
import Button from "../components/ui/Button.vue";
import Input from "../components/ui/Input.vue";
import Select from "../components/ui/Select.vue";

const router = useRouter();

const form = reactive({
  email: "",
  role: "analyst",
});

const error = ref("");
const success = ref("");

const inviteUser = async () => {
  error.value = "";
  success.value = "";
  try {
    const res = await api.post("/admin/users", form);
    success.value = res.data.msg || "User invited successfully!";
    form.email = "";
  } catch (e) {
    error.value = e.response?.data?.detail || "Failed to invite user.";
  }
};
</script>
