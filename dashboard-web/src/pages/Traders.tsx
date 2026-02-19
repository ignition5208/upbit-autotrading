import { useEffect, useMemo, useState } from 'react'
import type { TradersListResponse, CreateTraderRequest } from '../types/dto'
import { listTraders, createTrader, startTrader, stopTrader, recreateTrader, armLive } from '../api/traders'
import TraderCard from '../components/Traders/TraderCard'
import AddTraderModal from '../components/Traders/AddTraderModal'
import ArmLiveModal from '../components/Traders/ArmLiveModal'

export default function Traders() {
  const [data, setData] = useState<TradersListResponse | null>(null)
  const [err, setErr] = useState<string | null>(null)

  const [showAdd, setShowAdd] = useState(false)
  const [armTarget, setArmTarget] = useState<number | null>(null)

  const liveCount = useMemo(() => (data?.traders ?? []).filter(t => t.mode === 'LIVE').length, [data])
  const paperCount = useMemo(() => (data?.traders ?? []).filter(t => t.mode === 'PAPER').length, [data])

  async function refresh() {
    const r = await listTraders()
    setData(r)
  }

  useEffect(() => {
    let mounted = true
    refresh()
      .then(() => mounted && setErr(null))
      .catch((e) => mounted && setErr((e as Error).message))
    const id = window.setInterval(() => refresh().catch(() => void 0), 10_000)
    return () => {
      mounted = false
      window.clearInterval(id)
    }
  }, [])

  async function onCreate(body: CreateTraderRequest) {
    await createTrader(body)
    await refresh()
  }

  async function withAction(fn: () => Promise<void>) {
    try {
      await fn()
      await refresh()
    } catch (e) {
      setErr((e as Error).message)
    }
  }

  if (err) return <div className="card p-3">API Error: {err}</div>
  if (!data) return <div className="card p-3">Loading…</div>

  return (
    <>
      <div className="d-flex align-items-end justify-content-between mb-3">
        <div>
          <div className="text-muted-2 small">Manage</div>
          <div className="h4 mb-0">
            Traders <span className="text-muted-2 small ms-2">LIVE {liveCount} · PAPER {paperCount}</span>
          </div>
        </div>
        <div className="d-flex gap-2">
          <button className="btn btn-sm btn-accent" onClick={() => setShowAdd(true)}>Add Trader</button>
        </div>
      </div>

      <div className="row g-3">
        {data.traders.map((t) => (
          <div key={t.trader_id} className="col-12 col-xl-6">
            <TraderCard
              t={t}
              onStart={(id) => withAction(() => startTrader(id))}
              onStop={(id) => withAction(() => stopTrader(id))}
              onRecreate={(id) => withAction(() => recreateTrader(id))}
              onArm={(id) => setArmTarget(id)}
            />
          </div>
        ))}
        {data.traders.length === 0 ? (
          <div className="col-12">
            <div className="card p-4 text-center">
              <div className="h5 mb-2">No traders yet</div>
              <div className="text-muted-2">Add a trader to start monitoring.</div>
              <div className="mt-3">
                <button className="btn btn-accent" onClick={() => setShowAdd(true)}>Add Trader</button>
              </div>
            </div>
          </div>
        ) : null}
      </div>

      <AddTraderModal show={showAdd} onClose={() => setShowAdd(false)} onSubmit={onCreate} />
      <ArmLiveModal
        show={armTarget !== null}
        traderId={armTarget}
        onClose={() => setArmTarget(null)}
        onSubmit={(id, token) => withAction(() => armLive(id, { confirm_token: token }))}
      />
    </>
  )
}
