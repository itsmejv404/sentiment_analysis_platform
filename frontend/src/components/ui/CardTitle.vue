<template>
  <h3 :class="['text-xl font-semibold leading-none tracking-tight text-foreground', $attrs.class]" v-bind="$attrs">
    <slot />
  </h3>
</template>
