<template>
  <tr :class="['border-b border-border transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted', $attrs.class]" v-bind="$attrs">
    <slot />
  </tr>
</template>
