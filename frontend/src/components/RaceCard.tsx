import React from 'react';
import { Race } from '../types';
import { RecommendationBadge, EVBadge } from './PredictionBadge';
import { Calendar, Users, MapPin, Gauge } from 'lucide-react';

interface RaceCardProps {
  race: Race;
  isSelected?: boolean;
  onClick?: (race: Race) => void;
}

export const RaceCard: React.FC<RaceCardProps> = ({
  race,
  isSelected = false,
  onClick,
}) => {
  const isFinished = race.status === 'finished';
  const entryCount = race.entries ? race.entries.length : 0;

  // Find top pick (◎) if predictions are attached
  const topPrediction = race.predictions?.find(
    (p) => p.recommendation_mark === '◎'
  );

  // Surface color badge
  const isTurf = race.surface.includes('芝');
  const surfaceBadgeClass = isTurf
    ? 'bg-emerald-950/80 text-emerald-300 border-emerald-800/80'
    : 'bg-amber-950/80 text-amber-300 border-amber-800/80';

  return (
    <div
      onClick={() => onClick && onClick(race)}
      className={`group relative rounded-xl p-4 transition-all cursor-pointer border ${
        isSelected
          ? 'bg-slate-900 border-emerald-500 shadow-lg shadow-emerald-950/40 ring-1 ring-emerald-500/40'
          : 'bg-slate-900/80 hover:bg-slate-850 border-slate-800 hover:border-slate-700'
      }`}
    >
      {/* Top Header: Race Number, Course, Status */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          <span className="px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-xs font-mono font-bold">
            {race.race_number}R
          </span>
          <span className="text-sm font-bold text-slate-200 flex items-center">
            <MapPin className="w-3.5 h-3.5 mr-0.5 text-slate-400" />
            {race.race_course}
          </span>
        </div>

        <span
          className={`text-[11px] px-2 py-0.5 rounded-full font-medium border ${
            isFinished
              ? 'bg-slate-800 text-slate-400 border-slate-700'
              : 'bg-emerald-950/90 text-emerald-400 border-emerald-800 animate-pulse'
          }`}
        >
          {isFinished ? '確定' : '出走前'}
        </span>
      </div>

      {/* Race Name */}
      <h3
        className={`text-base font-bold truncate transition-colors ${
          isSelected ? 'text-emerald-400' : 'text-slate-100 group-hover:text-emerald-300'
        }`}
        title={race.race_name}
      >
        {race.race_name}
      </h3>

      {/* Race Metadata: Surface, Distance, Condition, Entries */}
      <div className="mt-2.5 flex flex-wrap items-center gap-1.5 text-xs">
        <span className={`px-2 py-0.5 rounded border font-medium ${surfaceBadgeClass}`}>
          {race.surface} {race.distance}m
        </span>

        {race.track_condition && (
          <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 flex items-center">
            <Gauge className="w-3 h-3 mr-1 text-slate-400" />
            {race.track_condition}
          </span>
        )}

        {entryCount > 0 && (
          <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 flex items-center">
            <Users className="w-3 h-3 mr-1 text-slate-500" />
            {entryCount}頭
          </span>
        )}
      </div>

      {/* Footer info: Date / AI Top Pick Preview */}
      <div className="mt-3 pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
        <div className="flex items-center space-x-1">
          <Calendar className="w-3.5 h-3.5 text-slate-500" />
          <span>{race.date}</span>
        </div>

        {topPrediction ? (
          <div className="flex items-center space-x-1.5">
            <span className="text-[10px] text-slate-500">AI本命:</span>
            <RecommendationBadge mark="◎" size="sm" />
            <span className="font-mono font-semibold text-slate-300">
              {topPrediction.horse_number}番
            </span>
            <EVBadge ev={topPrediction.expected_value} size="sm" showIcon={false} />
          </div>
        ) : (
          <span className="text-[11px] text-slate-500">予想未取得</span>
        )}
      </div>
    </div>
  );
};

export default RaceCard;
