import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 5000,
})

export const getCages = () => api.get('/cages').then(res => res.data)

export const getCageDetail = (id) => api.get(`/cages/${id}`).then(res => res.data)

export const getCageHistory = (id, hours = 24) =>
  api.get(`/cages/${id}/history?hours=${hours}`).then(res => res.data)

export const randomUpdate = () => api.post('/sensor/random-update').then(res => res.data)

export default api
