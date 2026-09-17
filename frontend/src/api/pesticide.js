import http, { createResourceApi } from './client'

const pesticideBase = createResourceApi('pesticides')

/** 药剂档案 */
export const pesticideApi = {
  ...pesticideBase,
  options: (params) => http.get('/pesticides/options', { params }),
  summary: (params) => http.get('/pesticides/summary', { params }),
}

/** 药剂出入库流水（不支持修改，删除即回滚库存） */
export const stockMovementApi = {
  list: (params) => http.get('/pesticide-stock-movements', { params }),
  detail: (id) => http.get(`/pesticide-stock-movements/${id}`),
  create: (payload) => http.post('/pesticide-stock-movements', payload),
  remove: (id) => http.delete(`/pesticide-stock-movements/${id}`),
}

/** 施药记录：登记/更新在间隔期冲突时需带 confirm=true 二次确认；409 由表单弹窗处理，不走全局报错 */
export const pesticideApplicationApi = {
  list: (params) => http.get('/pesticide-applications', { params }),
  summary: (params) => http.get('/pesticide-applications/summary', { params }),
  detail: (id) => http.get(`/pesticide-applications/${id}`),
  create: (payload, confirm = false) =>
    http.post('/pesticide-applications', payload, {
      params: confirm ? { confirm: 'true' } : {},
      skipErrorMessage: true,
    }),
  update: (id, payload, confirm = false) =>
    http.put(`/pesticide-applications/${id}`, payload, {
      params: confirm ? { confirm: 'true' } : {},
      skipErrorMessage: true,
    }),
  remove: (id) => http.delete(`/pesticide-applications/${id}`),
  intervalCheck: (params) =>
    http.get('/pesticide-applications/interval-check', { params, skipErrorMessage: true }),
}
