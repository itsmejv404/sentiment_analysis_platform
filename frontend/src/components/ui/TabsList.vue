<template>
  <div
    :class="[
      'inline-flex h-9 items-center justify-center rounded-lg bg-muted p-1 text-muted-foreground border border-border',
      $attrs.class
    ]"
    v-bind="$attrs"
  >
    <slot />
  </div>
</template>
