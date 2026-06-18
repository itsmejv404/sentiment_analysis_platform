<template>
  <div :class="['flex flex-col space-y-1.5 p-6', $attrs.class]" v-bind="$attrs">
    <slot />
  </div>
</template>
