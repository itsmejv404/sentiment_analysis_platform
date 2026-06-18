<template>
  <p :class="['text-sm text-muted-foreground', $attrs.class]" v-bind="$attrs">
    <slot />
  </p>
</template>
