<template>
  <div v-if="activeTab === value" :class="['mt-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-black focus-visible:ring-offset-2', $attrs.class]" v-bind="$attrs">
    <slot />
  </div>
</template>

<script setup>
import { inject } from 'vue';

const props = defineProps({
  value: {
    type: String,
    required: true,
  },
});

const activeTab = inject('activeTab');
</script>
