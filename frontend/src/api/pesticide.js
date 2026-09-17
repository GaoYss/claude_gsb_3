import { createResourceApi } from './client'
import http from './client'

export const pesticideApi = {
  ...createResourceApi('pesticides'),
  options: (params) => http.get('/pesticides/options', { params }),
}

export const pesticideRequisitionApi = {
  ...createResourceApi('pesticide-requisitions'),
  summary: (params) => http.get('/pesticide-requisitions/summary', { params }),
  // 覆盖 create：force 不用于领用；保留标准创建
  returns: (id, payload) => http.patch(`/pesticide-requisitions/${id}/return`, payload),
}

export const pesticideApplicationApi = {
  ...createResourceApi('pesticide-applications'),
  summary: (params) => http.get('/pesticide-applications/summary', { params }),
  create: (payload, { force = false } = {}) =>
    http.post('/pesticide-applications', payload, { params: force ? { force: true } : {} }),
  update: (id, payload, { force = false } = {}) =>
    http.put(`/pesticide-applications/${id}`, payload, { params: force ? { force: true } : {} }),
}
