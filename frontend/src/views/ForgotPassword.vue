<template>
  <main class="min-h-screen bg-background text-foreground flex flex-col justify-center items-center p-6">
    <Card class="w-full max-w-[400px]">
      <CardHeader class="space-y-1">
        <div class="flex justify-center mb-4">
          <span class="font-extrabold text-xl tracking-tighter uppercase border border-foreground px-2 py-0.5 rounded bg-foreground text-background">BrandPulse</span>
        </div>
        <CardTitle class="text-2xl text-center font-bold">Forgot Password</CardTitle>
        <CardDescription class="text-center">
          Enter your email to receive a password reset link
        </CardDescription>
      </CardHeader>

      <CardContent class="grid gap-4">
        <div class="grid gap-2">
          <label for="email" class="text-sm font-medium text-muted-foreground">Email</label>
          <Input id="email" v-model="form.email" type="email" placeholder="you@company.com" />
        </div>

        <p v-if="error" class="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md p-3">
          {{ error }}
        </p>

        <p v-if="success" class="text-sm text-green-600 bg-green-50 border border-green-200 rounded-md p-3">
          {{ success }}
        </p>

        <Button class="w-full" @click="forgotPassword" :disabled="loading">
          {{ loading ? 'Sending reset link...' : 'Send Password Reset Link' }}
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
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import api from "../api/api";
import Card from "../components/ui/Card.vue";
import CardHeader from "../components/ui/CardHeader.vue";
import CardTitle from "../components/ui/CardTitle.vue";
import CardDescription from "../components/ui/CardDescription.vue";
import CardContent from "../components/ui/CardContent.vue";
import CardFooter from "../components/ui/CardFooter.vue";
import Input from "../components/ui/Input.vue";
import Button from "../components/ui/Button.vue";

const router = useRouter();

const form = reactive({
  email: "",
});

const error = ref("");
const success = ref("");
const loading = ref(false);

const forgotPassword = async () => {
  error.value = "";
  success.value = "";
  loading.value = true;
  try {
    await api.post("/forgot-password", form);
    success.value = "Check your Inbox for a reset link.";
  } catch (e) {
    error.value = e.response?.data?.detail || "Something went wrong. Please check the email entered.";
  } finally {
    loading.value = false;
  }
};
</script>