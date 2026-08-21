import React, { useState, useMemo } from 'react';
import { RaceEntry, Prediction } from '../types';
import { RecommendationBadge, EVBadge, ProbBadge } from './PredictionBadge';
import { ArrowUpDown } from 'lucide-react';

interface OddsTableProps {
  entries: RaceEntry[];
  predictions?: Prediction[];
  isFinished?: boolean;
}

type SortField =
  | 'horse_number'
  | 'odds'
  | 'popularity'
  | 'win_prob'
  | 'place_prob'
  | 'expected_value'
  | 'finish_position';

type SortOrder = 'asc' | 'desc';

// JRA 8 Frame colors
export const getFrameColorClass = (postPosition: number): string => {
  switch (postPosition) {
    case 1:
      return 'bg-white text-slate-900 border border-slate-300 font-extrabold';
    case 2:
      return 'bg-slate-950 text-white border border-slate-600 font-extrabold';
    case 3:
      return 'bg-red-600 text-white font-extrabold shadow-sm shadow-red-950';
    case 4:
      return 'bg-blue-600 text-white font-extrabold shadow-sm shadow-blue-950';
    case 5:
      return 'bg-yellow-400 text-slate-950 font-extrabold shadow-sm shadow-yellow-950';
    case 6:
      return 'bg-emerald-600 text-white font-extrabold shadow-sm shadow-emerald-950';
    case 7:
      return 'bg-orange-500 text-white font-extrabold shadow-sm shadow-orange-950';
    case 8:
      return 'bg-pink-500 text-white font-extrabold shadow-sm shadow-pink-950';
    default:
      return 'bg-slate-800 text-slate-300 border border-slate-700 font-bold';
  }
};

export const OddsTable: React.FC<OddsTableProps> = ({
  entries,
  predictions = [],
  isFinished = false,
}) => {
  const [sortField, setSortField] = useState<SortField>('horse_number');
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');

  // Build prediction lookup map by horse_number
  const predictionMap = useMemo(() => {
    const map = new Map<number, Prediction>();
    predictions.forEach((p) => {
      map.set(p.horse_number, p);
    });
    return map;
  }, [predictions]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      // Default desc for probabilities and EV, asc for numbers/positions
      if (['win_prob', 'place_prob', 'expected_value'].includes(field)) {
        setSortOrder('desc');
      } else {
        setSortOrder('asc');
      }
    }
  };

  const sortedEntries = useMemo(() => {
    const list = [...entries];
    list.sort((a, b) => {
      const predA = predictionMap.get(a.horse_number);
      const predB = predictionMap.get(b.horse_number);

      let valA: number = 0;
      let valB: number = 0;

      switch (sortField) {
        case 'horse_number':
          valA = a.horse_number;
          valB = b.horse_number;
          break;
        case 'odds':
          valA = a.odds ?? 999;
          valB = b.odds ?? 999;
          break;
        case 'popularity':
          valA = a.popularity ?? 99;
          valB = b.popularity ?? 99;
          break;
        case 'win_prob':
          valA = predA?.win_prob ?? -1;
          valB = predB?.win_prob ?? -1;
          break;
        case 'place_prob':
          valA = predA?.place_prob ?? -1;
          valB = predB?.place_prob ?? -1;
          break;
        case 'expected_value':
          valA = predA?.expected_value ?? -1;
          valB = predB?.expected_value ?? -1;
          break;
        case 'finish_position':
          valA = a.finish_position ?? 99;
          valB = b.finish_position ?? 99;
          break;
      }

      if (valA < valB) return sortOrder === 'asc' ? -1 : 1;
      if (valA > valB) return sortOrder === 'asc' ? 1 : -1;
      return a.horse_number - b.horse_number;
    });
    return list;
  }, [entries, predictionMap, sortField, sortOrder]);

  if (!entries || entries.length === 0) {
    return (
      <div className="p-8 text-center bg-slate-900/60 rounded-xl border border-slate-800 text-slate-400">
        出走馬データがありません。
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/90 shadow-xl">
      <table className="w-full text-left text-xs text-slate-300">
        <thead className="bg-slate-950/80 text-[11px] uppercase tracking-wider text-slate-400 border-b border-slate-800">
          <tr>
            {isFinished && (
              <th
                onClick={() => handleSort('finish_position')}
                className="py-3 px-3 cursor-pointer hover:text-slate-100 transition whitespace-nowrap text-center"
              >
                <div className="flex items-center justify-center space-x-1">
                  <span>着順</span>
                  <ArrowUpDown className="w-3 h-3" />
                </div>
              </th>
            )}
            <th className="py-3 px-2 text-center whitespace-nowrap">枠</th>
            <th
              onClick={() => handleSort('horse_number')}
              className="py-3 px-2 cursor-pointer hover:text-slate-100 transition whitespace-nowrap text-center"
            >
              <div className="flex items-center justify-center space-x-1">
                <span>馬番</span>
                <ArrowUpDown className="w-3 h-3" />
              </div>
            </th>
            <th className="py-3 px-3 whitespace-nowrap">馬名 / 性齢</th>
            <th className="py-3 px-2 text-right whitespace-nowrap">斤量</th>
            <th className="py-3 px-3 whitespace-nowrap">騎手 / 調教師</th>
            <th className="py-3 px-3 text-right whitespace-nowrap">馬体重 (増減)</th>
            <th
              onClick={() => handleSort('odds')}
              className="py-3 px-3 cursor-pointer hover:text-slate-100 transition whitespace-nowrap text-right"
            >
              <div className="flex items-center justify-end space-x-1">
                <span>単勝オッズ</span>
                <ArrowUpDown className="w-3 h-3" />
              </div>
            </th>
            <th
              onClick={() => handleSort('popularity')}
              className="py-3 px-2 cursor-pointer hover:text-slate-100 transition whitespace-nowrap text-center"
            >
              <div className="flex items-center justify-center space-x-1">
                <span>人気</span>
                <ArrowUpDown className="w-3 h-3" />
              </div>
            </th>

            {/* AI Prediction Columns */}
            <th className="py-3 px-2 text-center bg-emerald-950/20 border-l border-r border-emerald-900/30 whitespace-nowrap">
              <span className="text-emerald-400 font-bold">AI印</span>
            </th>
            <th
              onClick={() => handleSort('win_prob')}
              className="py-3 px-3 cursor-pointer hover:text-emerald-300 transition whitespace-nowrap text-right bg-emerald-950/20"
            >
              <div className="flex items-center justify-end space-x-1 text-emerald-400 font-bold">
                <span>予測勝率</span>
                <ArrowUpDown className="w-3 h-3" />
              </div>
            </th>
            <th
              onClick={() => handleSort('place_prob')}
              className="py-3 px-3 cursor-pointer hover:text-cyan-300 transition whitespace-nowrap text-right bg-emerald-950/20"
            >
              <div className="flex items-center justify-end space-x-1 text-cyan-400 font-bold">
                <span>予測複勝率</span>
                <ArrowUpDown className="w-3 h-3" />
              </div>
            </th>
            <th
              onClick={() => handleSort('expected_value')}
              className="py-3 px-3 cursor-pointer hover:text-emerald-300 transition whitespace-nowrap text-center bg-emerald-950/30 border-r border-emerald-900/30"
            >
              <div className="flex items-center justify-center space-x-1 text-emerald-400 font-bold">
                <span>期待値 (EV)</span>
                <ArrowUpDown className="w-3 h-3" />
              </div>
            </th>

            {isFinished && (
              <>
                <th className="py-3 px-3 text-right whitespace-nowrap">タイム</th>
                <th className="py-3 px-2 text-left whitespace-nowrap">着差</th>
              </>
            )}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {sortedEntries.map((entry) => {
            const pred = predictionMap.get(entry.horse_number);
            const isTopMark = pred?.recommendation_mark === '◎';
            const isHighEV = (pred?.expected_value ?? 0) >= 1.20;
            const isPositiveEV = (pred?.expected_value ?? 0) >= 1.00;

            // Row highlighting
            let rowBgClass = 'hover:bg-slate-800/50';
            if (isTopMark) {
              rowBgClass = 'bg-emerald-950/20 hover:bg-emerald-950/30';
            } else if (isHighEV) {
              rowBgClass = 'bg-emerald-950/10 hover:bg-emerald-950/20';
            } else if (isPositiveEV) {
              rowBgClass = 'bg-amber-950/10 hover:bg-amber-950/20';
            }

            return (
              <tr key={entry.horse_number} className={`transition-colors ${rowBgClass}`}>
                {/* Finished Position */}
                {isFinished && (
                  <td className="py-3 px-3 text-center whitespace-nowrap">
                    {entry.finish_position === 1 ? (
                      <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-gradient-to-br from-amber-400 to-yellow-600 text-slate-950 font-black shadow-md shadow-amber-950">
                        1
                      </span>
                    ) : entry.finish_position === 2 ? (
                      <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-gradient-to-br from-slate-200 to-slate-400 text-slate-950 font-black shadow-md shadow-slate-950">
                        2
                      </span>
                    ) : entry.finish_position === 3 ? (
                      <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-gradient-to-br from-amber-700 to-amber-900 text-amber-100 font-black shadow-md shadow-amber-950">
                        3
                      </span>
                    ) : (
                      <span className="text-slate-400 font-mono font-medium text-sm">
                        {entry.finish_position ?? '-'}
                      </span>
                    )}
                  </td>
                )}

                {/* 枠番 (Post Position with JRA colors) */}
                <td className="py-3 px-2 text-center whitespace-nowrap">
                  <span
                    className={`inline-flex items-center justify-center w-6 h-6 rounded text-xs ${getFrameColorClass(
                      entry.post_position
                    )}`}
                  >
                    {entry.post_position}
                  </span>
                </td>

                {/* 馬番 (Horse Number) */}
                <td className="py-3 px-2 text-center whitespace-nowrap">
                  <span className="inline-flex items-center justify-center w-6 h-6 rounded-md bg-slate-800 text-slate-100 font-mono font-bold border border-slate-700">
                    {entry.horse_number}
                  </span>
                </td>

                {/* 馬名 / 性齢 */}
                <td className="py-3 px-3 whitespace-nowrap">
                  <div className="flex flex-col">
                    <span className="font-bold text-slate-100 text-sm hover:text-emerald-400 transition cursor-default">
                      {entry.horse_name}
                    </span>
                    <span className="text-[11px] text-slate-400">
                      {entry.sex}
                      {entry.age}
                    </span>
                  </div>
                </td>

                {/* 斤量 */}
                <td className="py-3 px-2 text-right whitespace-nowrap font-mono text-slate-300">
                  {entry.handicap_weight ? `${entry.handicap_weight.toFixed(1)}kg` : '-'}
                </td>

                {/* 騎手 / 調教師 */}
                <td className="py-3 px-3 whitespace-nowrap">
                  <div className="flex flex-col">
                    <span className="text-slate-200 font-medium">{entry.jockey_name}</span>
                    <span className="text-[11px] text-slate-400">{entry.trainer_name}</span>
                  </div>
                </td>

                {/* 馬体重 */}
                <td className="py-3 px-3 text-right whitespace-nowrap font-mono">
                  {entry.horse_weight ? (
                    <div className="flex items-center justify-end space-x-1">
                      <span className="text-slate-200">{entry.horse_weight}</span>
                      {entry.horse_weight_diff !== undefined &&
                      entry.horse_weight_diff !== null ? (
                        <span
                          className={`text-[11px] ${
                            entry.horse_weight_diff > 0
                              ? 'text-rose-400'
                              : entry.horse_weight_diff < 0
                              ? 'text-cyan-400'
                              : 'text-slate-400'
                          }`}
                        >
                          ({entry.horse_weight_diff > 0 ? `+${entry.horse_weight_diff}` : entry.horse_weight_diff})
                        </span>
                      ) : null}
                    </div>
                  ) : (
                    <span className="text-slate-500">-</span>
                  )}
                </td>

                {/* 単勝オッズ */}
                <td className="py-3 px-3 text-right whitespace-nowrap font-mono">
                  <span
                    className={`text-sm font-bold ${
                      entry.odds < 3.0
                        ? 'text-rose-400'
                        : entry.odds < 10.0
                        ? 'text-amber-300'
                        : 'text-slate-200'
                    }`}
                  >
                    {entry.odds ? entry.odds.toFixed(1) : '-'}
                  </span>
                </td>

                {/* 人気 */}
                <td className="py-3 px-2 text-center whitespace-nowrap font-mono">
                  {entry.popularity ? (
                    <span
                      className={`text-xs px-1.5 py-0.5 rounded ${
                        entry.popularity === 1
                          ? 'bg-rose-950/80 text-rose-300 border border-rose-800/80 font-bold'
                          : entry.popularity <= 3
                          ? 'bg-amber-950/60 text-amber-300 border border-amber-800/60'
                          : 'text-slate-400'
                      }`}
                    >
                      {entry.popularity}人気
                    </span>
                  ) : (
                    <span className="text-slate-500">-</span>
                  )}
                </td>

                {/* AI予想: 印 */}
                <td className="py-3 px-2 text-center bg-emerald-950/10 border-l border-r border-emerald-900/20 whitespace-nowrap">
                  <RecommendationBadge mark={pred?.recommendation_mark} size="sm" />
                </td>

                {/* AI予想: 予測勝率 */}
                <td className="py-3 px-3 text-right bg-emerald-950/10 whitespace-nowrap">
                  <ProbBadge prob={pred?.win_prob} type="win" />
                </td>

                {/* AI予想: 予測複勝率 */}
                <td className="py-3 px-3 text-right bg-emerald-950/10 whitespace-nowrap">
                  <ProbBadge prob={pred?.place_prob} type="place" />
                </td>

                {/* AI予想: 期待値 (EV) */}
                <td className="py-3 px-3 text-center bg-emerald-950/20 border-r border-emerald-900/20 whitespace-nowrap">
                  <EVBadge ev={pred?.expected_value} size="md" />
                </td>

                {/* Finished Result: Time & Margin */}
                {isFinished && (
                  <>
                    <td className="py-3 px-3 text-right whitespace-nowrap font-mono text-slate-200">
                      {entry.finish_time || '-'}
                    </td>
                    <td className="py-3 px-2 text-left whitespace-nowrap text-slate-400 text-xs">
                      {entry.margin || '-'}
                    </td>
                  </>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

export default OddsTable;
