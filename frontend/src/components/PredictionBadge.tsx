import React from 'react';

interface RecommendationBadgeProps {
  mark?: string | null;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

export const RecommendationBadge: React.FC<RecommendationBadgeProps> = ({
  mark,
  size = 'md',
  showLabel = false,
}) => {
  const normalizedMark = mark ? mark.trim() : '-';

  let bgClass = 'bg-slate-800 text-slate-400 border-slate-700';
  let label = '無印';

  switch (normalizedMark) {
    case '◎':
      bgClass = 'bg-emerald-950/90 text-emerald-300 border-emerald-500 shadow-sm shadow-emerald-950';
      label = '本命';
      break;
    case '◯':
    case '○':
      bgClass = 'bg-blue-950/90 text-blue-300 border-blue-500 shadow-sm shadow-blue-950';
      label = '対抗';
      break;
    case '▲':
      bgClass = 'bg-amber-950/90 text-amber-300 border-amber-500 shadow-sm shadow-amber-950';
      label = '単穴';
      break;
    case '☆':
      bgClass = 'bg-purple-950/90 text-purple-300 border-purple-500 shadow-sm shadow-purple-950';
      label = '連下';
      break;
    case '△':
      bgClass = 'bg-cyan-950/90 text-cyan-300 border-cyan-500 shadow-sm shadow-cyan-950';
      label = '連下';
      break;
    default:
      bgClass = 'bg-slate-800/60 text-slate-500 border-slate-800';
      label = '無印';
      break;
  }

  const sizeClasses = {
    sm: 'w-6 h-6 text-xs',
    md: 'w-7 h-7 text-sm',
    lg: 'w-9 h-9 text-base',
  };

  return (
    <div className="inline-flex items-center space-x-1.5">
      <span
        className={`inline-flex items-center justify-center rounded-full border font-bold font-mono transition-transform ${
          sizeClasses[size]
        } ${bgClass}`}
        title={`${normalizedMark} (${label})`}
      >
        {normalizedMark !== '-' ? normalizedMark : '・'}
      </span>
      {showLabel && normalizedMark !== '-' && (
        <span className="text-[11px] text-slate-400 font-medium">({label})</span>
      )}
    </div>
  );
};

interface EVBadgeProps {
  ev?: number | null;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
}

export const EVBadge: React.FC<EVBadgeProps> = ({
  ev,
  size = 'md',
  showIcon = true,
}) => {
  if (ev === undefined || ev === null) {
    return <span className="text-slate-500 font-mono text-xs">-</span>;
  }

  const isHighEV = ev >= 1.20;
  const isPositiveEV = ev >= 1.00;

  let colorClasses = 'bg-slate-800/80 text-slate-400 border-slate-700';
  if (isHighEV) {
    colorClasses =
      'bg-emerald-950/80 text-emerald-300 border-emerald-500/80 shadow-sm shadow-emerald-950';
  } else if (isPositiveEV) {
    colorClasses =
      'bg-amber-950/80 text-amber-300 border-amber-500/70 shadow-sm shadow-amber-950';
  }

  const sizeClasses = {
    sm: 'px-1.5 py-0.5 text-xs',
    md: 'px-2 py-0.5 text-xs font-semibold',
    lg: 'px-2.5 py-1 text-sm font-bold',
  };

  return (
    <span
      className={`inline-flex items-center space-x-1 rounded-md border font-mono ${sizeClasses[size]} ${colorClasses}`}
      title={`期待値 (EV): ${ev.toFixed(2)}`}
    >
      {showIcon && isHighEV && <span className="text-emerald-400 text-[10px]">★</span>}
      <span>{ev.toFixed(2)}</span>
    </span>
  );
};

interface ProbBadgeProps {
  prob?: number | null;
  type?: 'win' | 'place';
}

export const ProbBadge: React.FC<ProbBadgeProps> = ({ prob, type = 'win' }) => {
  if (prob === undefined || prob === null) {
    return <span className="text-slate-500 font-mono text-xs">-</span>;
  }

  const percent = prob <= 1.0 ? prob * 100 : prob;
  const isHigh = type === 'win' ? percent >= 20 : percent >= 45;

  return (
    <div className="flex flex-col items-end">
      <span
        className={`font-mono text-xs font-semibold ${
          isHigh
            ? type === 'win'
              ? 'text-emerald-400'
              : 'text-cyan-400'
            : 'text-slate-300'
        }`}
      >
        {percent.toFixed(1)}%
      </span>
      <div className="w-12 h-1 bg-slate-800 rounded-full overflow-hidden mt-0.5">
        <div
          className={`h-full rounded-full ${
            type === 'win' ? 'bg-emerald-500' : 'bg-cyan-500'
          }`}
          style={{ width: `${Math.min(percent, 100)}%` }}
        />
      </div>
    </div>
  );
};
