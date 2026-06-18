<script setup>
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import Button from '../components/ui/Button.vue';

const router = useRouter();
const hasToken = computed(() => Boolean(localStorage.getItem('token')));
</script>

<template>
  <main class="min-h-screen bg-background text-foreground flex flex-col justify-center items-center p-6 sm:p-12">
    <div class="max-w-2xl w-full text-center space-y-8">
      <!-- Brand Logo Text -->
      <div class="flex justify-center">
        <span class="font-extrabold text-3xl sm:text-4xl tracking-tighter uppercase border border-foreground px-4 py-1 rounded bg-foreground text-background inline-block">BrandPulse</span>
      </div>

      <div class="space-y-4">
        <p class="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Platform</p>
        <h1 class="text-4xl sm:text-5xl font-extrabold tracking-tight text-foreground leading-none">
          Social Media Sentiment Analytics
        </h1>
        <p class="text-base sm:text-lg text-muted-foreground max-w-lg mx-auto leading-relaxed">
          Track brand sentiment across social conversations, spot risk quickly, and drive decisions with live analytics.
        </p>
      </div>

      <div class="flex items-center justify-center gap-3">
        <Button size="lg" @click="router.push(hasToken ? '/dashboard' : '/login')">
          {{ hasToken ? 'Open Dashboard' : 'Sign In' }}
        </Button>
        <Button variant="outline" size="lg" @click="router.push('/register')">
          Create Account
        </Button>
      </div>
    </div>
  </main>
</template>
