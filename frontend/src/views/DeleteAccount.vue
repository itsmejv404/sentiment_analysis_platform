<template>
  <main class="min-h-[70vh] bg-transparent text-foreground flex flex-col justify-center items-center p-6">
    <Card class="w-full max-w-[500px] border-red-500/20 shadow-sm">
      <CardHeader class="space-y-1">
        <p class="text-xs font-semibold uppercase tracking-wider text-red-600">Danger Zone</p>
        <CardTitle class="text-2xl font-bold">Delete Account</CardTitle>
        <CardDescription class="text-muted-foreground">
          Are you sure you want to permanently delete your account?
        </CardDescription>
      </CardHeader>

      <CardContent class="space-y-4">
        <p class="text-sm font-semibold text-red-600 bg-red-500/10 border border-red-500/20 rounded p-3">
          ⚠️ Warning: This action cannot be undone and all associated organizations and records will be removed.
        </p>

        <div class="grid gap-1.5">
          <label class="text-xs font-semibold text-neutral-500">Before you go, share feedback (optional)</label>
          <textarea
            v-model="feedback"
            rows="4"
            class="flex w-full rounded-md border border-neutral-200 bg-white px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-neutral-400 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-black disabled:cursor-not-allowed disabled:opacity-50"
            placeholder="Tell us what made you leave or what we can improve"
          />
        </div>

        <p v-if="error" class="text-xs text-red-600 bg-red-50 border border-red-200 rounded p-3">
          {{ error }}
        </p>
      </CardContent>

      <CardFooter class="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 border-t border-neutral-100 pt-4 mt-2">
        <Button variant="outline" @click="router.push('/dashboard')">
          Cancel
        </Button>
        <Button variant="destructive" @click="confirmDelete">
          Yes, Delete Everything
        </Button>
      </CardFooter>
    </Card>
  </main>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import api from "../api/api";
import { useAuthStore } from "../stores/auth";
import Card from "../components/ui/Card.vue";
import CardHeader from "../components/ui/CardHeader.vue";
import CardTitle from "../components/ui/CardTitle.vue";
import CardDescription from "../components/ui/CardDescription.vue";
import CardContent from "../components/ui/CardContent.vue";
import CardFooter from "../components/ui/CardFooter.vue";
import Button from "../components/ui/Button.vue";

const router = useRouter();
const auth = useAuthStore();
const error = ref("");
const feedback = ref("");

const confirmDelete = async () => {
  try {
    error.value = "";
    await api.delete("/me", {
      data: {
        feedback: feedback.value,
      },
    });
    auth.logout();
    router.push("/login");
  } catch (e) {
    error.value = "Failed to delete account. Please try again.";
    console.error(e);
  }
};
</script>
