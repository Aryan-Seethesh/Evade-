interface Props {
  label: string;
  value: string;
  accent?: 'red' | 'green' | 'amber' | 'blue';
}

export default function MetricCard({ label, value, accent = 'blue' }: Props) {
  return (
    <div className={`metric-card ${accent}`}>
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
    </div>
  );
}
