<template>
  <tbody :class="['[&_tr:last-child]:border-0', $attrs.class]" v-bind="$attrs">
    <slot />
  </tbody>
</template>
