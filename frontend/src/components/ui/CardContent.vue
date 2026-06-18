<template>
  <div :class="['p-6 pt-0', $attrs.class]" v-bind="$attrs">
    <slot />
  </div>
</template>
