# 🏇 PakaPaka (パカパカ) - JRA AI 競馬投資・期待値運用プラットフォーム

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3+-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5+-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4+-38B2AC.svg?logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![LightGBM](https://img.shields.io/badge/LightGBM-4.6+-FF6F00.svg)](https://lightgbm.readthedocs.io)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.14-3776AB.svg?logo=python&logoColor=white)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**PakaPaka** は、JRA（日本中央競馬会）の出馬表データ・リアルタイムオッズからオッズの歪み（市場の過小評価・期待値 $> 1.0$）を LightGBM 機械学習モデルで検出し、ケリー基準に基づく最適資金管理で自動運用・シミュレーションを行う本格的な **AI 競馬クオンツ投資プラットフォーム** です。

---

## 🌟 主な機能 (Key Features)

- 🧠 **機械学習による確率推定 & キャリブレーション (LightGBM Probabilistic ML)**
  - 出馬表（馬齢、性別、斤量、馬体重増減、枠番、馬番、距離、芝/ダート、馬場状態）および市場人気・オッズから多面的に特徴量を抽出。
  - Platt Scaling (Sigmoid) キャリブレーションとレース内ソフトマックス正規化により、歪みのない真の勝率・複勝率を推定。
  - 単勝 ROC-AUC $> 0.85$、LogLoss、Brier Score による厳密なモデル評価。

- 🎯 **期待値分析 & 推奨印エンジン (EV Engine & Recommendation Marks)**
  - 予測勝率 $p$ と確定オッズ $O$ から期待値 $EV = p \times O$ をリアルタイム算出。
  - $EV > 1.15$ の割安馬を自動検出。JRA伝統の推奨印（本命 `◎`、対抗 `◯`、単穴 `▲`、穴馬 `☆`）を自動付与。

- 📊 **戦略バックテスト (Historical Backtesting)**
  - 単勝EV戦略・複勝EV戦略・定額ベット・フラクショナルケリー基準（Fractional Kelly Criterion）をサポート。
  - 回収率 (ROI)、的中率、プロフィットファクター (PF)、最大ドローダウン (Max Drawdown)、資産推移曲線（Equity Curve）を即時可視化。

- 💰 **フォワードテスト & 仮想ウォレット (Forward Paper Trading)**
  - 初期資金（100,000 pt）の仮想ウォレットを用いた出走前レースへの自動投票機能（Auto-Bet）。
  - レース確定後の自動精算（Settle）と払戻金・損益・ドローダウンのリアルタイムトラッキング。

- 🖥️ **リアルタイム投資ダッシュボード (Executive Dashboard)**
  - Tailwind CSS + Recharts によるモダンで洗練されたダークテーマ UI。
  - レース出馬表、オッズ分析、モデル性能、直近の的中速報、資産推移グラフを一画面で直感的に操作可能。

---

## 🛠️ 技術スタック (Tech Stack)

| レイヤー | 主要技術 |
|---|---|
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy 2.0, SQLite / PostgreSQL, Pydantic v2, Uvicorn |
| **Machine Learning** | LightGBM, Scikit-Learn, Pandas, NumPy, Joblib |
| **Data Collection** | BeautifulSoup4, Requests, HTTP Cache |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, Recharts, Lucide React, Axios |
| **Testing & Quality** | Pytest (46 テスト), TypeScript Strict Mode, ESLint |

---

## 🚀 クイックスタート (Quick Start)

### 1. 前提条件
- Python 3.11 以上
- Node.js 18 以上 (npm 9 以上)

### 2. リポジトリのクローン & バックエンド環境構築
```bash
git clone https://github.com/tfull/pakapaka.git
cd pakapaka

# Python仮想環境の作成と有効化
python3 -m venv .venv
source .venv/bin/activate

# バックエンド依存関係のインストール
pip install -r backend/requirements.txt
```

### 3. フロントエンド依存関係のインストール
```bash
cd frontend
npm install
cd ..
```

### 4. 初期データ投入 & モデル学習 (一発初期化)
初期シードスクリプトを実行することで、100件の確定レースデータ投入、LightGBMモデルの初期学習、出走前20レースの予想生成、初期ウォレット（100,000 pt）のセットアップが一括で行われます。

```bash
PYTHONPATH=backend python backend/seed_data.py
```

### 5. サーバーの起動

#### バックエンド API サーバー (FastAPI)
```bash
# 仮想環境が有効な状態で実行
PYTHONPATH=backend uvicorn main:app --reload --port 8000
```
- APIドキュメント (Swagger UI): [http://localhost:8000/docs](http://localhost:8000/docs)
- ヘルスチェック: [http://localhost:8000/health](http://localhost:8000/health)

#### フロントエンド 開発サーバー (React + Vite)
```bash
cd frontend
npm run dev
```
- アプリケーション画面: [http://localhost:5173](http://localhost:5173)

---

## 📖 画面構成・運用ガイド (Walkthrough)

### 1. ダッシュボード (`/`)
- ウォレット残高、通算純損益、回収率 (ROI)、的中率、最大ドローダウン、最新モデルのROC-AUCを表示。
- 資産推移曲線（Equity Curve）により、これまでの運用パフォーマンスを一目で確認。
- 「🎯 未発走レースに自動投票」「💰 確定レースを自動精算」「🧠 モデル再学習」「🎲 サンプル生成」のクイックアクションをワンクリックで実行可能。

### 2. レース一覧・詳細・AI予想 (`/races`)
- JRA全レースの開催日・競馬場・距離・馬場状態ごとのフィルタリング。
- 出馬表各馬の勝率予測・複勝率予測・リアルタイムオッズ・期待値 (EV)・AI推奨マーク（`◎` `◯` `▲` `☆`）の確認。

### 3. バックテスト (`/backtest`)
- 対象期間、戦略種別（単勝EV / 複勝EV）、最低期待値しきい値、資金管理方式（定額 / ケリー基準）を指定して過去レースを一括検証。
- 損益推移グラフ、月別パフォーマンス、全投票明細を表示。

### 4. フォワード運用 (`/simulation`)
- 仮想資金を用いたペーパートレード管理。
- 投票待ちチケット（Pending）、的中チケット（Won）、不的中チケット（Lost）のステータス管理と精算履歴。

### 5. モデル管理 (`/models`)
- 稼働中モデルの性能指標（ROC-AUC, LogLoss, Brier Score）の確認。
- 特徴量重要度（Feature Importance）のランキング表示。
- 最新レースデータを用いた追加学習（Retrain）トリガー。

---

## 📡 REST API 仕様 (API Reference)

| メソッド | エンドポイント | 説明 |
|---|---|---|
| `GET` | `/health` | システムヘルスチェック |
| `GET` | `/races` | レース一覧取得（ステータス・日付・競馬場フィルタ） |
| `GET` | `/races/{race_id}` | レース詳細・出馬表・オッズ・払戻金取得 |
| `POST` | `/data/sample` | サンプルレースデータの生成 |
| `POST` | `/data/scrape` | netkeiba等の出馬表スクレイピング |
| `GET` | `/models/active` | 現在アクティブな機械学習モデルのステータス取得 |
| `POST` | `/models/train` | モデルの再学習・評価・保存 |
| `GET` | `/predictions/{race_id}` | 特定レースのAI予想結果取得 |
| `POST` | `/predictions/predict/{race_id}` | AI予想の再計算・更新 |
| `POST` | `/backtest/run` | 戦略バックテストの実行 |
| `GET` | `/simulation/wallet` | 仮想ウォレット残高・KPI取得 |
| `POST` | `/simulation/wallet/reset` | ウォレット初期化（100,000 pt） |
| `POST` | `/simulation/auto-bet` | 出走予定レースへの自動投票実行 |
| `POST` | `/simulation/settle` | 確定レースの自動払戻精算実行 |
| `GET` | `/simulation/bets` | シミュレーション投票明細一覧 |

---

## 🧪 テストの実行 (Testing)

### バックエンド単体・結合テスト (Pytest)
```bash
PYTHONPATH=backend pytest backend/tests/ -v
```
- 全46件のテスト（API、データベース、特徴量抽出、リーク防止検証、ML学習/推論、バックテスト、フォワードシミュレータ）がパスします。

### フロントエンド型チェック & プロダクションビルド
```bash
cd frontend
npm run build
```

---

## 📂 ディレクトリ構成 (Project Structure)

```
pakapaka/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI REST ルーター (races, models, predictions, backtest, simulation)
│   │   ├── core/            # 設定・データベースセッション管理 (config, database)
│   │   ├── data/            # データスクレイパー・HTMLキャッシュ・合成データ生成
│   │   ├── ml/              # 特徴量抽出・LightGBMモデル・学習・推論エンジン
│   │   ├── models/          # SQLAlchemy ORM モデル (Race, RaceEntry, Payout, Prediction, SimulatedBet)
│   │   ├── schemas/         # Pydantic v2 スキーマ (リクエスト/レスポンスモデル)
│   │   └── strategy/        # ベッティング戦略・資金管理 (EV, Kelly, Backtest, Simulator)
│   ├── tests/               # Pytest テストスイート (46 test cases)
│   ├── seed_data.py         # 初期シード・モデル学習スクリプト
│   └── requirements.txt     # Python 依存ライブラリ一覧
├── frontend/
│   ├── src/
│   │   ├── components/      # UI共通コンポーネント (StatCard, EquityChart, OddsTable, Navbar, etc.)
│   │   ├── pages/           # 各画面 (Dashboard, Races, Backtest, Simulation, Models)
│   │   ├── services/        # Axios API クライアント
│   │   ├── types/           # TypeScript 型定義
│   │   ├── App.tsx          # メインルーター・タブ切り替え
│   │   └── main.tsx         # エントリーポイント
│   ├── package.json         # Node.js 依存パッケージ
│   ├── tailwind.config.js   # Tailwind CSS 設計
│   └── vite.config.ts       # Vite ビルド設定
└── README.md                # 本ドキュメント
```

---

## ⚖️ 免責事項 (Disclaimer)

本ソフトウェアは競馬データの分析および機械学習によるクオンツ投資戦略の学術的・技術的研究を目的として開発されています。実際の勝馬投票券の購入・投資判断は利用者ご自身の責任において行ってください。本ソフトウェアの使用によって生じた損害等について、開発者は一切の責任を負いません。
