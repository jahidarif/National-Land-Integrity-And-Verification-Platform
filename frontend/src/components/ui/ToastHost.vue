<template>
  <div class="toast-host" aria-live="polite">
    <div v-for="toast in toastState.items" :key="toast.id" class="toast-item" :class="toast.kind">
      <span>{{toast.message}}</span>
      <IconButton icon="cancel" label="Dismiss notification" @click="dismissToast(toast.id)"/>
    </div>
  </div>
  <div v-if="toastState.dialog" class="alert-dialog-backdrop" role="presentation" @click.self="dismissDialog">
    <section class="alert-dialog" role="alertdialog" aria-modal="true" aria-labelledby="alert-dialog-title" aria-describedby="alert-dialog-message">
      <div class="alert-dialog-icon" aria-hidden="true">!</div>
      <h2 id="alert-dialog-title">Something went wrong</h2>
      <p id="alert-dialog-message">{{toastState.dialog.message}}</p>
      <button class="alert-dialog-button" type="button" @click="dismissDialog">OK</button>
    </section>
  </div>
</template>
<script setup lang="ts">
import IconButton from './IconButton.vue';
import {toastState,dismissToast,dismissDialog} from '@/composables/useNotify';
</script>
