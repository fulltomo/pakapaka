import axios from 'axios';
import {
  Race,
  Prediction,
  SimulatedBet,
  WalletSession,
  BacktestRequest,
  BacktestResult,
  ActiveModelStatus,
  ModelTrainRequest,
  ModelTrainResponse,
  AutoBetRequest,
  AutoBetResult,
  SettleResult,
  SampleDataGenerateResponse,
  RaceFilterParams,
  BetFilterParams,
} from '../types';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  // ==========================================
  // Races & Data Management
  // ==========================================

  /**
   * Retrieves a list of races with optional filters (date, race_course, status).
   */
  getRaces: async (params?: RaceFilterParams): Promise<Race[]> => {
    const res = await apiClient.get<Race[]>('/races', { params });
    return res.data;
  },

  /**
   * Retrieves detailed race information including entries, payouts, and predictions.
   */
  getRaceDetail: async (raceId: string): Promise<Race> => {
    const res = await apiClient.get<Race>(`/races/${raceId}`);
    return res.data;
  },

  /**
   * Generates synthetic Japanese horse racing sample dataset.
   */
  generateSampleData: async (
    count = 20,
    scheduledCount = 0,
    startDate = '2024-01-06'
  ): Promise<SampleDataGenerateResponse> => {
    const res = await apiClient.post<SampleDataGenerateResponse>('/races/sample', null, {
      params: {
        count,
        scheduled_count: scheduledCount,
        start_date: startDate,
      },
    });
    return res.data;
  },

  /**
   * Scrapes race data from netkeiba by race ID.
   */
  scrapeRace: async (raceId: string, useCache = true): Promise<Race> => {
    const res = await apiClient.post<Race>('/races/scrape', null, {
      params: { race_id: raceId, use_cache: useCache },
    });
    return res.data;
  },

  // ==========================================
  // ML Model Management
  // ==========================================

  /**
   * Triggers LightGBM model training using finished historical races.
   */
  trainModel: async (params?: ModelTrainRequest): Promise<ModelTrainResponse> => {
    const res = await apiClient.post<ModelTrainResponse>('/models/train', params || {});
    return res.data;
  },

  /**
   * Gets current active model status, metrics, and feature importances.
   */
  getActiveModel: async (): Promise<ActiveModelStatus> => {
    const res = await apiClient.get<ActiveModelStatus>('/models/active');
    return res.data;
  },

  // ==========================================
  // Predictions & Expected Value (EV)
  // ==========================================

  /**
   * Retrieves or computes ML predictions (win/place prob, EV, recommendation mark) for a race.
   */
  getPredictions: async (raceId: string): Promise<Prediction[]> => {
    const res = await apiClient.get<Prediction[]>(`/predictions/${raceId}`);
    return res.data;
  },

  // ==========================================
  // Strategy Backtesting
  // ==========================================

  /**
   * Runs historical strategy backtest with customizable EV thresholds and Kelly sizing.
   */
  runBacktest: async (params: BacktestRequest): Promise<BacktestResult> => {
    const res = await apiClient.post<BacktestResult>('/backtest/run', params);
    return res.data;
  },

  // ==========================================
  // Virtual Wallet & Forward Simulation
  // ==========================================

  /**
   * Retrieves virtual wallet balance, ROI, win rate, and total points.
   */
  getWallet: async (sessionId = 'forward_live'): Promise<WalletSession> => {
    const res = await apiClient.get<WalletSession>('/simulation/wallet', {
      params: { session_id: sessionId },
    });
    return res.data;
  },

  /**
   * Resets virtual wallet balance and statistics.
   */
  resetWallet: async (
    initialPoints = 100000,
    sessionId = 'forward_live'
  ): Promise<WalletSession> => {
    const res = await apiClient.post<WalletSession>('/simulation/wallet/reset', {
      session_id: sessionId,
      initial_points: initialPoints,
    });
    return res.data;
  },

  /**
   * Automatically places simulated bets on upcoming scheduled races matching strategy criteria.
   */
  autoBet: async (params?: AutoBetRequest): Promise<AutoBetResult> => {
    const res = await apiClient.post<AutoBetResult>('/simulation/auto-bet', params || {});
    return res.data;
  },

  /**
   * Settles pending bets against finished race results.
   */
  settleRaces: async (sessionId = 'forward_live'): Promise<SettleResult> => {
    const res = await apiClient.post<SettleResult>('/simulation/settle', null, {
      params: { session_id: sessionId },
    });
    return res.data;
  },

  /**
   * Retrieves a paginated list of simulated bets for a session.
   */
  getSimulatedBets: async (params?: BetFilterParams): Promise<SimulatedBet[]> => {
    const res = await apiClient.get<SimulatedBet[]>('/simulation/bets', { params });
    return res.data;
  },
};

export default api;
