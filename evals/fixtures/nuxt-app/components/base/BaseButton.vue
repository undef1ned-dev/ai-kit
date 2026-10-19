<script setup lang="ts">
withDefaults(defineProps<{ variant?: "primary" | "secondary"; disabled?: boolean }>(), {
  variant: "primary",
  disabled: false,
})

const emit = defineEmits<{ click: [event: MouseEvent] }>()
</script>

<template>
  <button
    type="button"
    :class="['base-button', `base-button--${variant}`]"
    :disabled="disabled"
    data-test="base-button"
    @click="emit('click', $event)"
  >
    <slot />
  </button>
</template>
