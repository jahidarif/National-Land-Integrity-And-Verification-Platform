export interface PagedResult<T>{page:number;pageSize:number;totalCount:number;totalPages:number;hasPrevious:boolean;hasNext:boolean;items:T[]}
