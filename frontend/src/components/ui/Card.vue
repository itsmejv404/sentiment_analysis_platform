<template>
  <div :class="['rounded-lg border border-border bg-card text-card-foreground shadow-sm', $attrs.class]" v-bind="$attrs">
    <slot />
  </div>
</template>
