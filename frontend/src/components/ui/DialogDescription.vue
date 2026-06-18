<template>
  <p :class="['text-sm text-neutral-500', $attrs.class]" v-bind="$attrs">
    <slot />
  </p>
</template>
