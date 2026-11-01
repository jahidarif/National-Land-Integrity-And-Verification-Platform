<template>
  <AuthLayout><main class="auth-screen">
    <div class="auth-orbit orbit-one"></div><div class="auth-orbit orbit-two"></div>
    <section class="auth-brand">
      <div class="brand-lockup"><span class="brand-mark"><svg viewBox="0 0 44 44" aria-hidden="true"><path d="M22 3 39 13v18L22 41 5 31V13L22 3Z" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M13 25.5 20 13l11 18M12 30h20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></span><span><strong>LAND<span class="brand-dot">.</span>INTEGRITY</strong><small>NATIONAL LAND INTEGRITY PLATFORM</small></span></div>
      <div class="brand-copy"><span class="eyebrow light"><i></i> CITIZEN SERVICE PROTOTYPE</span><h1>Clarity for every<br><em>piece of land.</em></h1><p>A calmer, more transparent way to ask questions about land records, public services, and the journey toward trusted verification.</p>
        <div class="brand-proof"><div class="proof-icon"><svg viewBox="0 0 24 24"><path d="M12 3 20 6v5c0 5-3.5 8.2-8 10-4.5-1.8-8-5-8-10V6l8-3Z"/><path d="m8 12 2.5 2.5L16 9"/></svg></div><div><strong>Designed around public trust</strong><span>Privacy first · Human review · Clear guidance</span></div></div>
      </div>
      <div class="auth-footnote"><span>© 2026 · National Land Integrity</span><span>Prototype environment</span></div>
    </section>
    <section class="auth-form-side">
      <div class="auth-mobile-brand"><span class="brand-mark small-mark">LI</span><strong>LAND.INTEGRITY</strong></div>
      <div class="auth-form-wrap">
        <div class="auth-kicker"><span class="status-dot"></span> SECURE CITIZEN ACCESS</div>
        <h2>{{ isRegister ? 'Create your account' : 'Welcome back' }}</h2>
        <p class="auth-subtitle">{{ isRegister ? 'Start a conversation and keep your chat history in one place.' : 'Sign in to continue your land integrity conversations.' }}</p>
        <div v-if="formError" class="auth-alert"><span>!</span>{{ formError }}</div>
        <form @submit.prevent="submit" class="auth-fields">
          <label v-if="isRegister" class="form-control"><span>Full name</span><div class="input-shell"><svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="3.5"/><path d="M5 20c.7-4 3-6 7-6s6.3 2 7 6"/></svg><input v-model.trim="form.full_name" autocomplete="name" placeholder="Your full name" required minlength="2" maxlength="120" /></div></label>
          <label v-if="isRegister" class="form-control"><span>Account type</span><div class="input-shell"><select v-model="form.role"><option value="User">User</option><option value="LandOfficer">Land Officer</option></select></div></label>
          <label class="form-control"><span>Email address</span><div class="input-shell"><svg viewBox="0 0 24 24"><rect x="3.5" y="5" width="17" height="14" rx="2"/><path d="m4.5 7 7.5 6 7.5-6"/></svg><input v-model.trim="form.email" type="email" autocomplete="email" placeholder="you@example.com" required /></div></label>
          <label class="form-control"><span>Password</span><div class="input-shell"><svg viewBox="0 0 24 24"><rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg><input v-model="form.password" :type="showPassword ? 'text' : 'password'" :autocomplete="isRegister ? 'new-password' : 'current-password'" :placeholder="isRegister ? 'At least 8 characters' : 'Enter your password'" required minlength="8" maxlength="72" /><IconButton :icon="showPassword ? 'view' : 'info'" :label="showPassword ? 'Hide password' : 'Show password'" @click="showPassword = !showPassword"/></div></label>
          <template v-if="isRegister"><label class="form-control"><span>Confirm password</span><div class="input-shell"><svg viewBox="0 0 24 24"><path d="M12 3 20 6v5c0 5-3.5 8.2-8 10-4.5-1.8-8-5-8-10V6l8-3Z"/><path d="m8.5 12 2.2 2.2 4.8-5"/></svg><input v-model="form.confirmPassword" type="password" autocomplete="new-password" placeholder="Re-enter password" required minlength="8" maxlength="72" /></div></label></template>
          <IconButton class="auth-submit-icon" icon="publish" :label="isRegister ? 'Create account' : 'Sign in securely'" type="submit" :loading="loading"/>
        </form>
        <div class="auth-switch">{{ isRegister ? 'Already have an account?' : 'New to Land Integrity?' }} <router-link :to="isRegister ? '/auth/login' : '/auth/register'">{{ isRegister ? 'Sign in' : 'Create an account' }}</router-link></div>
        <div class="auth-legal"><svg viewBox="0 0 24 24"><path d="M12 3 20 6v5c0 5-3.5 8.2-8 10-4.5-1.8-8-5-8-10V6l8-3Z"/></svg><span>Your conversations are private to your account in this prototype. Do not submit sensitive personal or ownership data.</span></div>
        <div class="prototype-note"><span>DEMO</span> Maira uses demo-trained data; live government records are not connected.</div>
      </div>
      <span class="auth-side-foot">Built for an accessible, citizen-first land service.</span>
    </section>
  </main></AuthLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import IconButton from "@/components/ui/IconButton.vue";
import AuthLayout from "@/layouts/AuthLayout.vue";
import api from "@/services/api";
import { useRoute, useRouter } from "vue-router";
import { useStore } from "vuex";
const route = useRoute(); const router = useRouter(); const store = useStore();
const isRegister = computed(() => route.path.endsWith("register"));
const form = reactive({ full_name: "", role: "User", email: "", password: "", confirmPassword: "" });
const loading = ref(false); const formError = ref(""); const showPassword = ref(false);
onMounted(async () => { try { await api.get("/auth/csrf"); } catch { formError.value = "Could not initialize a secure sign-in session. Refresh the page and try again."; } });
async function submit() {
  formError.value = "";
  if (isRegister.value && form.password !== form.confirmPassword) { formError.value = "Your passwords do not match."; return; }
  loading.value = true;
  try {
    if (isRegister.value) await store.dispatch("auth/register", { full_name: form.full_name, role: form.role, email: form.email, password: form.password });
    await store.dispatch("auth/login", { email: form.email, password: form.password });
    const role = store.getters["auth/user"]?.role; const home: Record<string,string> = { Admin: "/dashboard/admin", LandOfficer: "/dashboard/landofficer", User: "/dashboard/user" }; await router.replace(home[role] || "/dashboard");
  } catch (error) { formError.value = error instanceof Error ? error.message : "We could not complete your request. Please try again."; }
  finally { loading.value = false; }
}
</script>
