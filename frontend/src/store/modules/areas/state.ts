import type { FeatureState } from './types';
export const state = ():FeatureState => ({items:[],page:1,pageSize:10,totalCount:0,totalPages:0,hasPrevious:false,hasNext:false,loading:false,error:null});
