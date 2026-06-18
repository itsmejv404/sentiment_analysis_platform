<template>
  <div :class="['w-full', $attrs.class]" v-bind="$attrs">
    <slot />
  </div>
</template>

<script setup>
import { provide, ref, watch } from 'vue';

const props = defineProps({
  defaultValue: {
    type: String,
    required: true,
  },
  modelValue: {
    type: String,
    default: undefined,
  },
});

const emit = defineEmits(['update:modelValue']);

const activeTab = ref(props.modelValue !== undefined ? props.modelValue : props.defaultValue);

watch(() => props.modelValue, (newVal) => {
  if (newVal !== undefined) {
    activeTab.value = newVal;
  }
});

watch(activeTab, (newVal) => {
  emit('update:modelValue', newVal);
});

provide('activeTab', activeTab);
</script>
