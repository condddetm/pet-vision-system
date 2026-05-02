/**
 * API 封装层测试
 *
 * 通过 mock http 客户端验证：
 *  - 各端点 URL 正确
 *  - 上传类接口构造 FormData
 *  - 反馈接口透传 JSON 负载
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

// 必须在 import 被测模块之前 mock 依赖
vi.mock('../src/api/http', () => ({
  default: {
    get: vi.fn(() => Promise.resolve({ data: {} })),
    post: vi.fn(() => Promise.resolve({ data: {} })),
  },
}))

const http = (await import('../src/api/http')).default
const api = await import('../src/api/index.js')

beforeEach(() => {
  http.get.mockClear()
  http.post.mockClear()
})

describe('GET 类接口 URL', () => {
  it('getDatasetStats 调用 /api/dataset/stats', () => {
    api.getDatasetStats()
    expect(http.get).toHaveBeenCalledWith('/api/dataset/stats')
  })

  it('getMetricsSummary 调用 /api/metrics/summary', () => {
    api.getMetricsSummary()
    expect(http.get).toHaveBeenCalledWith('/api/metrics/summary')
  })

  it('getConfusionMatrix 调用 /api/metrics/confusion-matrix', () => {
    api.getConfusionMatrix()
    expect(http.get).toHaveBeenCalledWith('/api/metrics/confusion-matrix')
  })

  it('getAugmentationPreview 拼接 breed 查询参数', () => {
    api.getAugmentationPreview('beagle')
    expect(http.get).toHaveBeenCalledWith('/api/dataset/augmentation?breed=beagle')
  })

  it('getFeedbackRecent 拼接 limit', () => {
    api.getFeedbackRecent(50)
    expect(http.get).toHaveBeenCalledWith('/api/feedback/recent?limit=50')
  })
})

describe('上传推理接口', () => {
  const fakeFile = new Blob([new Uint8Array([0xff, 0xd8])], { type: 'image/jpeg' })

  it('inferMultitask 走 POST + multipart', () => {
    api.inferMultitask(fakeFile)
    expect(http.post).toHaveBeenCalledTimes(1)
    const [url, formData, config] = http.post.mock.calls[0]
    expect(url).toBe('/api/infer/multitask')
    expect(formData).toBeInstanceOf(FormData)
    expect(config.headers['Content-Type']).toBe('multipart/form-data')
  })

  it('inferCompare 端点正确', () => {
    api.inferCompare(fakeFile)
    expect(http.post.mock.calls[0][0]).toBe('/api/infer/compare')
  })

  it('inferGradcam 端点正确', () => {
    api.inferGradcam(fakeFile)
    expect(http.post.mock.calls[0][0]).toBe('/api/infer/gradcam')
  })
})

describe('反馈接口', () => {
  it('submitFeedback 直传 JSON 负载', () => {
    const payload = {
      predicted_breed: 'Maine_Coon',
      predicted_confidence: 0.9,
      correct_breed: 'Russian_Blue',
    }
    api.submitFeedback(payload)
    expect(http.post).toHaveBeenCalledWith('/api/feedback', payload)
  })
})
