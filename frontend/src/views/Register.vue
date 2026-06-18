<template>
  <main class="min-h-screen bg-background text-foreground flex flex-col justify-center items-center p-6">
    <Card class="w-full max-w-[400px]">
      <CardHeader class="space-y-1">
        <div class="flex justify-center mb-4">
          <span class="font-extrabold text-xl tracking-tighter uppercase border border-foreground px-2 py-0.5 rounded bg-foreground text-background">BrandPulse</span>
        </div>
        <CardTitle class="text-2xl text-center font-bold">Create Account</CardTitle>
        <CardDescription class="text-center">
          Get started with BrandPulse analytics today
        </CardDescription>
      </CardHeader>

      <CardContent class="grid gap-4">
        <div class="grid gap-2">
          <label for="email" class="text-sm font-medium text-muted-foreground">Email</label>
          <Input id="email" v-model="form.username" type="email" placeholder="you@company.com" />
        </div>

        <div class="grid gap-2">
          <label for="password" class="text-sm font-medium text-muted-foreground">Password</label>
          <Input id="password" v-model="form.password" type="password" placeholder="Create a secure password" />
        </div>

        <div class="grid gap-2">
          <label for="role" class="text-sm font-medium text-muted-foreground">Role</label>
          <Select id="role" v-model="form.role">
            <option value="admin">Admin</option>
            <option value="manager">Manager</option>
            <option value="analyst">Analyst</option>
          </Select>
        </div>

        <p v-if="error" class="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md p-3">
          {{ error }}
        </p>

        <Button class="w-full" @click="register" :disabled="loading">
          {{ loading ? 'Creating Account...' : 'Register' }}
        </Button>
      </CardContent>

      <CardFooter class="flex justify-center text-center text-xs">
        <div class="text-neutral-500">
          Already have an account?
          <button class="text-black font-semibold hover:underline underline-offset-4" @click="router.push('/login')">
            Sign In
          </button>
        </div>
      </CardFooter>
    </Card>
  </main>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useAuthStore } from "../stores/auth";
import { useRouter } from "vue-router";
import Card from "../components/ui/Card.vue";
import CardHeader from "../components/ui/CardHeader.vue";
import CardTitle from "../components/ui/CardTitle.vue";
import CardDescription from "../components/ui/CardDescription.vue";
import CardContent from "../components/ui/CardContent.vue";
import CardFooter from "../components/ui/CardFooter.vue";
import Input from "../components/ui/Input.vue";
import Select from "../components/ui/Select.vue";
import Button from "../components/ui/Button.vue";

const auth = useAuthStore();
const router = useRouter();

const form = reactive({
  username: "",
  password: "",
  role: "admin",
});

const error = ref("");
const loading = ref(false);

const register = async () => {
  error.value = "";
  loading.value = true;
  try {
    await auth.register(form);
    router.push("/");
  } catch (e) {
    error.value = e.response?.data?.detail || "Registration failed. Please try again.";
  } finally {
    loading.value = false;
  }
};
</script>