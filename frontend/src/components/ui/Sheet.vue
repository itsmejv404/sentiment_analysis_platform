<template>
  <Teleport to="body">
    <Transition
      enter-active-class="ease-out duration-300"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="ease-in duration-200"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="open" class="fixed inset-0 z-50 flex">
        <!-- Backdrop -->
        <div class="fixed inset-0 bg-black/60 transition-opacity" @click="onClose" />

        <!-- Drawer Content -->
        <Transition
          enter-active-class="transform transition ease-in-out duration-300 sm:duration-300"
          :enter-from-class="side === 'left' ? '-translate-x-full' : 'translate-x-full'"
          enter-to-class="translate-x-0"
          leave-active-class="transform transition ease-in-out duration-300 sm:duration-300"
          leave-from-class="translate-x-0"
          :leave-to-class="side === 'left' ? '-translate-x-full' : 'translate-x-full'"
        >
          <div
            v-if="open"
            :class="[
              'relative flex w-full max-w-xs flex-col bg-background text-foreground p-6 shadow-xl border-border focus:outline-none h-full',
              side === 'left' ? 'mr-auto border-r' : 'ml-auto border-l',
              $attrs.class
            ]"
          >
            <!-- Close Trigger -->
            <button
              class="absolute right-4 top-4 rounded-sm opacity-70 transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring text-neutral-500 hover:text-neutral-900 dark:hover:text-neutral-50"
              @click="onClose"
            >
              <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
              <span class="sr-only">Close</span>
            </button>

            <slot />
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
  side: {
    type: String,
    default: 'right', // or 'left'
  },
});

const emit = defineEmits(['close']);

const onClose = () => {
  emit('close');
};
</script>
