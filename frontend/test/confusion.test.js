/**
 * 混淆矩阵工具函数单元测试
 *
 * 覆盖纯函数：resolveConfusionData / getPerClassStats / getConfusionInsights / getTopErrorClasses
 */
import { describe, it, expect } from 'vitest'
import {
  resolveConfusionData,
  getPerClassStats,
  getConfusionInsights,
  getTopErrorClasses,
} from '../src/utils/confusion.js'

// 测试夹具：3 类，第 0 类全对，第 1 类有 2 条混淆到第 0 类，第 2 类对角线为 0（极端）
const labels = ['A', 'B', 'C']
const matrix = [
  [10, 0, 0],   // A: 10 个全对
  [2, 8, 0],    // B: 2 个混淆为 A，8 个对
  [1, 1, 0],    // C: 全部混淆为 A 或 B
]

describe('resolveConfusionData', () => {
  it('优先使用真实数据', () => {
    const real = { labels: ['X'], matrix: [[5]] }
    const result = resolveConfusionData(real, labels, matrix)
    expect(result.labels).toEqual(['X'])
    expect(result.matrix).toEqual([[5]])
  })

  it('真实数据矩阵为空时使用 fallback', () => {
    const result = resolveConfusionData({ matrix: [] }, labels, matrix)
    expect(result.labels).toEqual(labels)
    expect(result.matrix).toEqual(matrix)
  })

  it('真实数据为 null 时使用 fallback', () => {
    const result = resolveConfusionData(null, labels, matrix)
    expect(result.labels).toEqual(labels)
  })
})

describe('getPerClassStats', () => {
  const stats = getPerClassStats(labels, matrix)

  it('返回数组长度与类别数一致', () => {
    expect(stats).toHaveLength(3)
  })

  it('类 A 准确率应为 100%', () => {
    expect(stats[0].acc).toBe(100)
    expect(stats[0].correct).toBe(10)
    expect(stats[0].errorCount).toBe(0)
    expect(stats[0].confusions).toHaveLength(0)
  })

  it('类 B 准确率应为 80%', () => {
    expect(stats[1].acc).toBe(80)
    expect(stats[1].errorCount).toBe(2)
    expect(stats[1].confusions[0]).toMatchObject({ source: 'B', target: 'A', count: 2 })
  })

  it('类 C 全部混淆 (acc=0)', () => {
    expect(stats[2].acc).toBe(0)
    expect(stats[2].correct).toBe(0)
    expect(stats[2].errorCount).toBe(2)
    expect(stats[2].confusions.length).toBe(2)
  })
})

describe('getConfusionInsights', () => {
  const insights = getConfusionInsights(labels, matrix, 5)

  it('完美类计数', () => {
    expect(insights.perfectCount).toBe(1)
    expect(insights.highAccCount).toBe(1)
  })

  it('最低准确率应为 0', () => {
    expect(insights.minAcc).toBe(0)
  })

  it('topPairs 按 count 降序', () => {
    expect(insights.topPairs.length).toBeGreaterThan(0)
    const counts = insights.topPairs.map(p => p.count)
    const sorted = [...counts].sort((a, b) => b - a)
    expect(counts).toEqual(sorted)
  })
})

describe('getTopErrorClasses', () => {
  it('完美类不应出现在错误榜', () => {
    const top = getTopErrorClasses(labels, matrix, 10)
    expect(top.find(item => item.breed === 'A')).toBeUndefined()
  })

  it('错误率最高的类排第一', () => {
    const top = getTopErrorClasses(labels, matrix, 10)
    expect(top[0].breed).toBe('C')
    expect(top[0].rate).toBe(100)
  })

  it('结果包含期望字段', () => {
    const top = getTopErrorClasses(labels, matrix, 10)
    top.forEach(item => {
      expect(item).toHaveProperty('breed')
      expect(item).toHaveProperty('rate')
      expect(item).toHaveProperty('errorCount')
      expect(item).toHaveProperty('total')
      expect(item).toHaveProperty('similar')
    })
  })
})
