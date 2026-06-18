<template>
  <div class="relative inline-block group">
    <slot />
    <div
      :class="[
        'absolute bottom-full left-1/2 z-50 mb-2 -translate-x-1/2 scale-0 rounded-md bg-neutral-900 px-2.5 py-1.5 text-xs font-medium text-white shadow-md transition-all duration-150 origin-bottom group-hover:scale-100 whitespace-nowrap',
        $attrs.class
      ]"
    >
      {{ content }}
      <slot name="content" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  content: {
    type: String,
    default: '',
  },
});
</script>
