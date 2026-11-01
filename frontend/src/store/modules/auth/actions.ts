import api,{apiErrorMessage}from'@/services/api';
export const actions={
async login({commit}:any,payload:{email:string;password:string}){commit('SET_LOADING',true);commit('SET_ERROR',null);try{const{data}=await api.post('/auth/login',payload);commit('SET_USER',data);return data}catch(error){const message=apiErrorMessage(error);commit('SET_ERROR',message);throw new Error(message)}finally{commit('SET_LOADING',false);commit('SET_BOOTSTRAPPED',true)}},
async register(_ctx:any,payload:{full_name:string;role:'User'|'LandOfficer';email:string;password:string}){try{const{data}=await api.post('/auth/register',payload);return data}catch(error){throw new Error(apiErrorMessage(error))}},
async fetchCurrentUser({commit}:any){commit('SET_LOADING',true);try{const{data}=await api.get('/auth/me');commit('SET_USER',data);return data}catch{commit('SET_USER',null);throw new Error('Not signed in')}finally{commit('SET_LOADING',false);commit('SET_BOOTSTRAPPED',true)}},
async logout({commit}:any){try{await api.post('/auth/logout',{})}finally{commit('SET_USER',null);commit('SET_BOOTSTRAPPED',true);commit('chat/CLEAR_CHAT',null,{root:true})}}
};
