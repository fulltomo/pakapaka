// ==========================================
// Race & Entry & Payout Types
// ==========================================

export interface RaceEntry {
  id?: number;
  race_id?: string;
  horse_id: string;
  horse_name: string;
  post_position: number;
  horse_number: number;
  jockey_name: string;
  trainer_name: string;
  sex: string;
  age: number;
  handicap_weight: number;
  horse_weight?: number | null;
  horse_weight_diff?: number | null;
  odds: number;
  popularity?: number | null;
  finish_position?: number | null;
  finish_time?: string | null;
  margin?: string | null;
}

export interface Payout {
  id?: number;
  race_id?: string;
  bet_type: string;
  combination: string;
  payout: number;
}

export interface Prediction {
  id?: number;
  race_id?: string;
  horse_number: number;
  model_version?: string | null;
  win_prob: number;
  place_prob: number;
  expected_value: number;
  recommendation_mark: string; // '◎' | '◯' | '▲' | '☆' | '-'
  created_at?: string;
}

export interface Race {
  id: string;
  date: string;
  race_course: string;
  race_number: number;
  race_name: string;
  distance: number;
  surface: string;
  track_condition: string;
  weather: string;
  status: 'scheduled' | 'finished' | string;
  entries?: RaceEntry[];
  payouts?: Payout[];
  predictions?: Prediction[];
}

export interface RaceFilterParams {
  date?: string;
  race_course?: string;
  status?: string;
  limit?: number;
  offset?: number;
}

// ==========================================
// Simulation & Wallet Types
// ==========================================

export interface SimulatedBet {
  id?: number;
  session_id: string;
  race_id: string;
  bet_type: string;
  combination: string;
  bet_points: number;
  odds_at_bet: number;
  expected_value_at_bet: number;
  status: 'pending' | 'won' | 'lost' | string;
  payout_points: number;
  profit: number;
  created_at?: string;
  race_name?: string | null;
  race_date?: string | null;
}

export interface WalletSession {
  session_id: string;
  initial_points: number;
  current_points: number;
  total_invested: number;
  total_returned: number;
  total_bets: number;
  won_bets: number;
  max_drawdown: number;
  roi?: number;
  win_rate?: number;
  profit?: number;
}

export interface BetFilterParams {
  session_id?: string;
  status?: string;
  limit?: number;
  offset?: number;
}

export interface AutoBetRequest {
  session_id?: string;
  target_date?: string | null;
  min_ev?: number;
  bet_type?: string;
  bet_amount?: number;
  use_kelly?: boolean;
  kelly_fraction?: number;
  min_prob?: number;
}

export interface AutoBetResult {
  session_id: string;
  placed_bets_count: number;
  total_points_spent: number;
  remaining_points: number;
  placed_bets: SimulatedBet[];
}

export interface SettleResult {
  status: string;
  session_id: string;
  settled_bets_count: number;
  settled_bets: SimulatedBet[];
  current_points: number;
}

// ==========================================
// Backtest Types
// ==========================================

export interface BacktestRequest {
  start_date?: string | null;
  end_date?: string | null;
  min_ev?: number;
  bet_type?: string;
  bet_amount?: number;
  use_kelly?: boolean;
  kelly_fraction?: number;
  min_prob?: number;
}

export interface EquityPoint {
  date: string;
  race_id: string;
  cumulative_profit: number;
  balance: number;
  drawdown: number;
}

export interface BacktestResult {
  total_bets: number;
  won_bets: number;
  win_rate: number;
  total_invested: number;
  total_returned: number;
  profit: number;
  roi: number;
  max_drawdown: number;
  profit_factor: number;
  equity_curve: EquityPoint[];
  bets: SimulatedBet[];
}

// ==========================================
// ML Model Types
// ==========================================

export interface ModelMetrics {
  train_samples?: number;
  test_samples?: number;
  roc_auc?: number;
  log_loss?: number;
  model_version?: string;
  [key: string]: unknown;
}

export interface ActiveModelStatus {
  status: 'active' | 'not_trained' | string;
  model_version: string | null;
  feature_importance: Record<string, number>;
  metrics: ModelMetrics | null;
  roc_auc: number | null;
  log_loss: number | null;
}

export interface ModelTrainRequest {
  model_type?: string;
  test_size?: number;
  random_state?: number;
}

export interface ModelTrainResponse {
  status: string;
  model_version: string;
  roc_auc: number;
  log_loss: number;
  feature_importance: Record<string, number>;
  trained_samples: number;
}

export interface SampleDataGenerateResponse {
  status: string;
  generated_races: number;
}
