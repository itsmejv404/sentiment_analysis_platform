<template>
  <div class="space-y-6 bg-transparent text-foreground">
    <!-- Header Card -->
    <div class="border border-border rounded-lg p-4 bg-card text-card-foreground shadow-sm space-y-1">
      <p class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Payments</p>
      <h2 class="text-2xl font-bold text-foreground">Billing</h2>
      <p class="text-xs text-muted-foreground">Purchase credits securely with Razorpay. Credits are added immediately after verification.</p>
    </div>

    <!-- Plans Grid -->
    <div class="grid gap-4 sm:grid-cols-3">
      <Card v-for="plan in creditPlans" :key="plan.id" class="flex flex-col justify-between">
        <CardHeader>
          <CardTitle class="text-lg font-bold text-center">{{ plan.credits.toLocaleString() }} Credits</CardTitle>
          <CardDescription class="text-center font-mono text-sm text-neutral-500 pt-1">
            Rs {{ plan.price_rs.toLocaleString() }}
          </CardDescription>
        </CardHeader>
        
        <CardContent class="text-center text-xs text-neutral-500 space-y-2">
          <p>Instant activation upon checkout approval.</p>
          <p>Valuable for keyword watches and AI sentiment prompts.</p>
        </CardContent>

        <CardFooter class="mt-auto pt-4 border-t border-neutral-100 flex justify-center">
          <Button
            class="w-full"
            :disabled="checkoutLoading || processingPlanId === plan.id"
            @click="startCheckout(plan)"
          >
            {{ processingPlanId === plan.id ? 'Processing...' : 'Buy Now' }}
          </Button>
        </CardFooter>
      </Card>
    </div>

    <p v-if="paymentMessage" class="text-xs text-green-600 bg-green-50 border border-green-200 rounded-md p-3">
      {{ paymentMessage }}
    </p>
    <p v-if="paymentError" class="text-xs text-red-600 bg-red-50 border border-red-200 rounded-md p-3">
      {{ paymentError }}
    </p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useAuthStore } from '../stores/auth';
import api from '../api/api';
import Card from '../components/ui/Card.vue';
import CardHeader from '../components/ui/CardHeader.vue';
import CardTitle from '../components/ui/CardTitle.vue';
import CardDescription from '../components/ui/CardDescription.vue';
import CardContent from '../components/ui/CardContent.vue';
import CardFooter from '../components/ui/CardFooter.vue';
import Button from '../components/ui/Button.vue';

const auth = useAuthStore();
const user = computed(() => auth.user);

const paymentMessage = ref('');
const paymentError = ref('');
const checkoutLoading = ref(false);
const processingPlanId = ref(null);
const creditPlans = ref([
  { id: 'starter_1000', credits: 1000, price_rs: 500, amount_paise: 50000, currency: 'INR' },
  { id: 'growth_5000', credits: 5000, price_rs: 2000, amount_paise: 200000, currency: 'INR' },
  { id: 'scale_30000', credits: 30000, price_rs: 10000, amount_paise: 1000000, currency: 'INR' },
]);

const loadRazorpayScript = async () => {
  if (window.Razorpay) return true;

  return await new Promise((resolve) => {
    const existing = document.querySelector('script[data-razorpay-checkout="true"]');
    if (existing) {
      existing.addEventListener('load', () => resolve(true), { once: true });
      existing.addEventListener('error', () => resolve(false), { once: true });
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://checkout.razorpay.com/v1/checkout.js';
    script.async = true;
    script.dataset.razorpayCheckout = 'true';
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
};

const fetchCreditPlans = async () => {
  try {
    const res = await api.get('/billing/plans');
    if (Array.isArray(res.data?.plans) && res.data.plans.length > 0) {
      creditPlans.value = res.data.plans;
    }
  } catch (error) {
    console.error('Failed to fetch plans. Using fallback plans.', error);
  }
};

const startCheckout = async (plan) => {
  checkoutLoading.value = true;
  processingPlanId.value = plan.id;
  paymentMessage.value = '';
  paymentError.value = '';

  try {
    const scriptReady = await loadRazorpayScript();
    if (!scriptReady) {
      paymentError.value = 'Unable to load Razorpay Checkout. Please try again.';
      return;
    }

    const orderRes = await api.post('/billing/razorpay/order', { plan_id: plan.id });
    const order = orderRes.data;

    const options = {
      key: order.key_id,
      amount: order.amount,
      currency: order.currency,
      name: 'BrandPulse',
      description: `${plan.credits.toLocaleString()} credits`,
      order_id: order.order_id,
      prefill: {
        email: user.value?.username || '',
      },
      theme: {
        color: '#000000', // Black theme for Razorpay to fit Vercel-style
      },
      handler: async (response) => {
        try {
          const verifyRes = await api.post('/billing/razorpay/verify', {
            plan_id: plan.id,
            razorpay_order_id: response.razorpay_order_id,
            razorpay_payment_id: response.razorpay_payment_id,
            razorpay_signature: response.razorpay_signature,
          });

          paymentMessage.value = verifyRes.data?.msg || 'Payment successful. Credits added.';
          await auth.fetchMe();
        } catch (verifyError) {
          paymentError.value = verifyError.response?.data?.detail || 'Payment verification failed.';
        }
      },
      modal: {
        ondismiss: () => {
          if (!paymentMessage.value) {
            paymentError.value = 'Payment cancelled. No credits were added.';
          }
        },
      },
    };

    const rzp = new window.Razorpay(options);
    rzp.open();
  } catch (error) {
    paymentError.value = error.response?.data?.detail || 'Failed to start payment.';
  } finally {
    checkoutLoading.value = false;
    processingPlanId.value = null;
  }
};

onMounted(async () => {
  if (!auth.user) {
    await auth.fetchMe();
  }
  await fetchCreditPlans();
});
</script>
