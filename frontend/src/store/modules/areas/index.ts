import type { Module } from 'vuex';
import { state } from './state'; import { getters } from './getters'; import { mutations } from './mutations'; import { actions } from './actions';
const module:Module<any,any>={namespaced:true,state,getters,mutations,actions}; export default module;
