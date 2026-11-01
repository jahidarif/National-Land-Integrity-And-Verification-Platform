export function formatDate(value:string|null|undefined){if(!value)return'—';const date=new Date(value);return Number.isNaN(date.getTime())?value:date.toLocaleDateString()}
export function formatBytes(value:number){if(value<1024)return`${value} B`;if(value<1024*1024)return`${(value/1024).toFixed(1)} KB`;return`${(value/1024/1024).toFixed(1)} MB`}
