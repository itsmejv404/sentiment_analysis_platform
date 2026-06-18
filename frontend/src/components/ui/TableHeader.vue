<template>
  <thead :class="['[&_tr]:border-b border-border', $attrs.class]" v-bind="$attrs">
    <slot />
  </thead>
</template>
