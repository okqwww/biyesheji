<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  nodes: { type: Array, default: () => [] },
  edges: { type: Array, default: () => [] },
  selectedKnowledgePointIds: { type: Array, default: () => [] },
})

const emit = defineEmits(['toggle-knowledge-point', 'toggle-chapter'])

const elRef = ref(null)
let chart = null

const selectedSet = computed(() => new Set(props.selectedKnowledgePointIds))

function buildOption() {
  const nodes = (props.nodes || []).map((n) => {
    const isChapter = n.type === 'chapter'
    const isSelected = !isChapter && selectedSet.value.has(n.id)

    return {
      id: n.id,
      name: n.name,
      value: n.description || '',
      category: isChapter ? 0 : 1,
      symbolSize: isChapter ? 52 : 26,
      itemStyle: {
        color: isChapter
          ? '#E5E5EA'
          : isSelected
            ? '#007AFF'
            : '#F5F5F7',
        borderColor: isChapter
          ? '#D2D2D7'
          : isSelected
            ? '#007AFF'
            : '#D2D2D7',
        borderWidth: isSelected ? 2 : 1,
      },
      label: {
        show: true,
        color: isChapter ? '#1D1D1F' : '#1D1D1F',
        fontSize: isChapter ? 13 : 12,
        fontFamily: 'Inter, -apple-system, sans-serif',
        fontWeight: isChapter ? 600 : 400,
      },
    }
  })

  const links = (props.edges || [])
    .filter((e) => e.type === 'contains' || e.type === 'relates_to')
    .map((e) => ({
      source: e.source,
      target: e.target,
      lineStyle: {
        color: e.type === 'relates_to'
          ? 'rgba(0, 122, 255, 0.35)'
          : 'rgba(0, 0, 0, 0.12)',
        width: e.type === 'relates_to' ? 2 : 1,
        type: e.type === 'relates_to' ? 'dashed' : 'solid',
      },
    }))

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: '#ffffff',
      borderColor: '#D2D2D7',
      borderWidth: 1,
      borderRadius: 8,
      padding: [8, 12],
      textStyle: {
        color: '#1D1D1F',
        fontSize: 12,
        fontFamily: 'Inter, -apple-system, sans-serif',
      },
      formatter: (p) => {
        const name = p?.data?.name || ''
        const desc = p?.data?.value || ''
        if (!desc) return `<b>${name}</b>`
        return `<b>${name}</b><br/><span style="color:#86868B;font-size:11px">${desc}</span>`
      },
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        draggable: true,
        data: nodes,
        links,
        force: {
          repulsion: 200,
          edgeLength: 130,
          layoutAnimation: true,
        },
        label: { position: 'right' },
        emphasis: {
          focus: 'adjacency',
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(0, 122, 255, 0.3)',
          },
        },
        lineStyle: {
          curveness: 0.1,
        },
      },
    ],
  }
}

function render() {
  if (!chart) return
  chart.setOption(buildOption(), true)
}

onMounted(() => {
  if (!elRef.value) return
  chart = echarts.init(elRef.value, null, { renderer: 'canvas' })

  // Set light theme background
  chart.getZr().setBackgroundColor('transparent')

  chart.on('click', (params) => {
    const id = params?.data?.id
    if (!id) return

    const node = (props.nodes || []).find((n) => n.id === id)
    if (!node) return

    if (node.type === 'chapter') emit('toggle-chapter', id)
    else emit('toggle-knowledge-point', id)
  })

  render()
  window.addEventListener('resize', resize)
})

function resize() {
  chart?.resize()
}

watch(
  () => [props.nodes, props.edges, props.selectedKnowledgePointIds],
  () => {
    render()
  },
  { deep: true },
)

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  if (chart) {
    chart.dispose()
    chart = null
  }
})
</script>

<template>
  <div ref="elRef" class="graph"></div>
</template>

<style scoped>
.graph {
  height: calc(100vh - 200px);
  min-height: 500px;
  width: 100%;
}
</style>
