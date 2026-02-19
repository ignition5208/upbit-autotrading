import { useState } from 'react'
import type { CreateTraderRequest } from '../../types/dto'

export default function AddTraderModal({
  show,
  onClose,
  onSubmit
}: {
  show: boolean
  onClose: () => void
  onSubmit: (body: CreateTraderRequest) => Promise<void>
}) {
  const [form, setForm] = useState<CreateTraderRequest>({
    name: '',
    mode: 'PAPER',
    risk_mode: 'STANDARD',
    score_strategy: 'STRAT_A',
    krw_allocation_limit: 0
  })
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  if (!show) return null

  async function submit() {
    setBusy(true)
    setErr(null)
    try {
      await onSubmit(form)
      onClose()
    } catch (e) {
      setErr((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="modal d-block" tabIndex={-1} style={{ background: 'rgba(0,0,0,.55)' }}>
      <div className="modal-dialog modal-lg">
        <div className="modal-content">
          <div className="modal-header border-bottom border-soft">
            <h5 className="modal-title">Add Trader</h5>
            <button className="btn-close btn-close-white" onClick={onClose} />
          </div>

          <div className="modal-body">
            {err ? <div className="alert alert-danger">{err}</div> : null}
            <div className="row g-3">
              <div className="col-md-4">
                <label className="form-label text-muted-2">Name</label>
                <input
                  className="form-control bg-panel-2 border-soft text-white"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                />
              </div>

              <div className="col-md-4">
                <label className="form-label text-muted-2">Mode</label>
                <select
                  className="form-select bg-panel-2 border-soft text-white"
                  value={form.mode}
                  onChange={(e) => setForm({ ...form, mode: e.target.value as any })}
                >
                  <option value="PAPER">PAPER</option>
                  <option value="LIVE">LIVE</option>
                </select>
                <div className="text-muted-2 small mt-1">LIVE는 ARM 전 주문 금지</div>
              </div>

              <div className="col-md-4">
                <label className="form-label text-muted-2">Risk</label>
                <select
                  className="form-select bg-panel-2 border-soft text-white"
                  value={form.risk_mode}
                  onChange={(e) => setForm({ ...form, risk_mode: e.target.value as any })}
                >
                  <option value="SAFE">SAFE</option>
                  <option value="STANDARD">STANDARD</option>
                  <option value="PROFIT">PROFIT</option>
                  <option value="CRAZY">CRAZY</option>
                </select>
              </div>

              <div className="col-md-6">
                <label className="form-label text-muted-2">Score Strategy</label>
                <select
                  className="form-select bg-panel-2 border-soft text-white"
                  value={form.score_strategy}
                  onChange={(e) => setForm({ ...form, score_strategy: e.target.value })}
                >
                  <option value="STRAT_A">STRAT_A</option>
                  <option value="STRAT_B">STRAT_B</option>
                  <option value="STRAT_C">STRAT_C</option>
                </select>
              </div>

              <div className="col-md-6">
                <label className="form-label text-muted-2">KRW Allocation Limit</label>
                <input
                  type="number"
                  className="form-control bg-panel-2 border-soft text-white mono"
                  value={form.krw_allocation_limit}
                  onChange={(e) => setForm({ ...form, krw_allocation_limit: Number(e.target.value) })}
                />
              </div>
            </div>
          </div>

          <div className="modal-footer border-top border-soft">
            <button className="btn badge-soft" onClick={onClose} disabled={busy}>Cancel</button>
            <button className="btn btn-accent" onClick={submit} disabled={busy || !form.name}>Create & Start</button>
          </div>
        </div>
      </div>
    </div>
  )
}
