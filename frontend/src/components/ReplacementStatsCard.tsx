import { ReplacementStats } from "../types/regex";

interface ReplacementStatsCardProps {
  stats: ReplacementStats | null;
}

export default function ReplacementStatsCard({ stats }: ReplacementStatsCardProps) {
  if (!stats) {
    return null;
  }

  return (
    <section className="replacement-stats-panel">
      <div className="replacement-stats-header">
        <div>
          <p className="eyebrow">Replacement Result</p>
          <h2>Run Stats</h2>
        </div>
      </div>

      <dl className="stats replacement-stats">
        <div>
          <dt>Checked</dt>
          <dd>{stats.checked_rows.toLocaleString()}</dd>
        </div>
        <div>
          <dt>Matched</dt>
          <dd>{stats.matched_rows.toLocaleString()}</dd>
        </div>
        <div>
          <dt>Total Matches</dt>
          <dd>{stats.total_matches.toLocaleString()}</dd>
        </div>
        <div>
          <dt>Replaced</dt>
          <dd>{stats.replaced_rows.toLocaleString()}</dd>
        </div>
      </dl>
    </section>
  );
}
