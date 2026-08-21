import React, { useState, useEffect, useCallback } from 'react';
import { Navbar, NavTab } from './components/Navbar';
import { Dashboard } from './pages/Dashboard';
import { Races } from './pages/Races';
import { Simulation } from './pages/Simulation';
import { Backtest } from './pages/Backtest';
import { Models } from './pages/Models';
import { WalletSession } from './types';
import { api } from './services/api';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavTab>('dashboard');
  const [wallet, setWallet] = useState<WalletSession | null>(null);
  const [isLoadingWallet, setIsLoadingWallet] = useState<boolean>(false);

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

  useEffect(() => {
    fetchWallet();
  }, [fetchWallet]);

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100 font-sans antialiased">
      {/* Header & Navbar */}
      <Navbar
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        wallet={wallet}
        isLoadingWallet={isLoadingWallet}
        onRefreshWallet={fetchWallet}
      />

      {/* Main Page Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'dashboard' && <Dashboard onNavigate={setActiveTab} />}
        {activeTab === 'races' && <Races />}
        {activeTab === 'simulation' && <Simulation />}
        {activeTab === 'backtest' && <Backtest />}
        {activeTab === 'models' && <Models />}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-950/90 py-5 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-400 gap-2">
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-slate-300">🏇 PakaPaka Horse Racing AI Platform</span>
            <span>•</span>
            <span className="font-mono text-emerald-400">v1.0.0</span>
          </div>
          <div className="text-slate-500">
            Next-Gen Quantitative Horse Racing Investment & Simulation System
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
