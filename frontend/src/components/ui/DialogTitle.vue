<template>
  <h2 :class="['text-lg font-semibold leading-none tracking-tight text-neutral-900', $attrs.class]" v-bind="$attrs">
    <slot />
  </h2>
</template>
