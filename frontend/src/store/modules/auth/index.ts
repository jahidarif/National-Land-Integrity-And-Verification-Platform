import type{Module}from'vuex';import{state}from'./state';import{getters}from'./getters';import{mutations}from'./mutations';import{actions}from'./actions';import type{AuthState}from'./types';
const auth:Module<AuthState,any>={namespaced:true,state,getters,mutations,actions};export default auth;
