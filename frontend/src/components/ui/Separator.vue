<template>
  <div
    :class="[
      'shrink-0 bg-border',
      orientation === 'horizontal' ? 'h-[1px] w-full' : 'h-full w-[1px]',
      $attrs.class
    ]"
    v-bind="$attrs"
  />
</template>

<script setup>
defineProps({
  orientation: {
    type: String,
    default: 'horizontal', // or 'vertical'
  },
});
</script>
