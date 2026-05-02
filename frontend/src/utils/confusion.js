export function resolveConfusionData(realData, fallbackLabels = [], fallbackMatrix = []) {
  if (realData?.matrix?.length > 0) {
    return { labels: realData.labels, matrix: realData.matrix }
  }
  return { labels: fallbackLabels, matrix: fallbackMatrix }
}

export function getPerClassStats(labels, matrix) {
  return labels.map((name, index) => {
    const row = matrix[index] ?? []
    const total = row.reduce((sum, value) => sum + value, 0)
    const correct = row[index] ?? 0
    const errorCount = total - correct
    const acc = total > 0 ? Number(((correct / total) * 100).toFixed(1)) : 0
    const errorRate = total > 0 ? Number(((errorCount / total) * 100).toFixed(1)) : 0
    const confusions = row
      .map((count, targetIndex) => (
        targetIndex !== index && count > 0
          ? { source: name, target: labels[targetIndex], count }
          : null
      ))
      .filter(Boolean)
      .sort((a, b) => b.count - a.count || a.target.localeCompare(b.target))

    return {
      name,
      total,
      correct,
      errorCount,
      acc,
      errorRate,
      confusions,
    }
  })
}

export function getConfusionInsights(labels, matrix, pairLimit = 4) {
  const perClass = getPerClassStats(labels, matrix)
  const perfectCount = perClass.filter(item => item.acc === 100).length
  const highAccCount = perClass.filter(item => item.acc >= 95).length
  const minAcc = perClass.length > 0 ? Math.min(...perClass.map(item => item.acc)) : 0
  const maxCell = matrix.length > 0 ? Math.max(...matrix.flat()) : 0

  const topPairs = perClass
    .flatMap(item => item.confusions.map(pair => ({
      ...pair,
      sourceAcc: item.acc,
      sourceErrorRate: item.errorRate,
      sourceErrorCount: item.errorCount,
      total: item.total,
      shareOfSourceErrors: item.errorCount > 0
        ? Number(((pair.count / item.errorCount) * 100).toFixed(1))
        : 0,
    })))
    .sort((a, b) =>
      b.count - a.count ||
      b.sourceErrorRate - a.sourceErrorRate ||
      a.source.localeCompare(b.source) ||
      a.target.localeCompare(b.target)
    )
    .slice(0, pairLimit)

  return { perClass, perfectCount, highAccCount, minAcc, maxCell, topPairs }
}

export function getTopErrorClasses(labels, matrix, limit = 6) {
  return getPerClassStats(labels, matrix)
    .filter(item => item.errorCount > 0)
    .sort((a, b) =>
      b.errorRate - a.errorRate ||
      b.errorCount - a.errorCount ||
      a.name.localeCompare(b.name)
    )
    .slice(0, limit)
    .map(item => ({
      breed: item.name,
      rate: item.errorRate,
      errorCount: item.errorCount,
      total: item.total,
      similar: item.confusions.map(pair => pair.target).join(' / '),
    }))
}
