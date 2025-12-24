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
      symbolSize: isChapter ? 46 : 22,
      itemStyle: {
        color: isChapter ? 'rgba(255,255,255,0.18)' : isSelected ? '#10b981' : 'rgba(255,255,255,0.10)',
        borderColor: isSelected ? 'rgba(255,255,255,0.75)' : 'rgba(255,255,255,0.18)',
        borderWidth: isSelected ? 2 : 1,
      },
      label: {
        show: true,
        color: 'rgba(255,255,255,0.88)',
        fontSize: isChapter ? 13 : 12,
      },
    }
  })

  const links = (props.edges || [])
    .filter((e) => e.type === 'contains' || e.type === 'relates_to')
    .map((e) => ({
      source: e.source,
      target: e.target,
      lineStyle: {
        color:
          e.type === 'relates_to'
            ? 'rgba(99, 102, 241, 0.45)'
            : e.type === 'contains'
              ? 'rgba(255, 255, 255, 0.22)'
              : 'rgba(255, 255, 255, 0.16)',
        width: e.type === 'relates_to' ? 2 : 1,
      },
    }))

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      formatter: (p) => {
        const name = p?.data?.name || ''
        const desc = p?.data?.value || ''
        if (!desc) return name
        return `${name}<br/><span style="opacity:.75">${desc}</span>`
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
          repulsion: 180,
          edgeLength: 120,
        },
        label: { position: 'right' },
        emphasis: { focus: 'adjacency' },
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
  chart = echarts.init(elRef.value)
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
  height: calc(100vh - 160px);
  min-height: 520px;
  width: 100%;
}
</style>
