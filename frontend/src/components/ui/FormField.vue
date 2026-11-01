<template><label class="form-field"><span>{{label}}</span><slot/><small v-if="hint">{{hint}}</small><small v-if="error" class="form-field-error">{{error}}</small></label></template>
<script setup lang="ts">defineProps<{label:string;hint?:string;error?:string}>();</script>
