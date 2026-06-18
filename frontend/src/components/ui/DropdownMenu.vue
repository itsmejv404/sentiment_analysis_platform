<template>
  <div class="relative inline-block text-left" v-click-outside="close">
    <div @click="toggle" class="cursor-pointer">
      <slot name="trigger" />
    </div>

    <Transition
      enter-active-class="transition ease-out duration-100"
      enter-from-class="transform opacity-0 scale-95"
      enter-to-class="transform opacity-100 scale-100"
      leave-active-class="transition ease-in duration-75"
      leave-from-class="transform opacity-100 scale-100"
      leave-to-class="transform opacity-0 scale-95"
    >
      <div
        v-if="isOpen"
        :class="[
          'absolute right-0 z-50 mt-2 w-56 origin-top-right rounded-md border border-border bg-popover p-1 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none text-popover-foreground',
          align === 'left' ? 'left-0 origin-top-left' : 'right-0 origin-top-right',
          $attrs.class
        ]"
      >
        <slot :close="close" />
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';

const props = defineProps({
  align: {
    type: String,
    default: 'right',
  },
});

const isOpen = ref(false);

const toggle = () => {
  isOpen.value = !isOpen.value;
};

const close = () => {
  isOpen.value = false;
};

// Simple click outside directive local registration
const vClickOutside = {
  mounted(el, binding) {
    el.clickOutsideEvent = (event) => {
      if (!(el === event.target || el.contains(event.target))) {
        binding.value(event);
      }
    };
    document.body.addEventListener('click', el.clickOutsideEvent);
  },
  unmounted(el) {
    document.body.removeEventListener('click', el.clickOutsideEvent);
  },
};
</script>
