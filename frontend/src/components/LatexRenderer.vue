<script setup>
import katex from 'katex'
import 'katex/dist/katex.min.css'
import { computed } from 'vue'

const props = defineProps({
  /** 含有 LaTeX 公式的文本，公式用 $...$ 或 $$...$$ 包裹 */
  content: {
    type: String,
    default: '',
  },
})

/**
 * 将文本按 $$...$$ 和 $...$ 切分为 token 数组：
 *   { type: 'text' | 'block' | 'inline', value: string }
 */
const tokens = computed(() => {
  const raw = props.content || ''
  const parts = []
  // 先按 $$ 块级公式切割，再在文本段落中按 $ 行内公式切割
  const blockRe = /\$\$([\s\S]+?)\$\$/g
  let lastIndex = 0
  let match

  while ((match = blockRe.exec(raw)) !== null) {
    if (match.index > lastIndex) {
      // 处理块级公式前的文本（可能含行内公式）
      splitInline(raw.slice(lastIndex, match.index), parts)
    }
    parts.push({ type: 'block', value: match[1] })
    lastIndex = blockRe.lastIndex
  }
  if (lastIndex < raw.length) {
    splitInline(raw.slice(lastIndex), parts)
  }
  return parts
})

function splitInline(text, parts) {
  const inlineRe = /\$([^\$]+?)\$/g
  let last = 0
  let m
  while ((m = inlineRe.exec(text)) !== null) {
    if (m.index > last) {
      parts.push({ type: 'text', value: text.slice(last, m.index) })
    }
    parts.push({ type: 'inline', value: m[1] })
    last = inlineRe.lastIndex
  }
  if (last < text.length) {
    parts.push({ type: 'text', value: text.slice(last) })
  }
}

function renderKatex(formula, displayMode) {
  try {
    return katex.renderToString(formula, {
      displayMode,
      throwOnError: false,
      output: 'html',
    })
  } catch {
    return `<span class="latex-error">${formula}</span>`
  }
}
</script>

<template>
  <span class="latex-renderer">
    <template v-for="(tok, i) in tokens" :key="i">
      <span v-if="tok.type === 'text'" class="latex-text" v-text="tok.value" />
      <!-- eslint-disable-next-line vue/no-v-html -->
      <span
        v-else-if="tok.type === 'inline'"
        class="latex-inline"
        v-html="renderKatex(tok.value, false)"
      />
      <!-- eslint-disable-next-line vue/no-v-html -->
      <span
        v-else
        class="latex-block"
        v-html="renderKatex(tok.value, true)"
      />
    </template>
  </span>
</template>

<style scoped>
.latex-renderer {
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--color-text);
}
.latex-block {
  display: block;
  margin: 8px 0;
  text-align: center;
}
.latex-error {
  color: var(--color-danger);
  font-family: 'SF Mono', 'Consolas', monospace;
  font-size: 0.9em;
}
</style>
