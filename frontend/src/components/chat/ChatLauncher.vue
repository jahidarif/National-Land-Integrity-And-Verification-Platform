<template><div class="chat-dock-launcher"><IconButton icon="chat" label="New conversation" @click="$emit('open')"/><span v-if="count" class="dock-count">{{count}}</span></div></template>
<script setup lang="ts">import IconButton from'@/components/ui/IconButton.vue';defineProps<{count:number}>();defineEmits<{open:[]}>();</script>
