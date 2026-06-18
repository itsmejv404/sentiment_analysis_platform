<template>
  <span
    :class="[
      'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
      variantClasses[variant] || variantClasses.default,
      $attrs.class
    ]"
    v-bind="$attrs"
  >
    <slot />
  </span>
</template>

<script setup>
const props = defineProps({
  variant: {
    type: String,
    default: 'default',
  },
});

const variantClasses = {
  default: 'border-transparent bg-primary text-primary-foreground shadow',
  secondary: 'border-transparent bg-secondary text-secondary-foreground',
  outline: 'text-foreground border-border bg-background',
  destructive: 'border-transparent bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  success: 'border-transparent bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  warning: 'border-transparent bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
};
</script>
