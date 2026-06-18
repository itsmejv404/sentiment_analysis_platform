<template>
  <button
    type="button"
    @click="selectTab"
    :class="[
      'inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50',
      activeTab === value
        ? 'bg-background text-foreground shadow-sm'
        : 'hover:bg-accent/50 hover:text-accent-foreground',
      $attrs.class
    ]"
    v-bind="$attrs"
  >
    <slot />
  </button>
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

const selectTab = () => {
  if (activeTab) {
    activeTab.value = props.value;
  }
};
</script>
