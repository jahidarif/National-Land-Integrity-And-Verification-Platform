<template><div class="table-scroll"><table class="glass-table"><thead><slot name="head"/></thead><tbody><slot/></tbody></table><div v-if="empty" class="state-message">{{emptyLabel}}</div></div></template>
<script setup lang="ts">withDefaults(defineProps<{empty?:boolean;emptyLabel?:string}>(),{empty:false,emptyLabel:'No records found.'});</script>
