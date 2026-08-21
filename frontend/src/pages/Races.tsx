import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Race, Prediction, Payout } from '../types';
import { api } from '../services/api';
import { RaceCard } from '../components/RaceCard';
import { OddsTable } from '../components/OddsTable';
import { RecommendationBadge, EVBadge } from '../components/PredictionBadge';
import {
  Trophy,
  Calendar,
  Search,
  Sparkles,
  RefreshCw,
  Coins,
  Filter,
  CheckCircle2,
  AlertCircle,
  Database,
} from 'lucide-react';

const POPULAR_COURSES = ['すべて', '東京', '中山', '京都', '阪神', '中京', '小倉', '新潟', '福島', '札幌', '函館'];

export const Races: React.FC = () => {
  const [races, setRaces] = useState<Race[]>([]);
  const [selectedRaceId, setSelectedRaceId] = useState<string | null>(null);
  const [selectedRaceDetail, setSelectedRaceDetail] = useState<Race | null>(null);
  const [predictions, setPredictions] = useState<Prediction[]>([]);

  // Filter States
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [selectedCourse, setSelectedCourse] = useState<string>('すべて');
  const [statusFilter, setStatusFilter] = useState<'all' | 'scheduled' | 'finished'>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Loading States
  const [isLoadingRaces, setIsLoadingRaces] = useState<boolean>(false);
  const [isLoadingDetail, setIsLoadingDetail] = useState<boolean>(false);
  const [isPredicting, setIsPredicting] = useState<boolean>(false);
  const [isGeneratingSample, setIsGeneratingSample] = useState<boolean>(false);
  const [feedbackMessage, setFeedbackMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Fetch races list
  const fetchRaces = useCallback(async () => {
    try {
      setIsLoadingRaces(true);
      const params: { date?: string; race_course?: string; status?: string } = {};
      if (selectedDate) params.date = selectedDate;
      if (selectedCourse !== 'すべて') params.race_course = selectedCourse;
      if (statusFilter !== 'all') params.status = statusFilter;

      const data = await api.getRaces(params);
      setRaces(data);

      // Auto select first race if current selection is not in list or none selected
      if (data.length > 0) {
        if (!selectedRaceId || !data.some((r) => r.id === selectedRaceId)) {
          setSelectedRaceId(data[0].id);
        }
      } else {
        setSelectedRaceId(null);
        setSelectedRaceDetail(null);
        setPredictions([]);
      }
    } catch (err) {
      console.error('Failed to fetch races:', err);
    } finally {
      setIsLoadingRaces(false);
    }
  }, [selectedDate, selectedCourse, statusFilter, selectedRaceId]);

  // Load detailed race info & predictions when selectedRaceId changes
  const loadRaceDetail = useCallback(async (raceId: string) => {
    try {
      setIsLoadingDetail(true);
      const detail = await api.getRaceDetail(raceId);
      setSelectedRaceDetail(detail);

      // Fetch predictions
      try {
        const preds = await api.getPredictions(raceId);
        setPredictions(preds);
      } catch (predErr) {
        console.warn('Predictions not yet generated for race:', raceId, predErr);
        setPredictions(detail.predictions || []);
      }
    } catch (err) {
      console.error('Failed to load race detail:', err);
    } finally {
      setIsLoadingDetail(false);
    }
  }, []);

  useEffect(() => {
    fetchRaces();
  }, [fetchRaces]);

  useEffect(() => {
    if (selectedRaceId) {
      loadRaceDetail(selectedRaceId);
    }
  }, [selectedRaceId, loadRaceDetail]);

  // Run or Refresh AI Predictions
  const handleRunPredictions = async () => {
    if (!selectedRaceId) return;
    try {
      setIsPredicting(true);
      setFeedbackMessage(null);
      const preds = await api.getPredictions(selectedRaceId);
      setPredictions(preds);
      setFeedbackMessage({
        type: 'success',
        text: `AI予想を更新しました（全${preds.length}頭の期待値を算出完了）`,
      });
    } catch (err: unknown) {
      console.error('Prediction failed:', err);
      setFeedbackMessage({
        type: 'error',
        text: 'AI予想の計算に失敗しました。アクティブなモデルが存在するか確認してください。',
      });
    } finally {
      setIsPredicting(false);
    }
  };

  // Generate Sample Data helper
  const handleGenerateSampleData = async () => {
    try {
      setIsGeneratingSample(true);
      const res = await api.generateSampleData(30, 6, '2024-01-06');
      setFeedbackMessage({
        type: 'success',
        text: `サンプルデータ ${res.generated_races} 件の生成が完了しました！`,
      });
      fetchRaces();
    } catch (err) {
      console.error('Sample generation failed:', err);
      setFeedbackMessage({
        type: 'error',
        text: 'サンプルデータの生成に失敗しました。',
      });
    } finally {
      setIsGeneratingSample(false);
    }
  };

  // Filtered races for the list
  const filteredRaces = useMemo(() => {
    return races.filter((race) => {
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const matchesName = race.race_name.toLowerCase().includes(q);
        const matchesCourse = race.race_course.toLowerCase().includes(q);
        const matchesEntry = race.entries?.some(
          (e) =>
            e.horse_name.toLowerCase().includes(q) ||
            e.jockey_name.toLowerCase().includes(q)
        );
        if (!matchesName && !matchesCourse && !matchesEntry) {
          return false;
        }
      }
      return true;
    });
  }, [races, searchQuery]);

  // Top AI Picks breakdown for callout card
  const topAIPicks = useMemo(() => {
    if (!predictions || predictions.length === 0 || !selectedRaceDetail?.entries) {
      return [];
    }

    const marksOrder: Record<string, number> = { '◎': 1, '◯': 2, '▲': 3, '☆': 4 };
    return [...predictions]
      .filter((p) => marksOrder[p.recommendation_mark])
      .sort((a, b) => (marksOrder[a.recommendation_mark] || 99) - (marksOrder[b.recommendation_mark] || 99))
      .map((pred) => {
        const entry = selectedRaceDetail.entries?.find((e) => e.horse_number === pred.horse_number);
        return {
          ...pred,
          horse_name: entry?.horse_name || `${pred.horse_number}番`,
          jockey_name: entry?.jockey_name || '',
          odds: entry?.odds || 0,
        };
      });
  }, [predictions, selectedRaceDetail]);

  // Organize payouts by bet type
  const groupedPayouts = useMemo(() => {
    if (!selectedRaceDetail?.payouts) return {};
    const groups: Record<string, Payout[]> = {};
    selectedRaceDetail.payouts.forEach((p) => {
      if (!groups[p.bet_type]) {
        groups[p.bet_type] = [];
      }
      groups[p.bet_type].push(p);
    });
    return groups;
  }, [selectedRaceDetail]);

  return (
    <div className="space-y-6">
      {/* Top Filter & Toolbar Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-5 shadow-lg">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          {/* Search & Date Input */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative min-w-[220px]">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="レース名・馬名・騎手で検索..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition"
              />
            </div>

            <div className="flex items-center space-x-2 bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5">
              <Calendar className="w-4 h-4 text-slate-400" />
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="bg-transparent text-xs text-slate-200 focus:outline-none"
              />
              {selectedDate && (
                <button
                  onClick={() => setSelectedDate('')}
                  className="text-slate-500 hover:text-slate-300 text-xs px-1"
                  title="日付クリア"
                >
                  ✕
                </button>
              )}
            </div>

            {/* Status Filter Buttons */}
            <div className="flex items-center rounded-xl bg-slate-950 p-1 border border-slate-800">
              <button
                onClick={() => setStatusFilter('all')}
                className={`px-3 py-1 text-xs rounded-lg font-medium transition ${
                  statusFilter === 'all'
                    ? 'bg-slate-800 text-slate-100 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                すべて
              </button>
              <button
                onClick={() => setStatusFilter('scheduled')}
                className={`px-3 py-1 text-xs rounded-lg font-medium transition ${
                  statusFilter === 'scheduled'
                    ? 'bg-emerald-950 text-emerald-300 border border-emerald-800 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                出走前
              </button>
              <button
                onClick={() => setStatusFilter('finished')}
                className={`px-3 py-1 text-xs rounded-lg font-medium transition ${
                  statusFilter === 'finished'
                    ? 'bg-slate-800 text-slate-200 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                確定
              </button>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="flex items-center space-x-2">
            <button
              onClick={() => fetchRaces()}
              disabled={isLoadingRaces}
              className="flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoadingRaces ? 'animate-spin text-emerald-400' : ''}`} />
              <span>更新</span>
            </button>

            {races.length === 0 && (
              <button
                onClick={handleGenerateSampleData}
                disabled={isGeneratingSample}
                className="flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition shadow disabled:opacity-50"
              >
                <Database className="w-3.5 h-3.5" />
                <span>{isGeneratingSample ? '生成中...' : 'サンプル生成'}</span>
              </button>
            )}
          </div>
        </div>

        {/* Course Filter Tabs */}
        <div className="mt-3 pt-3 border-t border-slate-800 flex items-center space-x-1 overflow-x-auto pb-1 text-xs">
          <span className="text-slate-500 flex items-center mr-2 shrink-0">
            <Filter className="w-3 h-3 mr-1" />
            競馬場:
          </span>
          {POPULAR_COURSES.map((c) => (
            <button
              key={c}
              onClick={() => setSelectedCourse(c)}
              className={`px-2.5 py-1 rounded-lg shrink-0 transition ${
                selectedCourse === c
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-semibold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      {/* Feedback Alert */}
      {feedbackMessage && (
        <div
          className={`p-4 rounded-xl border flex items-center space-x-3 text-xs ${
            feedbackMessage.type === 'success'
              ? 'bg-emerald-950/70 border-emerald-800 text-emerald-300'
              : 'bg-rose-950/70 border-rose-800 text-rose-300'
          }`}
        >
          {feedbackMessage.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          )}
          <span>{feedbackMessage.text}</span>
          <button
            onClick={() => setFeedbackMessage(null)}
            className="ml-auto text-slate-400 hover:text-slate-200"
          >
            ✕
          </button>
        </div>
      )}

      {/* Main Grid: Left Race List, Right Race Details */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left: Races Sidebar List (4 cols) */}
        <div className="lg:col-span-4 space-y-3">
          <div className="flex items-center justify-between px-1">
            <h2 className="text-sm font-bold text-slate-200 flex items-center space-x-1.5">
              <Trophy className="w-4 h-4 text-emerald-400" />
              <span>レース一覧 ({filteredRaces.length}件)</span>
            </h2>
            {isLoadingRaces && (
              <span className="text-xs text-slate-500 animate-pulse">読み込み中...</span>
            )}
          </div>

          <div className="space-y-2.5 max-h-[780px] overflow-y-auto pr-1">
            {filteredRaces.length > 0 ? (
              filteredRaces.map((race) => (
                <RaceCard
                  key={race.id}
                  race={race}
                  isSelected={race.id === selectedRaceId}
                  onClick={(r) => setSelectedRaceId(r.id)}
                />
              ))
            ) : (
              <div className="p-8 text-center bg-slate-900/60 rounded-2xl border border-slate-800 text-slate-400">
                <p className="text-sm">該当するレースが見つかりません。</p>
                <button
                  onClick={handleGenerateSampleData}
                  disabled={isGeneratingSample}
                  className="mt-4 inline-flex items-center space-x-2 px-3 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition"
                >
                  <Database className="w-3.5 h-3.5" />
                  <span>サンプルレースを生成する</span>
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Right: Selected Race Detail & AI View (8 cols) */}
        <div className="lg:col-span-8 space-y-6">
          {selectedRaceDetail ? (
            <>
              {/* Selected Race Hero Header Card */}
              <div className="bg-gradient-to-br from-slate-900 via-slate-900 to-slate-850 border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
                  <div>
                    <div className="flex items-center space-x-2 mb-1">
                      <span className="px-2.5 py-0.5 rounded-md bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-xs font-mono font-bold">
                        {selectedRaceDetail.race_number}R
                      </span>
                      <span className="text-sm font-bold text-slate-300">
                        {selectedRaceDetail.race_course} 競馬場
                      </span>
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-semibold border ${
                          selectedRaceDetail.status === 'finished'
                            ? 'bg-slate-800 text-slate-300 border-slate-700'
                            : 'bg-emerald-950 text-emerald-400 border-emerald-800 animate-pulse'
                        }`}
                      >
                        {selectedRaceDetail.status === 'finished' ? 'レース確定' : '出走前 (発走予定)'}
                      </span>
                    </div>

                    <div className="flex items-center space-x-3">
                      <h1 className="text-2xl font-extrabold text-white tracking-tight">
                        {selectedRaceDetail.race_name}
                      </h1>
                      {isLoadingDetail && (
                        <RefreshCw className="w-4 h-4 animate-spin text-emerald-400" />
                      )}
                    </div>
                  </div>

                  {/* AI Prediction Trigger Button */}
                  <button
                    onClick={handleRunPredictions}
                    disabled={isPredicting}
                    className="flex items-center justify-center space-x-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold shadow-lg shadow-emerald-950/50 border border-emerald-400/30 transition disabled:opacity-50"
                  >
                    <Sparkles className={`w-4 h-4 ${isPredicting ? 'animate-spin' : ''}`} />
                    <span>{isPredicting ? 'AI推論中...' : 'AI予想を実行 / 更新'}</span>
                  </button>
                </div>

                {/* Race Specs Info Grid */}
                <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/80">
                    <span className="text-slate-400 block text-[11px]">コース / 距離</span>
                    <span className="font-semibold text-slate-200 mt-0.5 block">
                      {selectedRaceDetail.surface} {selectedRaceDetail.distance}m
                    </span>
                  </div>

                  <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/80">
                    <span className="text-slate-400 block text-[11px]">馬場状態 / 天候</span>
                    <span className="font-semibold text-slate-200 mt-0.5 block">
                      {selectedRaceDetail.track_condition} / {selectedRaceDetail.weather}
                    </span>
                  </div>

                  <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/80">
                    <span className="text-slate-400 block text-[11px]">開催日</span>
                    <span className="font-semibold text-slate-200 mt-0.5 block">
                      {selectedRaceDetail.date}
                    </span>
                  </div>

                  <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/80">
                    <span className="text-slate-400 block text-[11px]">出走頭数</span>
                    <span className="font-semibold text-slate-200 mt-0.5 block">
                      {selectedRaceDetail.entries?.length ?? 0} 頭立
                    </span>
                  </div>
                </div>
              </div>

              {/* AI Top Picks Summary Callout */}
              {topAIPicks.length > 0 && (
                <div className="bg-slate-900 border border-emerald-900/40 rounded-2xl p-5 shadow-lg relative overflow-hidden">
                  <div className="flex items-center space-x-2 pb-3 border-b border-slate-800/80">
                    <Sparkles className="w-4 h-4 text-emerald-400" />
                    <h3 className="text-sm font-bold text-slate-100">
                      LightGBM AI 推奨マーク ＆ 期待値トップピック
                    </h3>
                  </div>

                  <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                    {topAIPicks.map((pick) => (
                      <div
                        key={pick.horse_number}
                        className="bg-slate-950/70 border border-slate-800 rounded-xl p-3 flex flex-col justify-between"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-1.5">
                            <RecommendationBadge mark={pick.recommendation_mark} size="sm" />
                            <span className="font-mono font-bold text-slate-100 text-sm">
                              {pick.horse_number}番
                            </span>
                          </div>
                          <EVBadge ev={pick.expected_value} size="sm" />
                        </div>

                        <div className="mt-2">
                          <div className="font-semibold text-slate-200 text-xs truncate">
                            {pick.horse_name}
                          </div>
                          <div className="text-[11px] text-slate-400 flex items-center justify-between mt-1">
                            <span>単勝 {pick.odds}倍</span>
                            <span className="text-emerald-400 font-mono">
                              勝率 {(pick.win_prob * 100).toFixed(1)}%
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Official Payouts Card (Finished Races Only) */}
              {selectedRaceDetail.status === 'finished' &&
                selectedRaceDetail.payouts &&
                selectedRaceDetail.payouts.length > 0 && (
                  <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg">
                    <div className="flex items-center space-x-2 pb-3 border-b border-slate-800">
                      <Coins className="w-4 h-4 text-amber-400" />
                      <h3 className="text-sm font-bold text-slate-100">
                        確定払戻金 (Official Payouts)
                      </h3>
                    </div>

                    <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
                      {Object.entries(groupedPayouts).map(([betType, payoutList]) => (
                        <div
                          key={betType}
                          className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-3"
                        >
                          <span className="text-[11px] font-bold text-amber-400 uppercase tracking-wider block mb-1.5">
                            {betType}
                          </span>
                          <div className="space-y-1">
                            {payoutList.map((p, idx) => (
                              <div
                                key={idx}
                                className="flex items-center justify-between text-xs"
                              >
                                <span className="font-mono font-medium text-slate-300">
                                  {p.combination}
                                </span>
                                <span className="font-mono font-bold text-amber-300">
                                  {p.payout.toLocaleString()} 円
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              {/* Full Entries & Prediction OddsTable */}
              <div className="space-y-2">
                <div className="flex items-center justify-between px-1">
                  <h3 className="text-sm font-bold text-slate-200">
                    出走表 ＆ AI予測詳細
                  </h3>
                  <span className="text-xs text-slate-400">
                    列ヘッダーをクリックして並び替え
                  </span>
                </div>

                <OddsTable
                  entries={selectedRaceDetail.entries || []}
                  predictions={predictions}
                  isFinished={selectedRaceDetail.status === 'finished'}
                />
              </div>
            </>
          ) : (
            <div className="p-12 text-center bg-slate-900 border border-slate-800 rounded-2xl text-slate-400">
              <Trophy className="w-12 h-12 text-slate-600 mx-auto mb-3" />
              <p className="text-base font-semibold text-slate-300">レースを選択してください</p>
              <p className="text-xs text-slate-500 mt-1">
                左側のレース一覧から詳細を確認したいレースを選択してください。
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Races;
