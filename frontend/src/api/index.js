import http from './http'

export const getDatasetStats   = () => http.get('/api/dataset/stats')
export const getDatasetSamples = () => http.get('/api/dataset/samples')
export const getMetricsSummary = () => http.get('/api/metrics/summary')
export const getMetricsCurves = () => http.get('/api/metrics/curves')
export const getMetricsCases = () => http.get('/api/metrics/cases')
export const getMetricsComparison = () => http.get('/api/metrics/comparison')
export const getConfusionMatrix = () => http.get('/api/metrics/confusion-matrix')
export const getAugmentationPreview = (breed = 'samoyed') => http.get(`/api/dataset/augmentation?breed=${breed}`)

export const inferMultitask = (file) => {
  const form = new FormData()
  form.append('file', file)
  return http.post('/api/infer/multitask', form, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export const inferCompare = (file) => {
  const form = new FormData()
  form.append('file', file)
  return http.post('/api/infer/compare', form, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export const inferGradcam = (file) => {
  const form = new FormData()
  form.append('file', file)
  return http.post('/api/infer/gradcam', form, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export const submitFeedback = (payload) => http.post('/api/feedback', payload)
export const getFeedbackRecent = (limit = 20) => http.get(`/api/feedback/recent?limit=${limit}`)
export const getFeedbackStats = () => http.get('/api/feedback/stats')
