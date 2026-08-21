import React, { useState, useEffect, useCallback } from 'react';
import { Navbar, NavTab } from './components/Navbar';
import { WalletSession, ActiveModelStatus } from './types';
import { api } from './services/api';
import {
  Trophy,
  PlayCircle,
  BarChart3,
  BrainCircuit,
  Database,
  CheckCircle2,
} from 'lucide-react';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavTab>('dashboard');
  const [wallet, setWallet] = useState<WalletSession | null>(null);
  const [isLoadingWallet, setIsLoadingWallet] = useState<boolean>(false);
  const [activeModel, setActiveModel] = useState<ActiveModelStatus | null>(null);
  const [sampleDataStatus, setSampleDataStatus] = useState<string | null>(null);
  const [isGeneratingSample, setIsGeneratingSample] = useState<boolean>(false);

  const fetchWallet = useCallback(async () => {
    try {
      setIsLoadingWallet(true);
      const data = await api.getWallet('forward_live');
      setWallet(data);
    } catch (err) {
      console.error('Failed to fetch wallet info:', err);
    } finally {
      setIsLoadingWallet(false);
    }
  }, []);

  const fetchActiveModel = useCallback(async () => {
    try {
      const data = await api.getActiveModel();
      setActiveModel(data);
    } catch (err) {
      console.error('Failed to fetch active model:', err);
    }
  }, []);

  useEffect(() => {
    fetchWallet();
    fetchActiveModel();
  }, [fetchWallet, fetchActiveModel]);

  const handleGenerateSampleData = async () => {
    try {
      setIsGeneratingSample(true);
      setSampleDataStatus(null);
      const res = await api.generateSampleData(30, 6, '2024-01-06');
      setSampleDataStatus(`サンプルレース ${res.generated_races} 件の生成に成功しました！`);
      fetchWallet();
    } catch (err: unknown) {
      console.error(err);
      setSampleDataStatus('サンプルデータの生成に失敗しました。');
    } finally {
      setIsGeneratingSample(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100">
      {/* Header & Navbar */}
      <Navbar
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        wallet={wallet}
        isLoadingWallet={isLoadingWallet}
        onRefreshWallet={fetchWallet}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* Hero / Quick Status Banner */}
            <div className="bg-gradient-to-br from-slate-900 via-slate-900 to-slate-800 border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
              <div className="absolute top-0 right-0 -mt-8 -mr-8 w-48 h-48 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
              <div className="relative z-10 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
                <div>
                  <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-emerald-950/80 border border-emerald-800/60 text-emerald-400 text-xs font-semibold mb-3">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    <span>システム稼働中 - LightGBM EV Strategy</span>
                  </div>
                  <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                    PakaPaka AI 競馬投資シミュレーター
                  </h1>
                  <p className="mt-2 text-sm sm:text-base text-slate-400 max-w-2xl">
                    JRA競馬データをLightGBM機械学習モデルで分析し、オッズとの歪み（期待値 &gt; 1.0）を捉えて最適なケリー基準で疑似運用を行うプラットフォームです。
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  <button
                    onClick={handleGenerateSampleData}
                    disabled={isGeneratingSample}
                    className="flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition shadow-lg shadow-emerald-900/30 disabled:opacity-50"
                  >
                    <Database className={`w-4 h-4 ${isGeneratingSample ? 'animate-spin' : ''}`} />
                    <span>{isGeneratingSample ? '生成中...' : 'サンプルデータ生成'}</span>
                  </button>
                  <button
                    onClick={() => setActiveTab('races')}
                    className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium text-sm border border-slate-700 transition"
                  >
                    レース一覧へ
                  </button>
                </div>
              </div>

              {sampleDataStatus && (
                <div className="mt-4 p-3 rounded-lg bg-emerald-950/60 border border-emerald-800 text-emerald-300 text-xs flex items-center space-x-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>{sampleDataStatus}</span>
                </div>
              )}
            </div>

            {/* Quick Metrics Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow">
                <span className="text-xs text-slate-400 font-medium">ウォレット残高</span>
                <div className="mt-2 flex items-baseline justify-between">
                  <span className="text-2xl font-bold font-mono text-slate-100">
                    {(wallet?.current_points ?? 100000).toLocaleString()}
                  </span>
                  <span className="text-xs text-slate-400">pt</span>
                </div>
                <div className="mt-2 text-xs text-slate-400">
                  初期資本: {(wallet?.initial_points ?? 100000).toLocaleString()} pt
                </div>
              </div>

              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow">
                <span className="text-xs text-slate-400 font-medium">通算回収率 (ROI)</span>
                <div className="mt-2 flex items-baseline justify-between">
                  <span
                    className={`text-2xl font-bold font-mono ${
                      (wallet?.roi ?? 0) >= 100
                        ? 'text-emerald-400'
                        : (wallet?.roi ?? 0) > 0
                        ? 'text-amber-400'
                        : 'text-slate-400'
                    }`}
                  >
                    {wallet?.roi ? `${wallet.roi.toFixed(1)}%` : '0.0%'}
                  </span>
                  <span className="text-xs text-slate-400">
                    {wallet?.profit && wallet.profit >= 0
                      ? `+${wallet.profit.toLocaleString()} pt`
                      : `${(wallet?.profit ?? 0).toLocaleString()} pt`}
                  </span>
                </div>
                <div className="mt-2 text-xs text-slate-400">
                  総投資: {(wallet?.total_invested ?? 0).toLocaleString()} pt
                </div>
              </div>

              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow">
                <span className="text-xs text-slate-400 font-medium">シミュレーション勝率</span>
                <div className="mt-2 flex items-baseline justify-between">
                  <span className="text-2xl font-bold font-mono text-cyan-400">
                    {wallet?.win_rate ? `${wallet.win_rate.toFixed(1)}%` : '0.0%'}
                  </span>
                  <span className="text-xs text-slate-400">
                    {wallet?.won_bets ?? 0} / {wallet?.total_bets ?? 0} 的中
                  </span>
                </div>
                <div className="mt-2 text-xs text-slate-400">
                  最大ドローダウン: {((wallet?.max_drawdown ?? 0) * 100).toFixed(1)}%
                </div>
              </div>

              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow">
                <span className="text-xs text-slate-400 font-medium">アクティブAIモデル</span>
                <div className="mt-2 flex items-baseline justify-between">
                  <span className="text-lg font-bold font-mono text-indigo-400 truncate">
                    {activeModel?.model_version || '未学習'}
                  </span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      activeModel?.status === 'active'
                        ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                        : 'bg-amber-950 text-amber-400 border border-amber-800'
                    }`}
                  >
                    {activeModel?.status === 'active' ? 'Active' : 'Not Trained'}
                  </span>
                </div>
                <div className="mt-2 text-xs text-slate-400">
                  {activeModel?.roc_auc
                    ? `ROC-AUC: ${activeModel.roc_auc.toFixed(3)}`
                    : 'モデルを学習させてください'}
                </div>
              </div>
            </div>

            {/* Navigation Cards to Modules */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div
                onClick={() => setActiveTab('races')}
                className="bg-slate-900/80 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 rounded-xl p-5 cursor-pointer transition flex flex-col justify-between group"
              >
                <div>
                  <div className="w-10 h-10 rounded-lg bg-emerald-950/60 border border-emerald-800/40 flex items-center justify-center text-emerald-400 mb-3 group-hover:scale-110 transition">
                    <Trophy className="w-5 h-5" />
                  </div>
                  <h3 className="text-base font-semibold text-slate-100">レース一覧 ＆ AI予想</h3>
                  <p className="mt-1.5 text-xs text-slate-400 leading-relaxed">
                    出馬表、オッズ、リアルタイム着順結果、LightGBMによる各馬の勝率・複勝率・EV（期待値）評価を確認できます。
                  </p>
                </div>
                <div className="mt-4 text-xs font-semibold text-emerald-400 flex items-center space-x-1">
                  <span>レース一覧を開く</span>
                  <span>→</span>
                </div>
              </div>

              <div
                onClick={() => setActiveTab('simulation')}
                className="bg-slate-900/80 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 rounded-xl p-5 cursor-pointer transition flex flex-col justify-between group"
              >
                <div>
                  <div className="w-10 h-10 rounded-lg bg-cyan-950/60 border border-cyan-800/40 flex items-center justify-center text-cyan-400 mb-3 group-hover:scale-110 transition">
                    <PlayCircle className="w-5 h-5" />
                  </div>
                  <h3 className="text-base font-semibold text-slate-100">リアルタイム運用 (Forward)</h3>
                  <p className="mt-1.5 text-xs text-slate-400 leading-relaxed">
                    未確定レースへの自動買い目算出・仮想ベット実行、およびレース確定後の自動清算・ウォレット収支を管理します。
                  </p>
                </div>
                <div className="mt-4 text-xs font-semibold text-cyan-400 flex items-center space-x-1">
                  <span>フォワード運用を開く</span>
                  <span>→</span>
                </div>
              </div>

              <div
                onClick={() => setActiveTab('backtest')}
                className="bg-slate-900/80 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 rounded-xl p-5 cursor-pointer transition flex flex-col justify-between group"
              >
                <div>
                  <div className="w-10 h-10 rounded-lg bg-indigo-950/60 border border-indigo-800/40 flex items-center justify-center text-indigo-400 mb-3 group-hover:scale-110 transition">
                    <BarChart3 className="w-5 h-5" />
                  </div>
                  <h3 className="text-base font-semibold text-slate-100">バックテスト・スタジオ</h3>
                  <p className="mt-1.5 text-xs text-slate-400 leading-relaxed">
                    過去レースデータを用いて期待値閾値・券種・ケリー基準などの投資戦略をシミュレーションし、資産推移曲線を可視化します。
                  </p>
                </div>
                <div className="mt-4 text-xs font-semibold text-indigo-400 flex items-center space-x-1">
                  <span>バックテストを開く</span>
                  <span>→</span>
                </div>
              </div>

              <div
                onClick={() => setActiveTab('models')}
                className="bg-slate-900/80 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 rounded-xl p-5 cursor-pointer transition flex flex-col justify-between group"
              >
                <div>
                  <div className="w-10 h-10 rounded-lg bg-purple-950/60 border border-purple-800/40 flex items-center justify-center text-purple-400 mb-3 group-hover:scale-110 transition">
                    <BrainCircuit className="w-5 h-5" />
                  </div>
                  <h3 className="text-base font-semibold text-slate-100">AIモデル管理 (Model Studio)</h3>
                  <p className="mt-1.5 text-xs text-slate-400 leading-relaxed">
                    LightGBMモデルの新規学習実行、ROC-AUC・LogLossスコア検証、特徴量重要度（Feature Importance）分析を行います。
                  </p>
                </div>
                <div className="mt-4 text-xs font-semibold text-purple-400 flex items-center space-x-1">
                  <span>モデル管理を開く</span>
                  <span>→</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'races' && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center space-x-3">
                <Trophy className="w-6 h-6 text-emerald-400" />
                <h2 className="text-xl font-bold text-slate-100">レース一覧 ＆ AI予想ビュー</h2>
              </div>
              <span className="text-xs px-3 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                Task 8 Preview
              </span>
            </div>
            <p className="mt-4 text-sm text-slate-400">
              このタブでは、確定済みおよび発走予定のレース一覧の確認、オッズ・出馬表、LightGBMモデルによる予想マーク（◎, ◯, ▲, ☆）や期待値（EV）の詳細表示を提供します。
            </p>
          </div>
        )}

        {activeTab === 'simulation' && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center space-x-3">
                <PlayCircle className="w-6 h-6 text-cyan-400" />
                <h2 className="text-xl font-bold text-slate-100">リアルタイム運用 (Forward Simulation)</h2>
              </div>
              <span className="text-xs px-3 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                Task 10 Preview
              </span>
            </div>
            <p className="mt-4 text-sm text-slate-400">
              未確定レースへの自動買い目生成・仮想ベット購入、レース結果確定後の自動清算・ウォレット残高更新、購入履歴管理を提供します。
            </p>
          </div>
        )}

        {activeTab === 'backtest' && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center space-x-3">
                <BarChart3 className="w-6 h-6 text-indigo-400" />
                <h2 className="text-xl font-bold text-slate-100">バックテスト・スタジオ (Backtest Studio)</h2>
              </div>
              <span className="text-xs px-3 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                Task 9 Preview
              </span>
            </div>
            <p className="mt-4 text-sm text-slate-400">
              期間や最小期待値（Min EV）、ケリー基準パラメータ、券種を指定して過去レースを一括検証し、資産推移チャート（Equity Curve）やドローダウンを可視化します。
            </p>
          </div>
        )}

        {activeTab === 'models' && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center space-x-3">
                <BrainCircuit className="w-6 h-6 text-purple-400" />
                <h2 className="text-xl font-bold text-slate-100">AIモデル管理 (Model Studio)</h2>
              </div>
              <span className="text-xs px-3 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                Task 11 Preview
              </span>
            </div>
            <p className="mt-4 text-sm text-slate-400">
              蓄積された過去データをもとにLightGBMモデルの再学習を実行し、ROC-AUC、Log-Loss、各特徴量の重要度グラフをリアルタイムに確認できます。
            </p>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-950 py-4">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-400">
          <div className="flex items-center space-x-2">
            <span>🏇 PakaPaka Horse Racing AI Platform</span>
            <span>•</span>
            <span>Version 1.0.0</span>
          </div>
          <div className="mt-2 sm:mt-0 text-slate-400">
            Next-Gen Quantitative Horse Racing System
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
