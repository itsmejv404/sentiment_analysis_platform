<template>
  <button
    type="button"
    :class="[
      'flex w-full items-center rounded-sm px-2 py-1.5 text-sm text-popover-foreground hover:bg-accent hover:text-accent-foreground transition-colors text-left focus:bg-accent focus:outline-none disabled:opacity-50 disabled:pointer-events-none',
      $attrs.class
    ]"
    v-bind="$attrs"
  >
    <slot />
  </button>
</template>
