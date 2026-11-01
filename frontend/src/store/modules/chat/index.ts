import type{Module}from'vuex';import{state}from'./state';import{getters}from'./getters';import{mutations}from'./mutations';import{actions}from'./actions';import type{ChatState}from'./types';
const chat:Module<ChatState,any>={namespaced:true,state,getters,mutations,actions};export default chat;
