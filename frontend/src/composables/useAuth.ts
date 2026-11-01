import { computed } from 'vue';import { useStore } from 'vuex';
export function useAuth(){const store=useStore();const user=computed(()=>store.getters['auth/user']);const isAuthenticated=computed(()=>!!user.value);const role=computed(()=>user.value?.role||null);const logout=()=>store.dispatch('auth/logout');return{user,isAuthenticated,role,logout}}
