<template>
  <main class="min-h-screen bg-background text-foreground flex flex-col justify-center items-center p-6">
    <Card class="w-full max-w-[400px]">
      <CardHeader class="space-y-1">
        <div class="flex justify-center mb-4">
          <span class="font-extrabold text-xl tracking-tighter uppercase border border-foreground px-2 py-0.5 rounded bg-foreground text-background">BrandPulse</span>
        </div>
        <CardTitle class="text-2xl text-center font-bold">Set New Password</CardTitle>
        <CardDescription class="text-center">
          Enter your new password below to update your credentials
        </CardDescription>
      </CardHeader>

      <CardContent class="grid gap-4">
        <div class="grid gap-2">
          <label for="new-password" class="text-sm font-medium text-muted-foreground">New Password</label>
          <Input id="new-password" v-model="form.new_password" type="password" placeholder="••••••••" />
        </div>

        <p v-if="error" class="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md p-3">
          {{ error }}
        </p>

        <p v-if="success" class="text-sm text-green-600 bg-green-50 border border-green-200 rounded-md p-3">
          {{ success }}
        </p>

        <Button class="w-full" @click="resetPassword" :disabled="loading || success !== ''">
          {{ loading ? 'Updating...' : 'Update Password' }}
        </Button>
      </CardContent>

      <CardFooter class="flex justify-center text-center text-xs">
        <button class="text-neutral-500 hover:text-black underline underline-offset-4" @click="router.push('/login')">
          Back to Login
        </button>
      </CardFooter>
    </Card>
  </main>
</template>

<script setup>
import { reactive, ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import api from "../api/api";
import Card from "../components/ui/Card.vue";
import CardHeader from "../components/ui/CardHeader.vue";
import CardTitle from "../components/ui/CardTitle.vue";
import CardDescription from "../components/ui/CardDescription.vue";
import CardContent from "../components/ui/CardContent.vue";
import CardFooter from "../components/ui/CardFooter.vue";
import Input from "../components/ui/Input.vue";
import Button from "../components/ui/Button.vue";

const route = useRoute();
const router = useRouter();

const form = reactive({
  token: "",
  new_password: "",
});

const error = ref("");
const success = ref("");
const loading = ref(false);

onMounted(() => {
  form.token = route.query.token || "";
  if (!form.token) {
    error.value = "Invalid or missing reset token.";
  }
});

const resetPassword = async () => {
  if (!form.token) {
    error.value = "Invalid or missing reset token.";
    return;
  }
  
  error.value = "";
  success.value = "";
  loading.value = true;
  try {
    await api.post("/reset-password", form);
    success.value = "Password updated successfully! You can now log in.";
  } catch (e) {
    error.value = e.response?.data?.detail || "Something went wrong.";
  } finally {
    loading.value = false;
  }
};
</script>
