export default function KpiCard({
  title,
  value,
  sub,
  footer
}: {
  title: string
  value: React.ReactNode
  sub?: React.ReactNode
  footer?: React.ReactNode
}) {
  return (
    <div className="card p-3">
      <div className="text-muted-2 small">{title}</div>
      <div className="h3 mb-0 kpi mono">{value}</div>
      {sub ? <div className="text-muted-2 small mt-2">{sub}</div> : null}
      {footer ? <div className="mt-2">{footer}</div> : null}
    </div>
  )
}
