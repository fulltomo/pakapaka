import React, { useState, useMemo } from 'react';
import {
  BacktestRequest,
  BacktestResult,
} from '../types';
import { api } from '../services/api';
import { StatCard } from '../components/StatCard';
import { EquityChart } from '../components/EquityChart';
import { EVBadge } from '../components/PredictionBadge';
import {
  BarChart3,
  Play,
  Sliders,
  TrendingUp,
  Percent,
  Trophy,
  ShieldAlert,
  Coins,
  Scale,
  Calendar,
  Layers,
  AlertCircle,
  FileSpreadsheet,
  Search,
} from 'lucide-react';

export const Backtest: React.FC = () => {
  // Form Parameters
  const [startDate, setStartDate] = useState<string>('2024-01-01');
  const [endDate, setEndDate] = useState<string>('2024-12-31');
  const [betType, setBetType] = useState<string>('tansho');
  const [minEv, setMinEv] = useState<number>(1.10);
  const [minProb, setMinProb] = useState<number>(0.10);
  const [useKelly, setUseKelly] = useState<boolean>(true);
  const [kellyFraction, setKellyFraction] = useState<number>(0.25);
  const [betAmount, setBetAmount] = useState<number>(1000);
  const [initialPoints, setInitialPoints] = useState<number>(100000);

  // Execution & Result States
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Trade log filter
  const [logFilter, setLogFilter] = useState<'all' | 'won' | 'lost'>('all');
  const [searchLog, setSearchLog] = useState<string>('');

  // Preset Handlers
  const applyPreset = (preset: 'high_ev' | 'safe_place' | 'longshot') => {
    if (preset === 'high_ev') {
      setBetType('tansho');
      setMinEv(1.20);
      setMinProb(0.10);
      setUseKelly(true);
      setKellyFraction(0.25);
    } else if (preset === 'safe_place') {
      setBetType('fukusho');
      setMinEv(1.05);
      setMinProb(0.25);
      setUseKelly(false);
      setBetAmount(2000);
    } else if (preset === 'longshot') {
      setBetType('tansho');
      setMinEv(1.50);
      setMinProb(0.05);
      setUseKelly(true);
      setKellyFraction(0.10);
    }
  };

  // Run Backtest
  const handleRunBacktest = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    try {
      setIsRunning(true);
      setErrorMessage(null);

      const payload: BacktestRequest = {
        start_date: startDate || null,
        end_date: endDate || null,
        min_ev: Number(minEv),
        min_prob: Number(minProb),
        bet_type: betType,
        use_kelly: useKelly,
        kelly_fraction: useKelly ? Number(kellyFraction) : undefined,
        bet_amount: !useKelly ? Number(betAmount) : undefined,
      };

      const res = await api.runBacktest(payload);
      setResult(res);
    } catch (err: unknown) {
      console.error('Backtest error:', err);
      setErrorMessage('バックテストの実行に失敗しました。対象期間内の確定レースデータが存在するか確認してください。');
    } finally {
      setIsRunning(false);
    }
  };

  // Filtered bets list
  const filteredBets = useMemo(() => {
    if (!result || !result.bets) return [];
    return result.bets.filter((b) => {
      if (logFilter === 'won' && b.status !== 'won') return false;
      if (logFilter === 'lost' && b.status !== 'lost') return false;
      if (searchLog.trim()) {
        const q = searchLog.toLowerCase();
        const matchRace = (b.race_name || b.race_id).toLowerCase().includes(q);
        const matchComb = b.combination.includes(q);
        if (!matchRace && !matchComb) return false;
      }
      return true;
    });
  }, [result, logFilter, searchLog]);

  const isProfit = (result?.profit ?? 0) >= 0;

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-850 to-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-indigo-400" />
              <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">
                Quantitative Strategy Backtesting
              </span>
            </div>
            <h1 className="text-2xl font-extrabold text-slate-100 mt-1">
              バックテスト・スタジオ (Backtest Studio)
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 max-w-2xl mt-1">
              過去レースデータをもとに、機械学習モデルの期待値（EV）フィルタリングやケリー基準資金管理戦略の収益性・ドローダウンを網羅的にシミュレーション検証します。
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-slate-400 mr-1">クイックプリセット:</span>
            <button
              onClick={() => applyPreset('high_ev')}
              className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-emerald-300 border border-emerald-800/60 text-xs transition"
            >
              高EV単勝
            </button>
            <button
              onClick={() => applyPreset('safe_place')}
              className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-cyan-300 border border-cyan-800/60 text-xs transition"
            >
              堅実複勝
            </button>
            <button
              onClick={() => applyPreset('longshot')}
              className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-purple-300 border border-purple-800/60 text-xs transition"
            >
              大穴EV
            </button>
          </div>
        </div>
      </div>

      {/* Parameter Settings Form */}
      <form onSubmit={handleRunBacktest} className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm space-y-5">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center space-x-2">
            <Sliders className="w-4 h-4 text-indigo-400" />
            <h2 className="text-sm font-bold text-slate-200">バックテスト条件設定</h2>
          </div>
          <span className="text-xs text-slate-400">期間・戦略・資金配分を自由にカスタマイズ</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {/* Date Range */}
          <div className="bg-slate-850 p-3.5 rounded-lg border border-slate-800 space-y-2">
            <label className="text-xs text-slate-300 font-medium flex items-center space-x-1">
              <Calendar className="w-3.5 h-3.5 text-indigo-400" />
              <span>検証期間 (Start - End)</span>
            </label>
            <div className="space-y-1.5">
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full bg-slate-800 text-slate-200 border border-slate-700 rounded px-2.5 py-1 text-xs font-mono"
              />
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full bg-slate-800 text-slate-200 border border-slate-700 rounded px-2.5 py-1 text-xs font-mono"
              />
            </div>
          </div>

          {/* Bet Type */}
          <div className="bg-slate-850 p-3.5 rounded-lg border border-slate-800 space-y-2">
            <label className="text-xs text-slate-300 font-medium block">対象券種</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setBetType('tansho')}
                className={`py-2 text-xs font-semibold rounded-md border transition ${
                  betType === 'tansho'
                    ? 'bg-indigo-600 text-white border-indigo-500 shadow-sm'
                    : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-slate-200'
                }`}
              >
                単勝 (Win)
              </button>
              <button
                type="button"
                onClick={() => setBetType('fukusho')}
                className={`py-2 text-xs font-semibold rounded-md border transition ${
                  betType === 'fukusho'
                    ? 'bg-cyan-600 text-white border-cyan-500 shadow-sm'
                    : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-slate-200'
                }`}
              >
                複勝 (Place)
              </button>
            </div>
            <div className="text-[10px] text-slate-500">
              {betType === 'tansho' ? '1着馬を狙う投資戦略' : '3着以内を狙う高勝率投資戦略'}
            </div>
          </div>

          {/* Min EV & Min Prob */}
          <div className="bg-slate-850 p-3.5 rounded-lg border border-slate-800 space-y-3">
            <div className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-slate-300">最小期待値 (Min EV):</span>
                <span className="font-mono font-bold text-emerald-400">{minEv.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min="1.00"
                max="2.50"
                step="0.05"
                value={minEv}
                onChange={(e) => setMinEv(parseFloat(e.target.value))}
                className="w-full h-1.5 bg-slate-700 rounded appearance-none accent-emerald-500 cursor-pointer"
              />
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-slate-300">最小勝率 (Min Prob):</span>
                <span className="font-mono font-bold text-cyan-400">{(minProb * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0.05"
                max="0.50"
                step="0.01"
                value={minProb}
                onChange={(e) => setMinProb(parseFloat(e.target.value))}
                className="w-full h-1.5 bg-slate-700 rounded appearance-none accent-cyan-500 cursor-pointer"
              />
            </div>
          </div>

          {/* Sizing & Kelly */}
          <div className="bg-slate-850 p-3.5 rounded-lg border border-slate-800 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-300 font-medium">資金管理方式</span>
              <button
                type="button"
                onClick={() => setUseKelly(!useKelly)}
                className={`text-[10px] px-2 py-0.5 rounded font-mono font-semibold border ${
                  useKelly
                    ? 'bg-indigo-950 text-indigo-300 border-indigo-700'
                    : 'bg-slate-800 text-slate-400 border-slate-700'
                }`}
              >
                {useKelly ? 'ケリー基準' : '固定ベット'}
              </button>
            </div>

            {useKelly ? (
              <div className="space-y-1">
                <div className="flex justify-between text-[11px] text-slate-400">
                  <span>ケリー比率:</span>
                  <span className="font-mono text-indigo-300 font-semibold">{kellyFraction.toFixed(2)}x</span>
                </div>
                <input
                  type="range"
                  min="0.10"
                  max="1.00"
                  step="0.05"
                  value={kellyFraction}
                  onChange={(e) => setKellyFraction(parseFloat(e.target.value))}
                  className="w-full h-1.5 bg-slate-700 rounded appearance-none accent-indigo-500 cursor-pointer"
                />
              </div>
            ) : (
              <div className="space-y-1">
                <div className="flex justify-between text-[11px] text-slate-400">
                  <span>1点あたり金額:</span>
                  <span className="font-mono text-slate-200">{betAmount.toLocaleString()} pt</span>
                </div>
                <select
                  value={betAmount}
                  onChange={(e) => setBetAmount(Number(e.target.value))}
                  className="w-full bg-slate-800 text-slate-200 border border-slate-700 rounded px-2 py-1 text-xs"
                >
                  <option value={500}>500 pt</option>
                  <option value={1000}>1,000 pt</option>
                  <option value={2000}>2,000 pt</option>
                  <option value={5000}>5,000 pt</option>
                  <option value={10000}>10,000 pt</option>
                </select>
              </div>
            )}
          </div>

          {/* Initial Points Input */}
          <div className="bg-slate-850 p-3.5 rounded-lg border border-slate-800 space-y-2">
            <label className="text-xs text-slate-300 font-medium block">初期仮想資本 (pt)</label>
            <input
              type="number"
              value={initialPoints}
              onChange={(e) => setInitialPoints(Number(e.target.value))}
              min="10000"
              step="10000"
              className="w-full bg-slate-800 text-slate-200 border border-slate-700 rounded px-2.5 py-1.5 text-xs font-mono"
            />
            <div className="text-[10px] text-slate-500">標準: 100,000 pt</div>
          </div>
        </div>

        {/* Submit Button */}
        <div className="pt-2 flex items-center justify-end">
          <button
            type="submit"
            disabled={isRunning}
            className="flex items-center space-x-2 px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-sm shadow-lg shadow-indigo-950/60 transition disabled:opacity-50"
          >
            <Play className={`w-4 h-4 ${isRunning ? 'animate-spin' : ''}`} />
            <span>{isRunning ? 'バックテスト計算中...' : '🚀 バックテストを実行する'}</span>
          </button>
        </div>
      </form>

      {/* Error Banner */}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-rose-950/70 border border-rose-800 text-rose-300 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Results Section */}
      {result && (
        <div className="space-y-6 animate-fadeIn">
          {/* Section Title */}
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-100 flex items-center space-x-2">
              <Trophy className="w-5 h-5 text-indigo-400" />
              <span>バックテスト検証結果レポート</span>
            </h2>
            <span className="text-xs px-3 py-1 rounded-full bg-indigo-950 text-indigo-300 border border-indigo-800 font-mono">
              Total {result.total_bets} Trades Executed
            </span>
          </div>

          {/* 8 KPI StatCards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
            <StatCard
              title="総取引数"
              value={`${result.total_bets} 件`}
              subtitle={`${betType === 'tansho' ? '単勝' : '複勝'}`}
              icon={Layers}
              color="slate"
            />

            <StatCard
              title="的中数 / 勝率"
              value={`${result.win_rate.toFixed(1)}%`}
              subtitle={`${result.won_bets} 勝 / ${result.total_bets - result.won_bets} 敗`}
              icon={Trophy}
              color="cyan"
              badge={`${result.won_bets}勝`}
            />

            <StatCard
              title="総投資額"
              value={`${result.total_invested.toLocaleString()} pt`}
              subtitle="累計購入額"
              icon={Coins}
              color="blue"
            />

            <StatCard
              title="総払戻額"
              value={`${result.total_returned.toLocaleString()} pt`}
              subtitle="累計リターン"
              icon={Coins}
              color="emerald"
            />

            <StatCard
              title="純損益"
              value={`${isProfit ? '+' : ''}${result.profit.toLocaleString()} pt`}
              subtitle={isProfit ? '黒字' : '赤字'}
              icon={TrendingUp}
              color={isProfit ? 'emerald' : 'red'}
              trend={{
                value: `${result.roi.toFixed(1)}%`,
                isPositive: isProfit,
              }}
            />

            <StatCard
              title="通算回収率"
              value={`${result.roi.toFixed(1)}%`}
              subtitle="ROI (払戻/投資)"
              icon={Percent}
              color={result.roi >= 100 ? 'emerald' : result.roi > 0 ? 'amber' : 'red'}
              trend={{
                value: result.roi >= 100 ? '利益確定' : 'マイナス',
                isPositive: result.roi >= 100,
              }}
            />

            <StatCard
              title="PF (損益比)"
              value={result.profit_factor ? result.profit_factor.toFixed(2) : '1.00'}
              subtitle="総利益 / 総損失"
              icon={Scale}
              color={result.profit_factor >= 1.2 ? 'emerald' : 'purple'}
              badge="Profit Factor"
            />

            <StatCard
              title="最大ドローダウン"
              value={`-${(result.max_drawdown * 100).toFixed(1)}%`}
              subtitle="最大資金下落率"
              icon={ShieldAlert}
              color={result.max_drawdown > 0.2 ? 'red' : 'purple'}
            />
          </div>

          {/* Equity Progression Chart */}
          <EquityChart
            data={result.equity_curve}
            initialBalance={initialPoints}
            height={360}
            title="バックテスト累積資産推移曲線 (Equity Curve)"
            currencyLabel="pt"
          />

          {/* Detailed Trade Log Table */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <FileSpreadsheet className="w-4 h-4 text-indigo-400" />
                <h3 className="text-sm font-bold text-slate-200">
                  取引ログ明細 (全 {result.bets?.length || 0} 件中 {filteredBets.length} 件表示)
                </h3>
              </div>

              {/* Filter Tabs & Search */}
              <div className="flex flex-wrap items-center gap-2">
                <div className="relative">
                  <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    placeholder="レース名・馬番検索..."
                    value={searchLog}
                    onChange={(e) => setSearchLog(e.target.value)}
                    className="pl-8 pr-3 py-1 bg-slate-800 text-slate-200 border border-slate-700 rounded-lg text-xs w-40 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div className="flex bg-slate-800 rounded-lg p-0.5 border border-slate-700 text-xs">
                  <button
                    onClick={() => setLogFilter('all')}
                    className={`px-3 py-1 rounded ${
                      logFilter === 'all' ? 'bg-slate-700 text-white font-bold' : 'text-slate-400'
                    }`}
                  >
                    すべて ({result.bets?.length || 0})
                  </button>
                  <button
                    onClick={() => setLogFilter('won')}
                    className={`px-3 py-1 rounded ${
                      logFilter === 'won' ? 'bg-emerald-950 text-emerald-300 font-bold border border-emerald-800' : 'text-slate-400'
                    }`}
                  >
                    的中のみ ({result.bets?.filter((b) => b.status === 'won').length || 0})
                  </button>
                  <button
                    onClick={() => setLogFilter('lost')}
                    className={`px-3 py-1 rounded ${
                      logFilter === 'lost' ? 'bg-rose-950 text-rose-300 font-bold border border-rose-800' : 'text-slate-400'
                    }`}
                  >
                    不的中のみ ({result.bets?.filter((b) => b.status === 'lost').length || 0})
                  </button>
                </div>
              </div>
            </div>

            {filteredBets.length === 0 ? (
              <div className="py-12 text-center text-slate-500 text-xs">
                条件に一致する取引ログはありません。
              </div>
            ) : (
              <div className="overflow-x-auto max-h-96">
                <table className="w-full text-left text-xs">
                  <thead className="sticky top-0 bg-slate-900 z-10">
                    <tr className="border-b border-slate-800 text-slate-400">
                      <th className="py-2.5 px-3">#</th>
                      <th className="py-2.5 px-3">レース</th>
                      <th className="py-2.5 px-3">券種/馬番</th>
                      <th className="py-2.5 px-3 text-right">オッズ</th>
                      <th className="py-2.5 px-3 text-right">期待値</th>
                      <th className="py-2.5 px-3 text-right">投資額</th>
                      <th className="py-2.5 px-3 text-center">判定</th>
                      <th className="py-2.5 px-3 text-right">払戻金</th>
                      <th className="py-2.5 px-3 text-right">損益</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {filteredBets.map((bet, idx) => {
                      const isWon = bet.status === 'won';

                      return (
                        <tr key={bet.id || idx} className="hover:bg-slate-800/40 transition">
                          <td className="py-2 px-3 font-mono text-slate-500">{idx + 1}</td>
                          <td className="py-2 px-3">
                            <div className="font-semibold text-slate-200 truncate max-w-[140px]">
                              {bet.race_name || bet.race_id}
                            </div>
                            <div className="text-[10px] text-slate-500 font-mono">
                              {bet.race_date || bet.race_id}
                            </div>
                          </td>
                          <td className="py-2 px-3">
                            <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-medium text-[11px] mr-1.5">
                              {bet.bet_type === 'tansho' ? '単勝' : '複勝'}
                            </span>
                            <span className="font-mono font-bold text-slate-200">{bet.combination}番</span>
                          </td>
                          <td className="py-2 px-3 text-right font-mono text-slate-300">
                            {bet.odds_at_bet.toFixed(1)}倍
                          </td>
                          <td className="py-2 px-3 text-right">
                            <EVBadge ev={bet.expected_value_at_bet} size="sm" showIcon={false} />
                          </td>
                          <td className="py-2 px-3 text-right font-mono text-slate-200">
                            {bet.bet_points.toLocaleString()} pt
                          </td>
                          <td className="py-2 px-3 text-center">
                            {isWon ? (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-700">
                                的中
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-800 text-slate-400">
                                外れ
                              </span>
                            )}
                          </td>
                          <td className="py-2 px-3 text-right font-mono text-slate-300">
                            {isWon ? (
                              <span className="text-emerald-400 font-bold">{bet.payout_points.toLocaleString()} pt</span>
                            ) : (
                              <span className="text-slate-500">0 pt</span>
                            )}
                          </td>
                          <td className="py-2 px-3 text-right font-mono font-bold">
                            {isWon ? (
                              <span className="text-emerald-400">+{bet.profit.toLocaleString()} pt</span>
                            ) : (
                              <span className="text-rose-400">-{bet.bet_points.toLocaleString()} pt</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Empty State before running */}
      {!result && !isRunning && (
        <div className="bg-slate-900/60 border border-dashed border-slate-800 rounded-2xl p-12 text-center space-y-3">
          <div className="w-16 h-16 rounded-2xl bg-indigo-950/60 border border-indigo-800/40 flex items-center justify-center text-indigo-400 mx-auto">
            <BarChart3 className="w-8 h-8" />
          </div>
          <h3 className="text-base font-bold text-slate-200">バックテストが未実行です</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
            上記の設定フォームで検証期間や戦略パラメータ（最小期待値・ケリー基準・券種）を指定し、「🚀 バックテストを実行する」をクリックしてください。
          </p>
        </div>
      )}
    </div>
  );
};

export default Backtest;
