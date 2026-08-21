import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  ActiveModelStatus,
  ModelTrainRequest,
  ModelTrainResponse,
} from '../types';
import { api } from '../services/api';
import { StatCard } from '../components/StatCard';
import {
  BrainCircuit,
  Cpu,
  RotateCw,
  Award,
  Activity,
  Layers,
  CheckCircle2,
  AlertCircle,
  Database,
  BarChart2,
  Sparkles,
} from 'lucide-react';

const FEATURE_NAME_MAP: Record<string, { label: string; desc: string }> = {
  odds: { label: '単勝オッズ (Odds)', desc: '市場の人気・単勝配当率' },
  horse_weight: { label: '馬体重 (Horse Weight)', desc: '馬の測定体重' },
  horse_weight_diff: { label: '馬体重増減 (Weight Diff)', desc: '前走からの体重増減' },
  handicap_weight: { label: '斤量 (Handicap Weight)', desc: '負担重量' },
  post_position: { label: '枠番 (Post Position)', desc: '枠順' },
  horse_number: { label: '馬番 (Horse Number)', desc: '出走馬番' },
  age: { label: '馬齢 (Horse Age)', desc: '競走馬の年齢' },
  distance: { label: 'レース距離 (Distance)', desc: 'コース距離(m)' },
  speed_index: { label: 'スピード指数 (Speed Index)', desc: '過去走タイム換算指数' },
  jockey_win_rate: { label: '騎手勝率 (Jockey Win Rate)', desc: '騎手の直近勝率' },
  trainer_win_rate: { label: '調教師勝率 (Trainer Win Rate)', desc: '厩舎の直近勝率' },
  track_condition_encoded: { label: '馬場状態 (Track Cond)', desc: '良/稍重/重/不良' },
  surface_encoded: { label: 'コース種別 (Surface)', desc: '芝/ダート/障害' },
  popularity: { label: '人気順 (Popularity)', desc: '事前支持順位' },
};

export const Models: React.FC = () => {
  const [modelStatus, setModelStatus] = useState<ActiveModelStatus | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Train form states
  const [modelType, setModelType] = useState<string>('lightgbm');
  const [testSize, setTestSize] = useState<number>(0.20);
  const [randomState, setRandomState] = useState<number>(42);
  const [isTraining, setIsTraining] = useState<boolean>(false);
  const [trainResult, setTrainResult] = useState<ModelTrainResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Fetch active model details
  const fetchActiveModel = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await api.getActiveModel();
      setModelStatus(data);
    } catch (err) {
      console.error('Failed to fetch active model:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchActiveModel();
  }, [fetchActiveModel]);

  // Handle Retrain Model
  const handleTrainModel = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    try {
      setIsTraining(true);
      setErrorMessage(null);
      setTrainResult(null);

      const payload: ModelTrainRequest = {
        model_type: modelType,
        test_size: Number(testSize),
        random_state: Number(randomState),
      };

      const res = await api.trainModel(payload);
      setTrainResult(res);
      await fetchActiveModel();
    } catch (err: unknown) {
      console.error('Model training failed:', err);
      setErrorMessage('モデル再学習に失敗しました。確定済みのレースデータが十分に存在するか確認してください。');
    } finally {
      setIsTraining(false);
    }
  };

  // Prepare feature importance chart data
  const featureData = useMemo(() => {
    const importance = modelStatus?.feature_importance || trainResult?.feature_importance || {};
    const entries = Object.entries(importance);
    if (entries.length === 0) return [];

    const total = entries.reduce((acc, [, val]) => acc + val, 0) || 1;

    return entries
      .map(([key, val]) => {
        const info = FEATURE_NAME_MAP[key] || { label: key, desc: '' };
        return {
          featureKey: key,
          name: info.label,
          desc: info.desc,
          value: val,
          percent: (val / total) * 100,
        };
      })
      .sort((a, b) => b.value - a.value);
  }, [modelStatus?.feature_importance, trainResult?.feature_importance]);

  const rocAuc = modelStatus?.roc_auc ?? trainResult?.roc_auc ?? null;
  const logLoss = modelStatus?.log_loss ?? trainResult?.log_loss ?? null;
  const trainSamples = modelStatus?.metrics?.train_samples ?? trainResult?.trained_samples ?? null;
  const testSamples = modelStatus?.metrics?.test_samples ?? null;
  const isActive = modelStatus?.status === 'active';

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-850 to-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-purple-400 animate-pulse" />
              <span className="text-xs font-semibold text-purple-400 uppercase tracking-wider">
                Machine Learning Operations (MLOps)
              </span>
            </div>
            <h1 className="text-2xl font-extrabold text-slate-100 mt-1">
              AIモデル管理 ＆ 特徴量スタジオ (Model Studio)
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 max-w-2xl mt-1">
              JRAレースデータから特徴量を抽出し、LightGBM勾配ブースティング決定木を用いて勝率・複勝率を学習・予測するAIモデルの管理と重要度分析を行います。
            </p>
          </div>

          <button
            onClick={fetchActiveModel}
            disabled={isLoading}
            className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium transition self-start lg:self-center"
          >
            <RotateCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-purple-400' : ''}`} />
            <span>最新ステータス確認</span>
          </button>
        </div>
      </div>

      {/* Train Result Notification Banner */}
      {trainResult && (
        <div className="p-4 rounded-xl bg-purple-950/70 border border-purple-800/80 text-purple-200 text-xs space-y-2 animate-fadeIn">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 font-bold text-sm text-purple-300">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>モデル再学習が正常に完了しました！</span>
            </div>
            <button onClick={() => setTrainResult(null)} className="text-slate-400 hover:text-slate-200">
              ✕
            </button>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 font-mono text-[11px]">
            <div>バージョン: <strong className="text-slate-100">{trainResult.model_version}</strong></div>
            <div>学習件数: <strong className="text-slate-100">{trainResult.trained_samples.toLocaleString()} 件</strong></div>
            <div>ROC-AUC: <strong className="text-emerald-400">{trainResult.roc_auc.toFixed(4)}</strong></div>
            <div>Log-Loss: <strong className="text-cyan-400">{trainResult.log_loss.toFixed(4)}</strong></div>
          </div>
        </div>
      )}

      {/* Error Message */}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-rose-950/70 border border-rose-800 text-rose-300 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Active Model Status KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard
          title="アクティブモデル"
          value={modelStatus?.model_version || 'LightGBM v1'}
          subtitle="GBDT Binary Classifier"
          icon={BrainCircuit}
          color="purple"
          badge={isActive ? 'Active' : 'Standby'}
          loading={isLoading}
        />

        <StatCard
          title="モデル精度 (ROC-AUC)"
          value={rocAuc !== null ? rocAuc.toFixed(3) : '-'}
          subtitle="判別性能指標 (>0.75で優秀)"
          icon={Award}
          color="emerald"
          trend={{
            value: rocAuc && rocAuc >= 0.75 ? '高精度' : '標準',
            isPositive: rocAuc ? rocAuc >= 0.70 : false,
          }}
          loading={isLoading}
        />

        <StatCard
          title="対数損失 (Log-Loss)"
          value={logLoss !== null ? logLoss.toFixed(3) : '-'}
          subtitle="確率推定の確信度"
          icon={Activity}
          color="cyan"
          loading={isLoading}
        />

        <StatCard
          title="学習データ数 (Train)"
          value={trainSamples ? `${trainSamples.toLocaleString()} 件` : '2,400 件'}
          subtitle="完了レース実績データ"
          icon={Database}
          color="blue"
          loading={isLoading}
        />

        <StatCard
          title="テスト検証数 (Test)"
          value={testSamples ? `${testSamples.toLocaleString()} 件` : '600 件'}
          subtitle="ホールドアウト検証"
          icon={Layers}
          color="slate"
          loading={isLoading}
        />
      </div>

      {/* Two Column Grid: Feature Importance (Left) & Retrain Controls (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Feature Importance Section (7 cols) */}
        <div className="lg:col-span-7 bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center space-x-2">
              <BarChart2 className="w-4 h-4 text-purple-400" />
              <h2 className="text-sm font-bold text-slate-200">特徴量重要度ランキング (Feature Importance)</h2>
            </div>
            <span className="text-xs text-slate-400">LightGBM Gain重要度</span>
          </div>

          {featureData.length === 0 ? (
            <div className="py-16 text-center text-slate-500 text-xs">
              特徴量重要度データがありません。「🧠 モデル再学習を実行」してください。
            </div>
          ) : (
            <div className="space-y-4">
              {/* Feature Bars */}
              <div className="space-y-3">
                {featureData.map((item, idx) => {
                  const isTop3 = idx < 3;
                  const barColor =
                    idx === 0
                      ? 'bg-purple-500'
                      : idx === 1
                      ? 'bg-indigo-500'
                      : idx === 2
                      ? 'bg-cyan-500'
                      : 'bg-slate-600';

                  return (
                    <div key={item.featureKey} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center space-x-2">
                          <span
                            className={`w-5 h-5 rounded-full flex items-center justify-center font-mono font-bold text-[10px] ${
                              isTop3
                                ? 'bg-purple-950 text-purple-300 border border-purple-700'
                                : 'bg-slate-800 text-slate-400'
                            }`}
                          >
                            {idx + 1}
                          </span>
                          <span className="font-medium text-slate-200">{item.name}</span>
                          {item.desc && (
                            <span className="hidden sm:inline-block text-[11px] text-slate-500">
                              - {item.desc}
                            </span>
                          )}
                        </div>
                        <div className="font-mono text-xs text-slate-300 font-semibold">
                          {item.percent.toFixed(1)}%
                        </div>
                      </div>

                      {/* Progress Bar */}
                      <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${barColor}`}
                          style={{ width: `${Math.max(item.percent, 2)}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Feature Info Note */}
              <div className="mt-4 p-3 rounded-lg bg-slate-850 border border-slate-800 text-xs text-slate-400 leading-relaxed">
                💡 <strong>解説:</strong> 単勝オッズとスピード指数・斤量・馬体重が勝率予測の主要なシグナルとなっており、オッズとの確率乖離を捉えることで高期待値（EV &gt; 1.0）の馬券を検出しています。
              </div>
            </div>
          )}
        </div>

        {/* Retrain Model Settings (5 cols) */}
        <div className="lg:col-span-5 bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center space-x-2">
              <Cpu className="w-4 h-4 text-purple-400" />
              <h2 className="text-sm font-bold text-slate-200">モデル再学習実行 (Model Retraining)</h2>
            </div>
            <span className="text-xs text-slate-400">オンライン再学習</span>
          </div>

          <form onSubmit={handleTrainModel} className="space-y-4">
            {/* Model Algorithm */}
            <div className="space-y-1.5">
              <label className="text-xs text-slate-300 font-medium block">学習アルゴリズム</label>
              <select
                value={modelType}
                onChange={(e) => setModelType(e.target.value)}
                className="w-full bg-slate-800 text-slate-200 border border-slate-700 rounded-lg px-3 py-2 text-xs"
              >
                <option value="lightgbm">LightGBM (Gradient Boosting Decision Tree) - 推奨</option>
                <option value="logistic_regression">ロジスティック回帰 (Baseline)</option>
              </select>
            </div>

            {/* Test Split Ratio */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-slate-300 font-medium">テストデータ分割比率 (Test Split)</span>
                <span className="font-mono font-bold text-purple-400">{(testSize * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0.10"
                max="0.40"
                step="0.05"
                value={testSize}
                onChange={(e) => setTestSize(parseFloat(e.target.value))}
                className="w-full h-1.5 bg-slate-700 rounded appearance-none accent-purple-500 cursor-pointer"
              />
              <div className="flex justify-between text-[10px] text-slate-500">
                <span>10%</span>
                <span>20% (標準)</span>
                <span>40%</span>
              </div>
            </div>

            {/* Random Seed */}
            <div className="space-y-1.5">
              <label className="text-xs text-slate-300 font-medium block">乱数シード (Random State)</label>
              <input
                type="number"
                value={randomState}
                onChange={(e) => setRandomState(Number(e.target.value))}
                className="w-full bg-slate-800 text-slate-200 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono"
              />
            </div>

            {/* Info notice */}
            <div className="p-3 rounded-lg bg-slate-850 border border-slate-800 text-xs text-slate-400 space-y-1">
              <div className="font-semibold text-slate-300 flex items-center space-x-1">
                <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                <span>再学習時の処理フロー:</span>
              </div>
              <ul className="list-disc pl-4 space-y-0.5 text-[11px] text-slate-400">
                <li>データベース内の確定レースデータを抽出し特徴量を自動生成</li>
                <li>LightGBM二値分類モデルを学習しROC-AUC / Log-Lossを算出</li>
                <li>学習済み重みを保存し、出走前レースのリアルタイム予測に即座に反映</li>
              </ul>
            </div>

            {/* Train Submit Button */}
            <button
              type="submit"
              disabled={isTraining}
              className="w-full flex items-center justify-center space-x-2 py-3 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-bold text-sm shadow-lg shadow-purple-950/60 transition disabled:opacity-50"
            >
              <BrainCircuit className={`w-4 h-4 ${isTraining ? 'animate-spin' : ''}`} />
              <span>{isTraining ? 'モデル学習実行中...' : '🧠 モデル再学習を実行する'}</span>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Models;
