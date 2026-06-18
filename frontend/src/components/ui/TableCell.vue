<template>
  <td :class="['p-4 align-middle [&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]', $attrs.class]" v-bind="$attrs">
    <slot />
  </td>
</template>
