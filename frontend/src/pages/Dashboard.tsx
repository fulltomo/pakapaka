import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  WalletSession,
  ActiveModelStatus,
  SimulatedBet,
  Race,
  EquityPoint,
} from '../types';
import { api } from '../services/api';
import { StatCard } from '../components/StatCard';
import { EquityChart } from '../components/EquityChart';
import { RecommendationBadge, EVBadge } from '../components/PredictionBadge';
import {
  Wallet,
  TrendingUp,
  Percent,
  Trophy,
  ShieldAlert,
  BrainCircuit,
  PlayCircle,
  Coins,
  RefreshCw,
  Database,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  Sparkles,
  Calendar,
} from 'lucide-react';
import { NavTab } from '../components/Navbar';

interface DashboardProps {
  onNavigate?: (tab: NavTab) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ onNavigate }) => {
  const [wallet, setWallet] = useState<WalletSession | null>(null);
  const [activeModel, setActiveModel] = useState<ActiveModelStatus | null>(null);
  const [recentBets, setRecentBets] = useState<SimulatedBet[]>([]);
  const [scheduledRaces, setScheduledRaces] = useState<Race[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Action states
  const [isAutoBetting, setIsAutoBetting] = useState<boolean>(false);
  const [isSettling, setIsSettling] = useState<boolean>(false);
  const [isGeneratingSample, setIsGeneratingSample] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error' | 'info'; message: string } | null>(null);

  const loadDashboardData = useCallback(async () => {
    try {
      setIsLoading(true);
      const [walletData, modelData, betsData, racesData] = await Promise.allSettled([
        api.getWallet('forward_live'),
        api.getActiveModel(),
        api.getSimulatedBets({ session_id: 'forward_live', limit: 50 }),
        api.getRaces({ status: 'scheduled', limit: 5 }),
      ]);

      if (walletData.status === 'fulfilled') setWallet(walletData.value);
      if (modelData.status === 'fulfilled') setActiveModel(modelData.value);
      if (betsData.status === 'fulfilled') setRecentBets(betsData.value);
      if (racesData.status === 'fulfilled') setScheduledRaces(racesData.value);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  // Construct equity curve from simulated bets
  const equityData: EquityPoint[] = useMemo(() => {
    const initialPoints = wallet?.initial_points ?? 100000;
    if (!recentBets || recentBets.length === 0) {
      return [
        {
          date: '開始時',
          race_id: '-',
          balance: initialPoints,
          cumulative_profit: 0,
          drawdown: 0,
        },
      ];
    }

    // Sort bets chronologically (oldest first)
    const settledBets = [...recentBets]
      .filter((b) => b.status === 'won' || b.status === 'lost')
      .reverse();

    if (settledBets.length === 0) {
      return [
        {
          date: '開始時',
          race_id: '-',
          balance: initialPoints,
          cumulative_profit: 0,
          drawdown: 0,
        },
      ];
    }

    let runningBalance = initialPoints;
    let peakBalance = initialPoints;
    const points: EquityPoint[] = [
      {
        date: '開始時',
        race_id: 'start',
        balance: initialPoints,
        cumulative_profit: 0,
        drawdown: 0,
      },
    ];

    settledBets.forEach((bet) => {
      runningBalance += bet.profit;
      if (runningBalance > peakBalance) peakBalance = runningBalance;
      const dd = peakBalance > 0 ? (peakBalance - runningBalance) / peakBalance : 0;
      points.push({
        date: bet.race_date || bet.created_at?.slice(0, 10) || `Bet #${bet.id}`,
        race_id: bet.race_id,
        balance: runningBalance,
        cumulative_profit: runningBalance - initialPoints,
        drawdown: dd,
      });
    });

    return points;
  }, [recentBets, wallet?.initial_points]);

  // Quick Action: Auto-Bet
  const handleAutoBet = async () => {
    try {
      setIsAutoBetting(true);
      setFeedback(null);
      const res = await api.autoBet({
        session_id: 'forward_live',
        min_ev: 1.1,
        use_kelly: true,
        kelly_fraction: 0.25,
      });
      setFeedback({
        type: 'success',
        message: `🎯 自動投票完了: ${res.placed_bets_count} 件の買い目（合計 ${res.total_points_spent.toLocaleString()} pt）を投票しました。`,
      });
      await loadDashboardData();
    } catch (err: unknown) {
      console.error(err);
      setFeedback({
        type: 'error',
        message: '自動投票の実行中にエラーが発生しました。',
      });
    } finally {
      setIsAutoBetting(false);
    }
  };

  // Quick Action: Settle Races
  const handleSettle = async () => {
    try {
      setIsSettling(true);
      setFeedback(null);
      const res = await api.settleRaces('forward_live');
      setFeedback({
        type: 'success',
        message: `💰 自動精算完了: ${res.settled_bets_count} 件の投票を精算しました。残高: ${res.current_points.toLocaleString()} pt`,
      });
      await loadDashboardData();
    } catch (err: unknown) {
      console.error(err);
      setFeedback({
        type: 'error',
        message: 'レース結果精算の実行中にエラーが発生しました。',
      });
    } finally {
      setIsSettling(false);
    }
  };

  // Quick Action: Fetch / Update Race Data
  const handleGenerateSample = async () => {
    try {
      setIsGeneratingSample(true);
      setFeedback(null);
      const res = await api.generateSampleData(30, 6, '2024-01-06');
      setFeedback({
        type: 'success',
        message: `🎲 サンプルレース ${res.generated_races} 件の生成に成功しました。`,
      });
      await loadDashboardData();
    } catch (err: unknown) {
      console.error(err);
      setFeedback({
        type: 'error',
        message: 'サンプルデータ生成中にエラーが発生しました。',
      });
    } finally {
      setIsGeneratingSample(false);
    }
  };

  const initialPoints = wallet?.initial_points ?? 100000;
  const currentPoints = wallet?.current_points ?? 100000;
  const profit = wallet?.profit ?? (currentPoints - initialPoints);
  const isPositiveProfit = profit >= 0;
  const roi = wallet?.roi ?? (wallet?.total_invested && wallet.total_invested > 0 ? (wallet.total_returned / wallet.total_invested) * 100 : 0);
  const winRate = wallet?.win_rate ?? (wallet?.total_bets && wallet.total_bets > 0 ? ((wallet.won_bets ?? 0) / wallet.total_bets) * 100 : 0);
  const wonBets = wallet?.won_bets ?? 0;
  const totalBets = wallet?.total_bets ?? 0;
  const rawDd = wallet?.max_drawdown ?? 0;
  const maxDrawdown = rawDd > 1 ? rawDd : rawDd * 100;

  return (
    <div className="space-y-6">
      {/* Hero / Executive Overview Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-800 border border-slate-800 p-6 sm:p-7 shadow-xl">
        <div className="absolute top-0 right-0 -mt-10 -mr-10 w-64 h-64 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-1/3 -mb-10 w-48 h-48 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-emerald-950/80 border border-emerald-700/60 text-emerald-300 text-xs font-semibold">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span>AI自動運用エンジン稼働中</span>
              </span>
              <span className="text-xs px-2.5 py-1 rounded-full bg-slate-800/80 border border-slate-700 text-slate-300 font-mono">
                Model: {activeModel?.model_version || 'LightGBM EV v1'}
              </span>
            </div>

            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              PakaPaka AI 競馬投資ダッシュボード
            </h1>
            <p className="text-sm text-slate-400 max-w-2xl leading-relaxed">
              JRAレース出馬表とオッズの歪み（期待値 &gt; 1.0）をLightGBM機械学習モデルで検出し、ケリー基準で最適投資を行うリアルタイム資産シミュレーターです。
            </p>
          </div>

          {/* Quick Refresh & Navigation */}
          <div className="flex items-center gap-3 self-start lg:self-center shrink-0">
            <button
              onClick={loadDashboardData}
              disabled={isLoading}
              className="flex items-center space-x-2 px-3.5 py-2.5 rounded-xl bg-slate-800/90 hover:bg-slate-700/90 text-slate-200 border border-slate-700 text-xs font-medium transition shadow-sm"
              title="データを再取得"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-emerald-400' : ''}`} />
              <span>最新データ更新</span>
            </button>
            {onNavigate && (
              <button
                onClick={() => onNavigate('races')}
                className="flex items-center space-x-1.5 px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition shadow-lg shadow-emerald-950/50"
              >
                <span>レース・予想を見る</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Feedback / Notification Banner */}
        {feedback && (
          <div
            className={`mt-5 p-3.5 rounded-xl border text-xs flex items-center justify-between transition-all animate-fadeIn ${
              feedback.type === 'success'
                ? 'bg-emerald-950/70 border-emerald-800/80 text-emerald-300'
                : feedback.type === 'error'
                ? 'bg-rose-950/70 border-rose-800/80 text-rose-300'
                : 'bg-cyan-950/70 border-cyan-800/80 text-cyan-300'
            }`}
          >
            <div className="flex items-center space-x-2">
              {feedback.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              )}
              <span>{feedback.message}</span>
            </div>
            <button
              onClick={() => setFeedback(null)}
              className="text-slate-400 hover:text-slate-200 text-xs ml-3"
            >
              ✕
            </button>
          </div>
        )}
      </div>

      {/* 6 Executive Metric StatCards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <StatCard
          title="ウォレット残高"
          value={`${currentPoints.toLocaleString()} pt`}
          subtitle={`初期: ${initialPoints.toLocaleString()} pt`}
          icon={Wallet}
          color="emerald"
          badge="Live"
          trend={{
            value: `${isPositiveProfit ? '+' : ''}${profit.toLocaleString()} pt`,
            isPositive: isPositiveProfit,
          }}
          loading={isLoading}
        />

        <StatCard
          title="通算純損益"
          value={`${isPositiveProfit ? '+' : ''}${profit.toLocaleString()} pt`}
          subtitle={`総投資: ${(wallet?.total_invested ?? 0).toLocaleString()} pt`}
          icon={TrendingUp}
          color={isPositiveProfit ? 'emerald' : 'red'}
          trend={{
            value: `${roi > 0 ? `${roi.toFixed(1)}%` : '0.0%'}`,
            isPositive: isPositiveProfit,
            label: 'ROI',
          }}
          loading={isLoading}
        />

        <StatCard
          title="通算回収率 (ROI)"
          value={`${roi.toFixed(1)}%`}
          subtitle={`総払戻: ${(wallet?.total_returned ?? 0).toLocaleString()} pt`}
          icon={Percent}
          color={roi >= 100 ? 'emerald' : roi > 0 ? 'amber' : 'slate'}
          trend={{
            value: roi >= 100 ? '黒字運用' : roi > 0 ? '運用中' : '未取引',
            isPositive: roi >= 100,
          }}
          loading={isLoading}
        />

        <StatCard
          title="的中率 ＆ 投票数"
          value={`${winRate.toFixed(1)}%`}
          subtitle={`${wonBets} 的中 / ${totalBets} 投票`}
          icon={Trophy}
          color="cyan"
          badge={`${wonBets}勝`}
          loading={isLoading}
        />

        <StatCard
          title="最大ドローダウン"
          value={`-${maxDrawdown.toFixed(1)}%`}
          subtitle="資産管理リスク指標"
          icon={ShieldAlert}
          color={maxDrawdown > 20 ? 'red' : 'purple'}
          trend={{
            value: maxDrawdown <= 15 ? '適正範囲' : '注意',
            isPositive: maxDrawdown <= 15,
          }}
          loading={isLoading}
        />

        <StatCard
          title="AI自動運用ステータス"
          value="常時稼働中"
          subtitle="期待値連動・最適配分"
          icon={BrainCircuit}
          color="blue"
          badge="Active"
          trend={{
            value: '最適化済',
            isPositive: true,
            label: '状態',
          }}
          loading={isLoading}
        />
      </div>

      {/* Quick Action Control Bar */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
          <div className="flex items-center space-x-2 text-xs font-semibold text-slate-300">
            <Sparkles className="w-4 h-4 text-emerald-400" />
            <span>AI運用アクション:</span>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <button
              onClick={handleAutoBet}
              disabled={isAutoBetting}
              className="flex items-center space-x-1.5 px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition shadow-md shadow-emerald-950/40 disabled:opacity-50"
            >
              <PlayCircle className={`w-3.5 h-3.5 ${isAutoBetting ? 'animate-spin' : ''}`} />
              <span>{isAutoBetting ? '自動投票中...' : '🎯 未発走レースに自動投票'}</span>
            </button>

            <button
              onClick={handleSettle}
              disabled={isSettling}
              className="flex items-center space-x-1.5 px-3.5 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-medium transition shadow-md shadow-cyan-950/40 disabled:opacity-50"
            >
              <Coins className={`w-3.5 h-3.5 ${isSettling ? 'animate-spin' : ''}`} />
              <span>{isSettling ? '精算中...' : '💰 確定レースを自動精算'}</span>
            </button>

            <button
              onClick={handleGenerateSample}
              disabled={isGeneratingSample}
              className="flex items-center space-x-1.5 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-medium transition disabled:opacity-50"
            >
              <Database className={`w-3.5 h-3.5 ${isGeneratingSample ? 'animate-spin' : ''}`} />
              <span>{isGeneratingSample ? '更新中...' : '🔄 最新レース情報を取得'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Equity Progression Chart */}
      <EquityChart
        data={equityData}
        initialBalance={initialPoints}
        height={320}
        title="ウォレット資産推移 (Equity Progression Curve)"
        currencyLabel="pt"
      />

      {/* Two Column Grid: Recent Simulated Bets & Upcoming Races */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (7 cols): Recent Simulated Bets Table */}
        <div className="lg:col-span-7 bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <Trophy className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-bold text-slate-200">直近の投票 ＆ 的中速報</h3>
              </div>
              {onNavigate && (
                <button
                  onClick={() => onNavigate('simulation')}
                  className="text-xs text-emerald-400 hover:text-emerald-300 font-medium flex items-center space-x-1"
                >
                  <span>すべて見る</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              )}
            </div>

            {recentBets.length === 0 ? (
              <div className="py-12 text-center text-slate-500 text-xs">
                まだシミュレーション投票履歴がありません。「🎯 未発走レースに自動投票」を実行してください。
              </div>
            ) : (
              <div className="mt-3 overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400">
                      <th className="pb-2 font-medium">レース</th>
                      <th className="pb-2 font-medium">券種/馬番</th>
                      <th className="pb-2 font-medium text-right">投票額</th>
                      <th className="pb-2 font-medium text-right">オッズ/EV</th>
                      <th className="pb-2 font-medium text-center">結果</th>
                      <th className="pb-2 font-medium text-right">損益</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {recentBets.slice(0, 7).map((bet, idx) => {
                      const isWon = bet.status === 'won';
                      const isPending = bet.status === 'pending';
                      const isLost = bet.status === 'lost';

                      return (
                        <tr key={bet.id || idx} className="hover:bg-slate-800/40 transition">
                          <td className="py-2.5 pr-2">
                            <div className="font-semibold text-slate-200 truncate max-w-[130px]">
                              {bet.race_name || bet.race_id}
                            </div>
                            <div className="text-[10px] text-slate-500">{bet.race_date || bet.created_at?.slice(0, 10) || '-'}</div>
                          </td>
                          <td className="py-2.5 pr-2">
                            <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-medium text-[11px] mr-1">
                              {bet.bet_type === 'tansho' ? '単勝' : bet.bet_type === 'fukusho' ? '複勝' : bet.bet_type}
                            </span>
                            <span className="font-mono font-bold text-slate-200">{bet.combination}番</span>
                          </td>
                          <td className="py-2.5 pr-2 text-right font-mono text-slate-300">
                            {bet.bet_points.toLocaleString()} pt
                          </td>
                          <td className="py-2.5 pr-2 text-right font-mono">
                            <div className="text-slate-300">{bet.odds_at_bet.toFixed(1)}倍</div>
                            <div className="text-[10px] text-emerald-400">EV {bet.expected_value_at_bet.toFixed(2)}</div>
                          </td>
                          <td className="py-2.5 text-center">
                            {isWon ? (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-600 shadow-sm shadow-emerald-950">
                                的中 🎉
                              </span>
                            ) : isPending ? (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-950/80 text-amber-300 border border-amber-700 animate-pulse">
                                結果待ち
                              </span>
                            ) : isLost ? (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-800 text-slate-400 border border-slate-700">
                                不的中
                              </span>
                            ) : (
                              <span className="text-slate-500">{bet.status}</span>
                            )}
                          </td>
                          <td className="py-2.5 pl-2 text-right font-mono font-bold">
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

          <div className="mt-3 pt-3 border-t border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
            <span>直近 {recentBets.length} 件中 {recentBets.filter(b => b.status === 'won').length} 件的中</span>
            {onNavigate && (
              <button
                onClick={() => onNavigate('simulation')}
                className="text-emerald-400 hover:underline flex items-center space-x-1"
              >
                <span>フォワード運用設定を開く</span>
                <ArrowRight className="w-3 h-3" />
              </button>
            )}
          </div>
        </div>

        {/* Right Column (5 cols): Upcoming Races Preview */}
        <div className="lg:col-span-5 bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <Calendar className="w-4 h-4 text-cyan-400" />
                <h3 className="text-sm font-bold text-slate-200">出走予定レース (Scheduled)</h3>
              </div>
              {onNavigate && (
                <button
                  onClick={() => onNavigate('races')}
                  className="text-xs text-cyan-400 hover:text-cyan-300 font-medium flex items-center space-x-1"
                >
                  <span>全レース</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              )}
            </div>

            {scheduledRaces.length === 0 ? (
              <div className="py-12 text-center text-slate-500 text-xs">
                出走予定レースはありません。「🎲 サンプル生成」でテスト用レースを追加できます。
              </div>
            ) : (
              <div className="mt-3 space-y-2.5">
                {scheduledRaces.map((race) => {
                  const topPick = race.predictions?.find((p) => p.recommendation_mark === '◎');

                  return (
                    <div
                      key={race.id}
                      onClick={() => onNavigate && onNavigate('races')}
                      className="p-3 rounded-lg bg-slate-850 border border-slate-800 hover:border-slate-700 hover:bg-slate-800 transition cursor-pointer flex items-center justify-between group"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center space-x-2">
                          <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-[10px] font-mono font-bold">
                            {race.race_number}R
                          </span>
                          <span className="text-xs font-bold text-slate-200 group-hover:text-emerald-300 transition truncate max-w-[150px]">
                            {race.race_name}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-400 flex items-center space-x-2">
                          <span>{race.race_course}</span>
                          <span>•</span>
                          <span>{race.surface} {race.distance}m</span>
                          <span>•</span>
                          <span>{race.date}</span>
                        </div>
                      </div>

                      <div className="flex items-center space-x-2 shrink-0">
                        {topPick ? (
                          <div className="flex items-center space-x-1 bg-slate-900 px-2 py-1 rounded border border-slate-800">
                            <RecommendationBadge mark="◎" size="sm" />
                            <span className="font-mono text-xs text-slate-200 font-bold">{topPick.horse_number}番</span>
                            <EVBadge ev={topPick.expected_value} size="sm" showIcon={false} />
                          </div>
                        ) : (
                          <span className="text-[10px] text-slate-500">AI予想済</span>
                        )}
                        <ArrowRight className="w-3.5 h-3.5 text-slate-600 group-hover:text-emerald-400 group-hover:translate-x-0.5 transition" />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between text-xs">
            <span className="text-slate-400">出走前レース数: {scheduledRaces.length} 件</span>
            <button
              onClick={handleAutoBet}
              disabled={isAutoBetting || scheduledRaces.length === 0}
              className="px-3 py-1.5 rounded-lg bg-emerald-600/90 hover:bg-emerald-500 text-white font-medium text-xs flex items-center space-x-1 disabled:opacity-40 transition"
            >
              <span>このレースに自動投票</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
