import React from 'react';
import {
  LayoutDashboard,
  Trophy,
  Wallet,
  TrendingUp,
  TrendingDown,
  RefreshCw,
} from 'lucide-react';
import { WalletSession } from '../types';

export type NavTab = 'dashboard' | 'races' | 'simulation';

interface NavbarProps {
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  wallet: WalletSession | null;
  isLoadingWallet: boolean;
  onRefreshWallet: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  onSelectTab,
  wallet,
  isLoadingWallet,
  onRefreshWallet,
}) => {
  const navItems: { id: NavTab; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
    { id: 'dashboard', label: '運用ダッシュボード', icon: LayoutDashboard },
    { id: 'races', label: 'AI競馬予報 (出走表)', icon: Trophy },
    { id: 'simulation', label: 'AI運用履歴・実績', icon: TrendingUp },
  ];

  const currentPoints = wallet?.current_points ?? 100000;
  const roi = wallet?.roi ?? 0;
  const profit = wallet?.profit ?? 0;
  const isPositive = profit >= 0;

  return (
    <header className="sticky top-0 z-50 bg-slate-900/90 backdrop-blur border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => onSelectTab('dashboard')}>
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-700 flex items-center justify-center shadow-lg shadow-emerald-900/30">
              <span className="text-xl">🏇</span>
            </div>
            <div>
              <span className="text-xl font-bold bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400 bg-clip-text text-transparent">
                PakaPaka
              </span>
              <span className="hidden sm:inline-block ml-2 text-xs px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800/60 font-mono">
                AI Trading
              </span>
            </div>
          </div>

          {/* Desktop Navigation Tabs */}
          <nav className="hidden md:flex items-center space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onSelectTab(item.id)}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Live Wallet Badge */}
          <div className="flex items-center space-x-2">
            <div className="flex items-center bg-slate-800/80 border border-slate-700 rounded-lg px-3 py-1.5 shadow-inner">
              <Wallet className="w-4 h-4 text-emerald-400 mr-2" />
              <div className="flex flex-col">
                <span className="text-[10px] text-slate-400 leading-tight uppercase tracking-wider">Wallet Balance</span>
                <span className="text-sm font-bold text-slate-100 font-mono">
                  {currentPoints.toLocaleString()} <span className="text-xs font-normal text-emerald-400">pt</span>
                </span>
              </div>
              <div className="hidden sm:flex flex-col ml-3 pl-3 border-l border-slate-700">
                <span className="text-[10px] text-slate-400 leading-tight">ROI / 収支</span>
                <div className="flex items-center space-x-1">
                  {isPositive ? (
                    <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <TrendingDown className="w-3.5 h-3.5 text-rose-400" />
                  )}
                  <span
                    className={`text-xs font-mono font-semibold ${
                      isPositive ? 'text-emerald-400' : 'text-rose-400'
                    }`}
                  >
                    {roi > 0 ? `${roi.toFixed(1)}%` : `${roi.toFixed(1)}%`} ({profit >= 0 ? `+${profit.toLocaleString()}` : profit.toLocaleString()})
                  </span>
                </div>
              </div>
              <button
                onClick={onRefreshWallet}
                disabled={isLoadingWallet}
                title="ウォレット更新"
                className="ml-2.5 p-1 rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-700 transition disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoadingWallet ? 'animate-spin text-emerald-400' : ''}`} />
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Tab Bar */}
        <div className="md:hidden flex items-center justify-around py-2 border-t border-slate-800/80">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`flex flex-col items-center py-1 px-2 rounded text-xs transition ${
                  isActive ? 'text-emerald-400 font-bold' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Icon className="w-4 h-4 mb-0.5" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
};

export default Navbar;
