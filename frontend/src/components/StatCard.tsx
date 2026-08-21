import React from 'react';
import { LucideIcon, TrendingUp, TrendingDown } from 'lucide-react';

export type StatCardColor = 'emerald' | 'blue' | 'purple' | 'amber' | 'red' | 'cyan' | 'slate';

export interface StatTrend {
  value: string | number;
  isPositive?: boolean;
  label?: string;
}

export interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: StatTrend;
  icon?: LucideIcon | React.ComponentType<{ className?: string }>;
  color?: StatCardColor;
  badge?: string;
  loading?: boolean;
  className?: string;
  onClick?: () => void;
}

const colorStyles: Record<
  StatCardColor,
  {
    iconBg: string;
    iconText: string;
    iconBorder: string;
    accentText: string;
    badgeBg: string;
    badgeText: string;
    badgeBorder: string;
  }
> = {
  emerald: {
    iconBg: 'bg-emerald-500/10',
    iconText: 'text-emerald-400',
    iconBorder: 'border-emerald-500/30',
    accentText: 'text-emerald-400',
    badgeBg: 'bg-emerald-950/80',
    badgeText: 'text-emerald-300',
    badgeBorder: 'border-emerald-800',
  },
  blue: {
    iconBg: 'bg-blue-500/10',
    iconText: 'text-blue-400',
    iconBorder: 'border-blue-500/30',
    accentText: 'text-blue-400',
    badgeBg: 'bg-blue-950/80',
    badgeText: 'text-blue-300',
    badgeBorder: 'border-blue-800',
  },
  purple: {
    iconBg: 'bg-purple-500/10',
    iconText: 'text-purple-400',
    iconBorder: 'border-purple-500/30',
    accentText: 'text-purple-400',
    badgeBg: 'bg-purple-950/80',
    badgeText: 'text-purple-300',
    badgeBorder: 'border-purple-800',
  },
  amber: {
    iconBg: 'bg-amber-500/10',
    iconText: 'text-amber-400',
    iconBorder: 'border-amber-500/30',
    accentText: 'text-amber-400',
    badgeBg: 'bg-amber-950/80',
    badgeText: 'text-amber-300',
    badgeBorder: 'border-amber-800',
  },
  red: {
    iconBg: 'bg-rose-500/10',
    iconText: 'text-rose-400',
    iconBorder: 'border-rose-500/30',
    accentText: 'text-rose-400',
    badgeBg: 'bg-rose-950/80',
    badgeText: 'text-rose-300',
    badgeBorder: 'border-rose-800',
  },
  cyan: {
    iconBg: 'bg-cyan-500/10',
    iconText: 'text-cyan-400',
    iconBorder: 'border-cyan-500/30',
    accentText: 'text-cyan-400',
    badgeBg: 'bg-cyan-950/80',
    badgeText: 'text-cyan-300',
    badgeBorder: 'border-cyan-800',
  },
  slate: {
    iconBg: 'bg-slate-800',
    iconText: 'text-slate-300',
    iconBorder: 'border-slate-700',
    accentText: 'text-slate-300',
    badgeBg: 'bg-slate-800',
    badgeText: 'text-slate-400',
    badgeBorder: 'border-slate-700',
  },
};

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  trend,
  icon: Icon,
  color = 'emerald',
  badge,
  loading = false,
  className = '',
  onClick,
}) => {
  const styles = colorStyles[color];

  return (
    <div
      onClick={onClick}
      className={`relative bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm transition-all duration-200 ${
        onClick ? 'cursor-pointer hover:border-slate-700 hover:bg-slate-850 hover:shadow-md' : ''
      } ${className}`}
    >
      {/* Header: Title & Icon / Badge */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-400 tracking-wide uppercase">{title}</span>
        <div className="flex items-center space-x-2">
          {badge && (
            <span
              className={`text-[10px] px-2 py-0.5 rounded-full border font-mono font-medium ${styles.badgeBg} ${styles.badgeText} ${styles.badgeBorder}`}
            >
              {badge}
            </span>
          )}
          {Icon && (
            <div
              className={`w-8 h-8 rounded-lg border flex items-center justify-center ${styles.iconBg} ${styles.iconText} ${styles.iconBorder}`}
            >
              <Icon className="w-4 h-4" />
            </div>
          )}
        </div>
      </div>

      {/* Main Value */}
      <div className="mt-3">
        {loading ? (
          <div className="h-8 bg-slate-800 rounded animate-pulse w-3/4" />
        ) : (
          <div className="text-2xl sm:text-3xl font-extrabold font-mono text-slate-100 tracking-tight">
            {value}
          </div>
        )}
      </div>

      {/* Footer: Trend / Subtitle */}
      <div className="mt-2.5 flex items-center justify-between text-xs min-h-[1.25rem]">
        {trend ? (
          <div className="flex items-center space-x-1 font-mono">
            {trend.isPositive ? (
              <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
            ) : trend.isPositive === false ? (
              <TrendingDown className="w-3.5 h-3.5 text-rose-400" />
            ) : null}
            <span
              className={`font-semibold ${
                trend.isPositive
                  ? 'text-emerald-400'
                  : trend.isPositive === false
                  ? 'text-rose-400'
                  : 'text-slate-300'
              }`}
            >
              {trend.value}
            </span>
            {trend.label && <span className="text-slate-500 font-sans">{trend.label}</span>}
          </div>
        ) : subtitle ? (
          <span className="text-slate-400 truncate">{subtitle}</span>
        ) : (
          <span />
        )}

        {trend && subtitle && (
          <span className="text-slate-500 text-[11px] truncate max-w-[120px]">{subtitle}</span>
        )}
      </div>
    </div>
  );
};

export default StatCard;
