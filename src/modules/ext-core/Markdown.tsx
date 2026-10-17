import type { ReactNode } from 'react'

/** Безопасный мини-рендер markdown уроков и правил: ## заголовки, списки, **жирный**. Без HTML. */
function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) => (part.startsWith('**') && part.endsWith('**') ? <strong key={i}>{part.slice(2, -2)}</strong> : part))
}

export function Markdown({ text }: { text: string }) {
  const blocks: ReactNode[] = []
  let list: { ordered: boolean; items: string[] } | null = null
  const flush = () => {
    if (!list) return
    const items = list.items.map((it, i) => <li key={i}>{inline(it)}</li>)
    blocks.push(list.ordered ? <ol key={blocks.length}>{items}</ol> : <ul key={blocks.length}>{items}</ul>)
    list = null
  }
  for (const raw of text.split('\n')) {
    const line = raw.trim()
    const ordered = /^\d+\.\s+/.test(line)
    if (ordered || line.startsWith('- ')) {
      const item = line.replace(/^(\d+\.|-)\s+/, '')
      if (!list || list.ordered !== ordered) { flush(); list = { ordered, items: [] } }
      list.items.push(item)
      continue
    }
    flush()
    if (!line) continue
    if (line.startsWith('## ')) blocks.push(<h3 key={blocks.length}>{inline(line.slice(3))}</h3>)
    else if (line.startsWith('# ')) blocks.push(<h2 key={blocks.length}>{inline(line.slice(2))}</h2>)
    else blocks.push(<p key={blocks.length}>{inline(line)}</p>)
  }
  flush()
  return <div className="ext-md">{blocks}</div>
}
