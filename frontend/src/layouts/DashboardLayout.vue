<template>
  <div class="dashboard-shell">
    <aside class="dash-sidebar">
      <div class="dash-brand"><span class="dash-mark">LI</span><span><b>LAND.INTEGRITY</b><small>NATIONAL LAND PLATFORM</small></span></div>
      <div class="dash-role"><span class="role-dot"/><span>{{ roleLabel }}</span></div>
      <nav class="dash-nav">
        <template v-if="user?.role === 'Admin'">
          <router-link to="/dashboard/admin/officers"><span>♙</span>Land Officers</router-link>
          <router-link to="/dashboard/admin/areas"><span>⌖</span>Areas</router-link>
        </template>
        <template v-else-if="user?.role === 'LandOfficer'">
          <router-link to="/dashboard/landofficer/lands"><span>▦</span>Lands</router-link>
          <router-link to="/dashboard/landofficer/drafts/updates"><span>◷</span>Draft updates</router-link>
          <router-link to="/dashboard/landofficer/drafts/creates"><span>▤</span>Draft creates</router-link>
          <router-link to="/chat"><span>◌</span>Maira chat</router-link>
        </template>
        <template v-else>
          <router-link to="/dashboard/user/lands"><span>▦</span>My Lands</router-link>
          <router-link to="/dashboard/user/documents"><span>▧</span>Documents</router-link>
          <router-link to="/chat"><span>◌</span>Maira chat</router-link>
        </template>
      </nav>
      <div class="dash-side-bottom"><div class="profile-mini"><span class="profile-avatar">{{ initials }}</span><span><b>{{ user?.fullName || 'Account' }}</b><small>{{ user?.email }}</small></span></div><IconButton icon="logout" label="Sign out" @click="logout"/></div>
    </aside>
    <main class="dash-main"><header class="dash-topbar"><div><span class="dash-kicker">NATIONAL LAND INTEGRITY PLATFORM</span><h1>{{ pageTitle }}</h1></div><span class="prototype-pill">DEMO ENVIRONMENT</span></header><section class="dash-content"><router-view/></section></main>
    <ChatDock ref="chatDock" v-if="user?.role === 'User' || user?.role === 'LandOfficer'"/>
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'; import { useStore } from 'vuex'; import { useRouter, useRoute } from 'vue-router'; import IconButton from '@/components/ui/IconButton.vue'; import ChatDock from '@/components/chat/ChatDock.vue';
const store=useStore(), router=useRouter(), route=useRoute(); const user=computed(()=>store.getters['auth/user']); const chatDock=ref<InstanceType<typeof ChatDock>|null>(null); function openChatFromRoute(){if(route.query.openChat==='1'){chatDock.value?.newWindow();router.replace({path:route.path,query:{...route.query,openChat:undefined}})}} onMounted(openChatFromRoute); watch(()=>route.query.openChat,openChatFromRoute);
const roleLabel=computed(()=>user.value?.role==='Admin'?'SYSTEM ADMINISTRATOR':user.value?.role==='LandOfficer'?'LAND OFFICER':'CITIZEN ACCOUNT');
const initials=computed(()=>String(user.value?.fullName||'U').split(' ').map((x:string)=>x[0]).slice(0,2).join('').toUpperCase());
const pageTitle=computed(()=>({officers:'Land Officers',areas:'Areas',lands:'Land Records',updates:'Draft Updates',creates:'Draft Creates',documents:'My Documents'}[String(route.name||'').split('-').pop()||'']||'Land Integrity'));
async function logout(){await store.dispatch('auth/logout');await router.replace('/auth/login')}
</script>
