import type { AuthState } from './types';
export const state=():AuthState=>({user:null,loading:false,bootstrapped:false,error:null});
