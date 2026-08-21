import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  WalletSession,
  SimulatedBet,
  AutoBetRequest,
  AutoBetResult,
  SettleResult,
} from '../types';
import { api } from '../services/api';
import { EVBadge } from '../components/PredictionBadge';
import {
  PlayCircle,
  Coins,
  RefreshCw,
  RotateCcw,
  Sliders,
  CheckCircle2,
  AlertCircle,
  Clock,
  Info,
  Search,
  Calendar,
} from 'lucide-react';

export const Simulation: React.FC = () => {
  // Data States
  const [wallet, setWallet] = useState<WalletSession | null>(null);
  const [bets, setBets] = useState<SimulatedBet[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Filter States
  const [statusFilter, setStatusFilter] = useState<'all' | 'pending' | 'won' | 'lost'>('all');
  const [betTypeFilter, setBetTypeFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Strategy Configuration Form State
  const [targetDate, setTargetDate] = useState<string>('');
  const [minEv, setMinEv] = useState<number>(1.10);
  const [minProb, setMinProb] = useState<number>(0.10);
  const [betType, setBetType] = useState<string>('tansho');
  const [useKelly, setUseKelly] = useState<boolean>(true);
  const [kellyFraction, setKellyFraction] = useState<number>(0.25);
  const [fixedBetAmount, setFixedBetAmount] = useState<number>(1000);

  // Action Loading & Feedback
  const [isAutoBetting, setIsAutoBetting] = useState<boolean>(false);
  const [isSettling, setIsSettling] = useState<boolean>(false);
  const [isResetting, setIsResetting] = useState<boolean>(false);
  const [showResetConfirm, setShowResetConfirm] = useState<boolean>(false);
  const [resetPointsInput, setResetPointsInput] = useState<number>(100000);
  const [actionResult, setActionResult] = useState<{
    type: 'success' | 'error' | 'info';
    title: string;
    details?: string;
    items?: string[];
  } | null>(null);

  // Load Wallet and Bets History
  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true);
      const [walletData, betsData] = await Promise.all([
        api.getWallet('forward_live'),
        api.getSimulatedBets({ session_id: 'forward_live', limit: 100 }),
      ]);
      setWallet(walletData);
      setBets(betsData);
    } catch (err) {
      console.error('Failed to load simulation data:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Execute Auto-Bet
  const handleAutoBet = async () => {
    try {
      setIsAutoBetting(true);
      setActionResult(null);

      const payload: AutoBetRequest = {
        session_id: 'forward_live',
        target_date: targetDate || undefined,
        min_ev: Number(minEv),
        min_prob: Number(minProb),
        bet_type: betType,
        use_kelly: useKelly,
        kelly_fraction: useKelly ? Number(kellyFraction) : undefined,
        bet_amount: !useKelly ? Number(fixedBetAmount) : undefined,
      };

      const res: AutoBetResult = await api.autoBet(payload);

      const items = res.placed_bets.map(
        (b) =>
          `[${b.bet_type === 'tansho' ? '単勝' : '複勝'}] ${b.race_name || b.race_id} ${b.combination}番 (${b.bet_points.toLocaleString()} pt, EV ${b.expected_value_at_bet.toFixed(2)})`
      );

      setActionResult({
        type: 'success',
        title: `🎯 自動投票完了: ${res.placed_bets_count} 件の投票を実行しました`,
        details: `消費ポイント: ${res.total_points_spent.toLocaleString()} pt (残高: ${res.remaining_points.toLocaleString()} pt)`,
        items: items.length > 0 ? items.slice(0, 5) : undefined,
      });

      await fetchData();
    } catch (err: unknown) {
      console.error(err);
      setActionResult({
        type: 'error',
        title: '自動投票の実行に失敗しました',
        details: '出走前の対象レースが存在しないか、期待値条件に適合する買い目がありませんでした。',
      });
    } finally {
      setIsAutoBetting(false);
    }
  };

  // Execute Settle
  const handleSettle = async () => {
    try {
      setIsSettling(true);
      setActionResult(null);

      const res: SettleResult = await api.settleRaces('forward_live');

      const wonItems = res.settled_bets
        .filter((b) => b.status === 'won')
        .map(
          (b) =>
            `🎉 的中: ${b.race_name || b.race_id} ${b.combination}番 (+${b.profit.toLocaleString()} pt)`
        );

      setActionResult({
        type: 'success',
        title: `💰 自動精算完了: ${res.settled_bets_count} 件の投票を精算しました`,
        details: `現在のウォレット残高: ${res.current_points.toLocaleString()} pt`,
        items: wonItems.length > 0 ? wonItems : ['今回の精算対象レースで的中はありませんでした。'],
      });

      await fetchData();
    } catch (err: unknown) {
      console.error(err);
      setActionResult({
        type: 'error',
        title: 'レース結果精算に失敗しました',
        details: '確定済みの未精算レースがありませんでした。',
      });
    } finally {
      setIsSettling(false);
    }
  };

  // Reset Wallet
  const handleResetWallet = async () => {
    try {
      setIsResetting(true);
      await api.resetWallet(Number(resetPointsInput), 'forward_live');
      setShowResetConfirm(false);
      setActionResult({
        type: 'info',
        title: '🔄 ウォレットを初期化しました',
        details: `初期残高: ${Number(resetPointsInput).toLocaleString()} pt にリセットされました。`,
      });
      await fetchData();
    } catch (err) {
      console.error(err);
      setActionResult({
        type: 'error',
        title: 'ウォレット初期化に失敗しました',
      });
    } finally {
      setIsResetting(false);
    }
  };

  // Filter bets
  const filteredBets = useMemo(() => {
    return bets.filter((bet) => {
      if (statusFilter !== 'all' && bet.status !== statusFilter) return false;
      if (betTypeFilter !== 'all' && bet.bet_type !== betTypeFilter) return false;
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const raceMatch = (bet.race_name || bet.race_id).toLowerCase().includes(query);
        const combMatch = bet.combination.includes(query);
        if (!raceMatch && !combMatch) return false;
      }
      return true;
    });
  }, [bets, statusFilter, betTypeFilter, searchQuery]);

  // Aggregate stats for filtered bets
  const filteredSummary = useMemo(() => {
    const totalCount = filteredBets.length;
    const wonCount = filteredBets.filter((b) => b.status === 'won').length;
    const totalInvested = filteredBets.reduce((acc, b) => acc + b.bet_points, 0);
    const totalPayout = filteredBets.reduce((acc, b) => acc + (b.payout_points || 0), 0);
    const netProfit = totalPayout - totalInvested;
    const hitRate = totalCount > 0 ? (wonCount / totalCount) * 100 : 0;
    return { totalCount, wonCount, totalInvested, totalPayout, netProfit, hitRate };
  }, [filteredBets]);

  const initialPoints = wallet?.initial_points ?? 100000;
  const currentPoints = wallet?.current_points ?? 100000;
  const netProfit = currentPoints - initialPoints;
  const isPositive = netProfit >= 0;
  const roi = wallet?.roi ?? (wallet?.total_invested && wallet.total_invested > 0 ? (wallet.total_returned / wallet.total_invested) * 100 : 0);
  const winRate = wallet?.win_rate ?? (wallet?.total_bets && wallet.total_bets > 0 ? ((wallet.won_bets ?? 0) / wallet.total_bets) * 100 : 0);

  return (
    <div className="space-y-6">
      {/* Active Wallet Banner & Quick Stats */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-850 to-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">
                Live Simulation Control
              </span>
              <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                Session: forward_live
              </span>
            </div>
            <h1 className="text-2xl font-extrabold text-slate-100">
              リアルタイム疑似運用 (Forward Testing)
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 max-w-2xl">
              実際のオッズとLightGBM期待値予測に基づいて、出走前レースへの自動仮想投票とレース確定後の自動払戻清算をリアルタイムに行います。
            </p>
          </div>

          <div className="flex items-center gap-3 self-start lg:self-center">
            <button
              onClick={() => setShowResetConfirm(true)}
              className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-rose-400 border border-slate-700 hover:border-rose-900/60 text-xs font-medium transition"
              title="ウォレットと取引履歴をリセット"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>ウォレット初期化</span>
            </button>
            <button
              onClick={fetchData}
              disabled={isLoading}
              className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium transition"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-emerald-400' : ''}`} />
              <span>更新</span>
            </button>
          </div>
        </div>

        {/* Wallet Key Metrics Row */}
        <div className="mt-6 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 pt-6 border-t border-slate-800">
          <div className="bg-slate-900/80 rounded-xl p-3 border border-slate-800">
            <span className="text-[11px] text-slate-400">ウォレット残高</span>
            <div className="text-lg font-bold font-mono text-slate-100 mt-0.5">
              {currentPoints.toLocaleString()} <span className="text-xs text-slate-400">pt</span>
            </div>
            <span className="text-[10px] text-slate-500">初期: {initialPoints.toLocaleString()} pt</span>
          </div>

          <div className="bg-slate-900/80 rounded-xl p-3 border border-slate-800">
            <span className="text-[11px] text-slate-400">通算純損益</span>
            <div
              className={`text-lg font-bold font-mono mt-0.5 ${
                isPositive ? 'text-emerald-400' : 'text-rose-400'
              }`}
            >
              {isPositive ? '+' : ''}
              {netProfit.toLocaleString()} <span className="text-xs font-normal">pt</span>
            </div>
            <span className="text-[10px] text-slate-500">
              損益率: {initialPoints > 0 ? `${((netProfit / initialPoints) * 100).toFixed(1)}%` : '0.0%'}
            </span>
          </div>

          <div className="bg-slate-900/80 rounded-xl p-3 border border-slate-800">
            <span className="text-[11px] text-slate-400">通算回収率 (ROI)</span>
            <div
              className={`text-lg font-bold font-mono mt-0.5 ${
                roi >= 100 ? 'text-emerald-400' : roi > 0 ? 'text-amber-400' : 'text-slate-400'
              }`}
            >
              {roi.toFixed(1)}%
            </div>
            <span className="text-[10px] text-slate-500">
              総投資: {(wallet?.total_invested ?? 0).toLocaleString()} pt
            </span>
          </div>

          <div className="bg-slate-900/80 rounded-xl p-3 border border-slate-800">
            <span className="text-[11px] text-slate-400">的中率 / 投票数</span>
            <div className="text-lg font-bold font-mono text-cyan-400 mt-0.5">
              {winRate.toFixed(1)}%
            </div>
            <span className="text-[10px] text-slate-500">
              {wallet?.won_bets ?? 0} 勝 / {wallet?.total_bets ?? 0} 投票
            </span>
          </div>

          <div className="bg-slate-900/80 rounded-xl p-3 border border-slate-800">
            <span className="text-[11px] text-slate-400">総回収額</span>
            <div className="text-lg font-bold font-mono text-slate-200 mt-0.5">
              {(wallet?.total_returned ?? 0).toLocaleString()} <span className="text-xs text-slate-400">pt</span>
            </div>
            <span className="text-[10px] text-slate-500">精算済払戻合計</span>
          </div>

          <div className="bg-slate-900/80 rounded-xl p-3 border border-slate-800">
            <span className="text-[11px] text-slate-400">最大ドローダウン</span>
            <div className="text-lg font-bold font-mono text-purple-400 mt-0.5">
              -{((wallet?.max_drawdown ?? 0) * 100).toFixed(1)}%
            </div>
            <span className="text-[10px] text-slate-500">ピーク時からの最大下落</span>
          </div>
        </div>
      </div>

      {/* Action Notification Alert */}
      {actionResult && (
        <div
          className={`p-4 rounded-xl border text-xs transition-all ${
            actionResult.type === 'success'
              ? 'bg-emerald-950/70 border-emerald-800/80 text-emerald-300'
              : actionResult.type === 'error'
              ? 'bg-rose-950/70 border-rose-800/80 text-rose-300'
              : 'bg-cyan-950/70 border-cyan-800/80 text-cyan-300'
          }`}
        >
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <div className="flex items-center space-x-2 font-bold text-sm">
                {actionResult.type === 'success' ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-rose-400" />
                )}
                <span>{actionResult.title}</span>
              </div>
              {actionResult.details && <p className="text-slate-300">{actionResult.details}</p>}
              {actionResult.items && actionResult.items.length > 0 && (
                <ul className="mt-2 space-y-1 pl-4 list-disc text-[11px] text-slate-300">
                  {actionResult.items.map((it, idx) => (
                    <li key={idx}>{it}</li>
                  ))}
                </ul>
              )}
            </div>
            <button
              onClick={() => setActionResult(null)}
              className="text-slate-400 hover:text-slate-200 text-xs ml-3"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Strategy Configuration & Operations Grid */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm space-y-5">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center space-x-2">
            <Sliders className="w-4 h-4 text-emerald-400" />
            <h2 className="text-sm font-bold text-slate-200">投資戦略 ＆ ボット運用パラメータ設定</h2>
          </div>
          <span className="text-xs text-slate-400">
            条件に合致した買い目を自動抽出して投票します
          </span>
        </div>

        {/* Configuration Controls */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          {/* Target Date */}
          <div className="bg-slate-850 p-3.5 rounded-lg border border-slate-800 space-y-2">
            <label className="text-xs text-slate-300 font-medium flex items-center space-x-1">
              <Calendar className="w-3.5 h-3.5 text-emerald-400" />
              <span>対象日付 (空欄で全レース)</span>
            </label>
            <input
              type="date"
              value={targetDate}
              onChange={(e) => setTargetDate(e.target.value)}
              className="w-full bg-slate-800 text-slate-200 border border-slate-700 rounded px-2 py-1.5 text-xs font-mono"
            />
            <div className="text-[10px] text-slate-500">
              {targetDate ? `${targetDate} のレースのみ` : '全出走前レースが対象'}
            </div>
          </div>

          {/* Min EV Slider */}
          <div className="bg-slate-850 p-3.5 rounded-lg border border-slate-800 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-300 font-medium">最小期待値 (Min EV)</span>
              <span className="font-mono font-bold text-emerald-400 bg-emerald-950 px-2 py-0.5 rounded border border-emerald-800">
                {minEv.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min="1.00"
              max="2.50"
              step="0.05"
              value={minEv}
              onChange={(e) => setMinEv(parseFloat(e.target.value))}
              className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-emerald-500"
            />
            <div className="flex justify-between text-[10px] text-slate-500">
              <span>1.00 (損益分岐)</span>
              <span>1.50</span>
              <span>2.50 (厳選)</span>
            </div>
          </div>

          {/* Min Prob Slider */}
          <div className="bg-slate-850 p-3.5 rounded-lg border border-slate-800 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-300 font-medium">最小勝率 (Min Prob)</span>
              <span className="font-mono font-bold text-cyan-400 bg-cyan-950 px-2 py-0.5 rounded border border-cyan-800">
                {(minProb * 100).toFixed(0)}%
              </span>
            </div>
            <input
              type="range"
              min="0.05"
              max="0.50"
              step="0.01"
              value={minProb}
              onChange={(e) => setMinProb(parseFloat(e.target.value))}
              className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
            />
            <div className="flex justify-between text-[10px] text-slate-500">
              <span>5% (穴狙い)</span>
              <span>20%</span>
              <span>50% (本命)</span>
            </div>
          </div>

          {/* Bet Type Selection */}
          <div className="bg-slate-850 p-3.5 rounded-lg border border-slate-800 space-y-2">
            <label className="text-xs text-slate-300 font-medium block">対象券種</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setBetType('tansho')}
                className={`py-1.5 text-xs font-semibold rounded-md border transition ${
                  betType === 'tansho'
                    ? 'bg-emerald-600 text-white border-emerald-500 shadow-sm'
                    : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-slate-200'
                }`}
              >
                単勝 (Win)
              </button>
              <button
                type="button"
                onClick={() => setBetType('fukusho')}
                className={`py-1.5 text-xs font-semibold rounded-md border transition ${
                  betType === 'fukusho'
                    ? 'bg-cyan-600 text-white border-cyan-500 shadow-sm'
                    : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-slate-200'
                }`}
              >
                複勝 (Place)
              </button>
            </div>
            <div className="text-[10px] text-slate-500 text-center">
              {betType === 'tansho' ? '1着的中・高配当' : '3着以内・高勝率'}
            </div>
          </div>

          {/* Sizing & Kelly Settings */}
          <div className="bg-slate-850 p-3.5 rounded-lg border border-slate-800 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-300 font-medium">資金配分方式</span>
              <button
                type="button"
                onClick={() => setUseKelly(!useKelly)}
                className={`text-[10px] px-2 py-0.5 rounded font-mono font-semibold border ${
                  useKelly
                    ? 'bg-emerald-950 text-emerald-400 border-emerald-700'
                    : 'bg-slate-800 text-slate-400 border-slate-700'
                }`}
              >
                {useKelly ? 'ケリー基準' : '固定ベット'}
              </button>
            </div>

            {useKelly ? (
              <div className="space-y-1">
                <div className="flex justify-between text-[11px] text-slate-400">
                  <span>倍率:</span>
                  <span className="font-mono text-emerald-400 font-semibold">{kellyFraction.toFixed(2)}x</span>
                </div>
                <input
                  type="range"
                  min="0.10"
                  max="1.00"
                  step="0.05"
                  value={kellyFraction}
                  onChange={(e) => setKellyFraction(parseFloat(e.target.value))}
                  className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-emerald-500"
                />
              </div>
            ) : (
              <div className="space-y-1">
                <div className="flex justify-between text-[11px] text-slate-400">
                  <span>1点金額:</span>
                  <span className="font-mono text-slate-200 font-semibold">{fixedBetAmount.toLocaleString()} pt</span>
                </div>
                <select
                  value={fixedBetAmount}
                  onChange={(e) => setFixedBetAmount(Number(e.target.value))}
                  className="w-full bg-slate-800 text-slate-200 border border-slate-700 rounded px-2 py-1 text-xs"
                >
                  <option value={500}>500 pt</option>
                  <option value={1000}>1,000 pt (標準)</option>
                  <option value={2000}>2,000 pt</option>
                  <option value={5000}>5,000 pt</option>
                  <option value={10000}>10,000 pt</option>
                </select>
              </div>
            )}
          </div>
        </div>

        {/* Action Buttons Row */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-800">
          <div className="flex items-center space-x-2 text-xs text-slate-400">
            <Info className="w-3.5 h-3.5 text-slate-500" />
            <span>設定条件を満たす出走前レースに自動で投票・確定後に自動で払い戻しが行われます。</span>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={handleAutoBet}
              disabled={isAutoBetting}
              className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs sm:text-sm shadow-lg shadow-emerald-950/60 transition disabled:opacity-50"
            >
              <PlayCircle className={`w-4 h-4 ${isAutoBetting ? 'animate-spin' : ''}`} />
              <span>{isAutoBetting ? '自動投票実行中...' : '🎯 未発走レースに自動投票 (Auto-Bet)'}</span>
            </button>

            <button
              onClick={handleSettle}
              disabled={isSettling}
              className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs sm:text-sm shadow-lg shadow-cyan-950/60 transition disabled:opacity-50"
            >
              <Coins className={`w-4 h-4 ${isSettling ? 'animate-spin' : ''}`} />
              <span>{isSettling ? '自動精算処理中...' : '💰 確定レースを自動精算 (Settle)'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Filterable Simulated Bets Table Section */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
        {/* Table Header & Filters */}
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-3 border-b border-slate-800">
          <div className="flex items-center space-x-2">
            <Clock className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-bold text-slate-200">疑似投票・取引履歴明細 ({filteredBets.length} 件)</h3>
          </div>

          {/* Search and Filter Controls */}
          <div className="flex flex-wrap items-center gap-2">
            {/* Search Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="レース名・馬番検索..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8 pr-3 py-1 bg-slate-800 text-slate-200 border border-slate-700 rounded-lg text-xs w-44 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500"
              />
            </div>

            {/* Status Tabs */}
            <div className="flex items-center bg-slate-800/90 rounded-lg p-1 border border-slate-700 text-xs">
              <button
                onClick={() => setStatusFilter('all')}
                className={`px-2.5 py-1 rounded-md transition ${
                  statusFilter === 'all'
                    ? 'bg-slate-700 text-white font-semibold shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                すべて ({bets.length})
              </button>
              <button
                onClick={() => setStatusFilter('pending')}
                className={`px-2.5 py-1 rounded-md transition ${
                  statusFilter === 'pending'
                    ? 'bg-amber-950 text-amber-300 font-semibold border border-amber-800 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                結果待ち ({bets.filter((b) => b.status === 'pending').length})
              </button>
              <button
                onClick={() => setStatusFilter('won')}
                className={`px-2.5 py-1 rounded-md transition ${
                  statusFilter === 'won'
                    ? 'bg-emerald-950 text-emerald-300 font-semibold border border-emerald-800 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                的中 ({bets.filter((b) => b.status === 'won').length})
              </button>
              <button
                onClick={() => setStatusFilter('lost')}
                className={`px-2.5 py-1 rounded-md transition ${
                  statusFilter === 'lost'
                    ? 'bg-slate-700 text-rose-300 font-semibold shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                不的中 ({bets.filter((b) => b.status === 'lost').length})
              </button>
            </div>

            {/* Bet Type Filter */}
            <select
              value={betTypeFilter}
              onChange={(e) => setBetTypeFilter(e.target.value)}
              className="bg-slate-800 text-slate-300 border border-slate-700 rounded-lg px-2.5 py-1 text-xs"
            >
              <option value="all">全券種</option>
              <option value="tansho">単勝のみ</option>
              <option value="fukusho">複勝のみ</option>
            </select>
          </div>
        </div>

        {/* Filtered Aggregation Summary Bar */}
        <div className="bg-slate-850 rounded-lg p-3 border border-slate-800/80 flex flex-wrap items-center justify-between gap-4 text-xs">
          <div className="flex items-center space-x-4">
            <span className="text-slate-400">
              表示中: <strong className="text-slate-200 font-mono">{filteredSummary.totalCount} 件</strong>
            </span>
            <span className="text-slate-400">
              的中: <strong className="text-emerald-400 font-mono">{filteredSummary.wonCount} 件 ({filteredSummary.hitRate.toFixed(1)}%)</strong>
            </span>
            <span className="text-slate-400">
              総投資: <strong className="text-slate-200 font-mono">{filteredSummary.totalInvested.toLocaleString()} pt</strong>
            </span>
          </div>

          <div className="flex items-center space-x-3 font-mono">
            <span className="text-slate-400">抽出内損益:</span>
            <span
              className={`font-bold ${
                filteredSummary.netProfit >= 0 ? 'text-emerald-400' : 'text-rose-400'
              }`}
            >
              {filteredSummary.netProfit >= 0 ? '+' : ''}
              {filteredSummary.netProfit.toLocaleString()} pt
            </span>
          </div>
        </div>

        {/* Table Content */}
        {filteredBets.length === 0 ? (
          <div className="py-16 text-center text-slate-500 text-xs">
            該当するシミュレーション投票履歴はありません。
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 bg-slate-900/50">
                  <th className="py-2.5 px-3 font-medium">投票日時</th>
                  <th className="py-2.5 px-3 font-medium">レース情報</th>
                  <th className="py-2.5 px-3 font-medium">券種</th>
                  <th className="py-2.5 px-3 font-medium text-center">馬番</th>
                  <th className="py-2.5 px-3 font-medium text-right">投票額</th>
                  <th className="py-2.5 px-3 font-medium text-right">オッズ</th>
                  <th className="py-2.5 px-3 font-medium text-right">期待値</th>
                  <th className="py-2.5 px-3 font-medium text-center">ステータス</th>
                  <th className="py-2.5 px-3 font-medium text-right">払戻金</th>
                  <th className="py-2.5 px-3 font-medium text-right">損益</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredBets.map((bet, idx) => {
                  const isWon = bet.status === 'won';
                  const isPending = bet.status === 'pending';
                  const isLost = bet.status === 'lost';

                  return (
                    <tr key={bet.id || idx} className="hover:bg-slate-800/40 transition">
                      <td className="py-3 px-3 text-slate-400 font-mono text-[11px] whitespace-nowrap">
                        {bet.created_at ? bet.created_at.slice(0, 16).replace('T', ' ') : '-'}
                      </td>
                      <td className="py-3 px-3 whitespace-nowrap">
                        <div className="font-semibold text-slate-200">
                          {bet.race_name || bet.race_id}
                        </div>
                        <div className="text-[10px] text-slate-500 font-mono">
                          {bet.race_date || bet.race_id}
                        </div>
                      </td>
                      <td className="py-3 px-3 whitespace-nowrap">
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-medium text-[11px] border border-slate-700">
                          {bet.bet_type === 'tansho' ? '単勝' : bet.bet_type === 'fukusho' ? '複勝' : bet.bet_type}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-center whitespace-nowrap">
                        <span className="font-mono font-bold text-sm px-2 py-0.5 rounded-full bg-slate-800 text-slate-100 border border-slate-700">
                          {bet.combination}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-right font-mono font-semibold text-slate-200 whitespace-nowrap">
                        {bet.bet_points.toLocaleString()} pt
                      </td>
                      <td className="py-3 px-3 text-right font-mono text-slate-300 whitespace-nowrap">
                        {bet.odds_at_bet.toFixed(1)}倍
                      </td>
                      <td className="py-3 px-3 text-right whitespace-nowrap">
                        <EVBadge ev={bet.expected_value_at_bet} size="sm" showIcon={false} />
                      </td>
                      <td className="py-3 px-3 text-center whitespace-nowrap">
                        {isWon ? (
                          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-600 shadow-sm shadow-emerald-950">
                            的中 🎉
                          </span>
                        ) : isPending ? (
                          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-medium bg-amber-950/80 text-amber-300 border border-amber-700 animate-pulse">
                            結果待ち
                          </span>
                        ) : isLost ? (
                          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-medium bg-slate-800 text-slate-400 border border-slate-700">
                            不的中
                          </span>
                        ) : (
                          <span className="text-slate-500">{bet.status}</span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-right font-mono text-slate-300 whitespace-nowrap">
                        {isWon ? (
                          <span className="text-emerald-400 font-bold">{bet.payout_points.toLocaleString()} pt</span>
                        ) : isPending ? (
                          <span className="text-slate-500">-</span>
                        ) : (
                          <span className="text-slate-500">0 pt</span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-right font-mono font-bold whitespace-nowrap">
                        {isWon ? (
                          <span className="text-emerald-400">+{bet.profit.toLocaleString()} pt</span>
                        ) : isPending ? (
                          <span className="text-slate-500">-</span>
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

      {/* Reset Confirmation Modal */}
      {showResetConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-fadeIn">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-full bg-rose-950/80 border border-rose-800/80 flex items-center justify-center text-rose-400">
                <RotateCcw className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-100">ウォレット残高・取引履歴の初期化</h3>
                <p className="text-xs text-slate-400">
                  疑似運用の取引履歴と統計値がすべてリセットされます。
                </p>
              </div>
            </div>

            <div className="space-y-2 pt-2">
              <label className="text-xs text-slate-300 font-medium block">初期資金設定 (pt):</label>
              <input
                type="number"
                value={resetPointsInput}
                onChange={(e) => setResetPointsInput(Number(e.target.value))}
                min="1000"
                step="10000"
                className="w-full bg-slate-800 text-slate-100 border border-slate-700 rounded-lg px-3 py-2 text-sm font-mono focus:border-emerald-500 focus:outline-none"
              />
            </div>

            <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setShowResetConfirm(false)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition"
              >
                キャンセル
              </button>
              <button
                type="button"
                onClick={handleResetWallet}
                disabled={isResetting}
                className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold transition shadow-lg shadow-rose-950/50 disabled:opacity-50"
              >
                {isResetting ? '初期化中...' : '初期化を実行する'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Simulation;
