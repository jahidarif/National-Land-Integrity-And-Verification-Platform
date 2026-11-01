import type { User } from '@/types';
export const mutations={SET_USER(s:any,user:User|null){s.user=user},SET_LOADING(s:any,v:boolean){s.loading=v},SET_BOOTSTRAPPED(s:any,v:boolean){s.bootstrapped=v},SET_ERROR(s:any,v:string|null){s.error=v}};
