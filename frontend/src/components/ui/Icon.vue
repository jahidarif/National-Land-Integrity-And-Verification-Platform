<template><svg class="ui-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="icons[name]||icons.info"/></template>
<script setup lang="ts">import{icons}from'./icons';defineProps<{name:string}>();</script>
