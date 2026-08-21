import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from 'recharts';
import { EquityPoint } from '../types';

export interface EquityChartDataPoint {
  date?: string;
  race_id?: string;
  balance: number;
  cumulative_profit?: number;
  drawdown?: number;
  profit?: number;
  index?: number;
  label?: string;
}

export interface EquityChartProps {
  data?: (EquityPoint | EquityChartDataPoint)[];
  initialBalance?: number;
  height?: number;
  title?: string;
  showDrawdown?: boolean;
  currencyLabel?: string;
  className?: string;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ value: number; payload: EquityChartDataPoint }>;
  label?: string;
  initialBalance: number;
  currencyLabel: string;
}

const CustomTooltip: React.FC<CustomTooltipProps> = ({
  active,
  payload,
  label,
  initialBalance,
  currencyLabel,
}) => {
  if (!active || !payload || !payload.length) return null;

  const item = payload[0].payload;
  const balance = item.balance;
  const netProfit = balance - initialBalance;
  const isProfit = netProfit >= 0;
  const returnRate = initialBalance > 0 ? (balance / initialBalance) * 100 : 100;

  return (
    <div className="bg-slate-900/95 border border-slate-700 backdrop-blur rounded-xl p-3.5 shadow-2xl text-xs min-w-[200px]">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800 text-slate-400">
        <span className="font-medium">{item.date || label || '取引点'}</span>
        {item.race_id && <span className="font-mono text-[10px] text-slate-500">ID: {item.race_id}</span>}
      </div>

      <div className="mt-2 space-y-1.5">
        <div className="flex items-center justify-between">
          <span className="text-slate-400">資産残高:</span>
          <span className="font-bold font-mono text-slate-100 text-sm">
            {balance.toLocaleString()} {currencyLabel}
          </span>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-slate-400">累積損益:</span>
          <span
            className={`font-semibold font-mono ${
              isProfit ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            {isProfit ? `+${netProfit.toLocaleString()}` : netProfit.toLocaleString()}{' '}
            {currencyLabel}
          </span>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-slate-400">資産倍率:</span>
          <span
            className={`font-semibold font-mono ${
              returnRate >= 100 ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            {returnRate.toFixed(1)}%
          </span>
        </div>

        {item.drawdown !== undefined && item.drawdown > 0 && (
          <div className="flex items-center justify-between pt-1 border-t border-slate-800/80 text-[11px]">
            <span className="text-slate-500">最大DD:</span>
            <span className="font-mono text-rose-400 font-semibold">
              -{(item.drawdown * 100).toFixed(1)}%
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export const EquityChart: React.FC<EquityChartProps> = ({
  data = [],
  initialBalance = 100000,
  height = 320,
  title,
  showDrawdown: _showDrawdown = false,
  currencyLabel = 'pt',
  className = '',
}) => {
  // If no data or single item, format initial baseline
  const chartData: EquityChartDataPoint[] = React.useMemo(() => {
    if (!data || data.length === 0) {
      return [
        { date: 'Start', balance: initialBalance, cumulative_profit: 0, drawdown: 0, index: 0 },
      ];
    }
    return data.map((pt, idx) => ({
      ...pt,
      index: idx + 1,
      label: pt.date ? `${pt.date} (#${idx + 1})` : `Trade #${idx + 1}`,
    }));
  }, [data, initialBalance]);

  const latestBalance = chartData[chartData.length - 1]?.balance ?? initialBalance;
  const isPositive = latestBalance >= initialBalance;
  const gradientId = React.useId();

  // Format y-axis ticks
  const formatYAxis = (val: number) => {
    if (val >= 1000000) return `${(val / 1000000).toFixed(1)}M`;
    if (val >= 10000) return `${Math.round(val / 1000)}k`;
    return `${val}`;
  };

  const strokeColor = isPositive ? '#10b981' : '#f43f5e';
  const fillGradientStart = isPositive ? '#10b981' : '#f43f5e';

  if (!data || data.length === 0) {
    return (
      <div
        className={`bg-slate-900/90 border border-slate-800 rounded-xl p-6 flex flex-col items-center justify-center text-center ${className}`}
        style={{ height }}
      >
        <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center text-slate-500 mb-3">
          📈
        </div>
        <p className="text-slate-300 font-semibold text-sm">資産推移データがありません</p>
        <p className="text-slate-500 text-xs mt-1">
          シミュレーション投票またはバックテストを実行すると、リアルタイムに資産推移曲線がプロットされます。
        </p>
      </div>
    );
  }

  return (
    <div className={`bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm ${className}`}>
      {title && (
        <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-800">
          <h3 className="text-sm font-bold text-slate-200 tracking-tight flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span>{title}</span>
          </h3>
          <div className="flex items-center space-x-3 text-xs font-mono">
            <span className="text-slate-400">
              現在: <strong className="text-slate-100">{latestBalance.toLocaleString()} {currencyLabel}</strong>
            </span>
            <span
              className={`font-semibold ${
                isPositive ? 'text-emerald-400' : 'text-rose-400'
              }`}
            >
              ({isPositive ? '+' : ''}{(latestBalance - initialBalance).toLocaleString()} {currencyLabel})
            </span>
          </div>
        </div>
      )}

      <div style={{ width: '100%', height }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={chartData}
            margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
          >
            <defs>
              <linearGradient id={`gradient-${gradientId}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={fillGradientStart} stopOpacity={0.35} />
                <stop offset="95%" stopColor={fillGradientStart} stopOpacity={0.0} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} vertical={false} />

            <XAxis
              dataKey="date"
              stroke="#64748b"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: '#334155' }}
              tickFormatter={(val, i) => {
                if (chartData.length > 20) {
                  return i % Math.ceil(chartData.length / 8) === 0 ? val : '';
                }
                return val ? val.slice(5) : `#${i + 1}`;
              }}
            />

            <YAxis
              stroke="#64748b"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: '#334155' }}
              tickFormatter={formatYAxis}
              domain={['auto', 'auto']}
            />

            <Tooltip
              content={
                <CustomTooltip
                  initialBalance={initialBalance}
                  currencyLabel={currencyLabel}
                />
              }
            />

            {initialBalance && (
              <ReferenceLine
                y={initialBalance}
                stroke="#64748b"
                strokeDasharray="4 4"
                label={{
                  value: `初期: ${initialBalance.toLocaleString()}pt`,
                  fill: '#94a3b8',
                  fontSize: 10,
                  position: 'right',
                }}
              />
            )}

            <Area
              type="monotone"
              dataKey="balance"
              stroke={strokeColor}
              strokeWidth={2.5}
              fillOpacity={1}
              fill={`url(#gradient-${gradientId})`}
              dot={chartData.length < 30 ? { r: 3, fill: strokeColor, strokeWidth: 1, stroke: '#0f172a' } : false}
              activeDot={{ r: 5, fill: strokeColor, stroke: '#ffffff', strokeWidth: 2 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default EquityChart;
