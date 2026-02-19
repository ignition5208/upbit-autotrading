import { useEffect, useState } from 'react'
import Sidebar from './Sidebar'
import Topbar from './Topbar'
import type { RegimeNow } from '../../types/dto'
import { getOverview } from '../../api/overview'

type ShellState = {
  now_kst: string
  telegram_ok: boolean
  regime_now: RegimeNow
}

const emptyState: ShellState = {
  now_kst: '',
  telegram_ok: false,
  regime_now: { label: '—', score: 0, entry_allowed: false }
}

export default function Shell({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<ShellState>(emptyState)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        const o = await getOverview()
        if (!mounted) return
        setState({ now_kst: o.now_kst, telegram_ok: o.telegram_ok, regime_now: o.regime_now })
        setErr(null)
      } catch (e) {
        if (!mounted) return
        setErr((e as Error).message)
      }
    })()

    const id = window.setInterval(() => {
      getOverview()
        .then((o) => setState({ now_kst: o.now_kst, telegram_ok: o.telegram_ok, regime_now: o.regime_now }))
        .catch(() => void 0)
    }, 10_000)

    return () => {
      mounted = false
      window.clearInterval(id)
    }
  }, [])

  return (
    <div className="d-flex" style={{ minHeight: '100vh' }}>
      <Sidebar />
      <main className="flex-grow-1">
        <Topbar nowKst={state.now_kst} telegramOk={state.telegram_ok} regimeNow={state.regime_now} error={err} />
        <div className="p-3 p-lg-4">{children}</div>
      </main>
    </div>
  )
}
