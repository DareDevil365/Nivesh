"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Star, Bell, Trash2, ArrowUpRight, ArrowDownRight, AlertCircle } from "lucide-react";
import StockSearchInput from "@/components/StockSearchInput";


interface WatchlistItem {
  ticker: string;
  name: string;
  sector: string;
  current_price: number;
  day_change: number;
  day_change_pct: number;
  pe: number;
  roe: number;
}

interface AlertItem {
  id: string;
  ticker: string;
  condition: string;
  threshold: number;
  active: boolean;
}

export default function WatchlistPage() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState(true);

  const [newTicker, setNewTicker] = useState("");
  const [alertTicker, setAlertTicker] = useState("RELIANCE.NS");
  const [alertCondition, setAlertCondition] = useState("PRICE_ABOVE");
  const [alertThreshold, setAlertThreshold] = useState("3100");

  const [loadError, setLoadError] = useState<string | null>(null);

  const fetchWatchlist = async () => {
    try {
      const data = await api.get<{ items: WatchlistItem[] }>("/api/watchlist");
      setItems(data.items || []);
    } catch (err) {
      setLoadError("Unable to load watchlist. Make sure the backend server is running.");
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchAlerts = async () => {
    try {
      const data = await api.get<{ alerts: AlertItem[] }>("/api/watchlist/alerts");
      setAlerts(data.alerts || []);
    } catch (err) {
      setAlerts([]);
    }
  };

  useEffect(() => {
    fetchWatchlist();
    fetchAlerts();
  }, []);

  const handleAddStock = async (tickerToAdd?: string) => {
    const symbol = tickerToAdd || newTicker;
    if (!symbol.trim()) return;
    try {
      await api.post("/api/watchlist/item", { ticker: symbol.trim() });
      setNewTicker("");
      fetchWatchlist();
    } catch (err) {
      console.error(err);
    }
  };

  const handleRemoveStock = async (tickerToRemove: string) => {
    try {
      await api.delete(`/api/watchlist/item?ticker=${encodeURIComponent(tickerToRemove)}`);
      setItems((prev) => prev.filter((i) => i.ticker !== tickerToRemove));
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateAlert = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!alertTicker.trim() || !alertThreshold) return;
    try {
      const data = await api.post<{ alert: AlertItem }>("/api/watchlist/alerts", {
        ticker: alertTicker.trim().toUpperCase(),
        condition: alertCondition,
        threshold: parseFloat(alertThreshold),
      });
      if (data.alert) {
        setAlerts((prev) => [data.alert, ...prev]);
      } else {
        fetchAlerts();
      }
      setAlertTicker("");
    } catch (err) {
      // Optimistic update on API failure
      setAlerts((prev) => [
        { id: `alert-${Date.now()}`, ticker: alertTicker.trim().toUpperCase(), condition: alertCondition, threshold: parseFloat(alertThreshold), active: true },
        ...prev,
      ]);
      setAlertTicker("");
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="bg-surface border border-border rounded-card p-6 md:p-8 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2 max-w-xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/20 border border-primary/30 text-positive text-xs font-semibold">
            <Star className="w-3.5 h-3.5" />
            Watchlist & Custom Trigger Alerts
          </div>
          <h1 className="font-heading font-bold text-2xl md:text-3xl text-neutralText">
            NSE Stock Watchlist & Alerts
          </h1>
          <p className="text-mutedText text-xs md:text-sm">
            Track your favorite NSE tickers with live quotes, P/E multiples, and RSI/Price alerts.
          </p>
        </div>

        {/* Add Ticker Form */}
        <div className="w-full md:w-80">
          <label className="text-xs text-mutedText font-semibold mb-1 block">Add Stock to Watchlist</label>
          <StockSearchInput
            placeholder="Type symbol to add (e.g. INFY)..."
            buttonText="Add"
            onSelectTicker={(ticker) => handleAddStock(ticker)}
          />
        </div>
      </div>

      {/* Grid: Watchlist Table + Create Alert Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Watchlist Table */}
        <div className="lg:col-span-2 bg-surface border border-border rounded-card p-6 space-y-4">
          <h2 className="font-heading font-bold text-lg text-neutralText">
            Your Tracked Stocks ({items.length})
          </h2>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs min-w-[650px]">
              <thead>
                <tr className="border-b border-border text-mutedText uppercase text-[11px] font-semibold">
                  <th className="py-3 px-3">Stock</th>
                  <th className="py-3 px-3">Price</th>
                  <th className="py-3 px-3">Day Change</th>
                  <th className="py-3 px-3">P/E</th>
                  <th className="py-3 px-3">ROE</th>
                  <th className="py-3 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {items.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-sm text-mutedText">
                      <div className="space-y-1">
                        <p className="font-semibold text-neutralText">No stocks tracked yet</p>
                        <p className="text-xs">Search above to add your first stock to the watchlist.</p>
                      </div>
                    </td>
                  </tr>
                ) : items.map((stk) => {
                  const isUp = stk.day_change >= 0;
                  return (
                    <tr key={stk.ticker} className="hover:bg-bg/50 transition-colors">
                      <td className="py-3.5 px-3 font-semibold text-neutralText">
                        <Link href={`/stock/${stk.ticker}`} className="hover:text-primary transition-colors">
                          <div>{stk.name}</div>
                          <div className="text-[10px] text-mutedText">{stk.ticker}</div>
                        </Link>
                      </td>
                      <td className="py-3.5 px-3 font-semibold text-neutralText">
                        ₹{stk.current_price.toLocaleString("en-IN")}
                      </td>
                      <td className="py-3.5 px-3">
                        <span className={`font-semibold flex items-center gap-0.5 ${isUp ? "text-positive" : "text-negative"}`}>
                          {isUp ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
                          {isUp ? "+" : ""}{stk.day_change_pct}%
                        </span>
                      </td>
                      <td className="py-3.5 px-3 text-neutralText">{stk.pe}x</td>
                      <td className="py-3.5 px-3 font-semibold text-positive">{stk.roe}%</td>
                      <td className="py-3.5 px-3 text-right space-x-3">
                        <Link href={`/stock/${stk.ticker}`} className="text-xs text-primary font-medium hover:underline">
                          View →
                        </Link>
                        <button
                          onClick={() => handleRemoveStock(stk.ticker)}
                          className="text-xs text-negative hover:underline"
                          title="Remove from Watchlist"
                        >
                          <Trash2 className="w-3.5 h-3.5 inline" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Alerts Configuration Card */}
        <div className="bg-surface border border-border rounded-card p-6 space-y-4 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Bell className="w-5 h-5 text-secondary" />
              <h2 className="font-heading font-bold text-lg text-neutralText">
                Set Price & Indicator Alerts
              </h2>
            </div>

            <form onSubmit={handleCreateAlert} className="space-y-3 text-xs">
              <div>
                <label className="text-mutedText block mb-1 font-semibold">Stock Ticker</label>
                <input
                  type="text"
                  placeholder="e.g. INFY.NS or RELIANCE.NS"
                  value={alertTicker}
                  onFocus={(e) => e.target.select()}
                  onChange={(e) => setAlertTicker(e.target.value)}
                  className="w-full bg-bg border border-border rounded-lg p-2 text-neutralText focus:outline-none focus:border-primary font-mono"
                />
              </div>

              <div>
                <label className="text-mutedText block mb-1 font-semibold">Alert Condition</label>
                <select
                  value={alertCondition}
                  onChange={(e) => setAlertCondition(e.target.value)}
                  className="w-full bg-bg border border-border rounded-lg p-2 text-neutralText focus:outline-none focus:border-primary"
                >
                  <option value="PRICE_ABOVE">Price Crosses Above</option>
                  <option value="PRICE_BELOW">Price Crosses Below</option>
                  <option value="RSI_BELOW">RSI (14) Drops Below (Oversold)</option>
                  <option value="RSI_ABOVE">RSI (14) Rises Above (Overbought)</option>
                  <option value="VOLUME_SPIKE">Volume Spike &gt; 2x Avg</option>
                </select>
              </div>

              <div>
                <label className="text-mutedText block mb-1 font-semibold font-mono">Threshold Value</label>
                <input
                  type="number"
                  placeholder="Threshold numeric value..."
                  value={alertThreshold}
                  onChange={(e) => setAlertThreshold(e.target.value)}
                  className="w-full bg-bg border border-border rounded-lg p-2 text-neutralText focus:outline-none focus:border-primary font-mono"
                />
              </div>

              <button
                type="submit"
                className="w-full bg-primary hover:bg-primary/90 text-white font-semibold py-2.5 rounded-lg transition-colors flex items-center justify-center gap-1.5 shadow"
              >
                <Bell className="w-4 h-4" /> Create Alert Trigger
              </button>
            </form>
          </div>

          {/* Active Alerts List */}
          <div className="pt-4 border-t border-border space-y-2">
            <div className="text-xs font-semibold text-mutedText">Active Trigger List</div>
            <div className="space-y-1.5 max-h-48 overflow-y-auto">
                {alerts.map((al) => {
                  const conditionLabel: Record<string, string> = {
                    PRICE_ABOVE: "Price ↑",
                    PRICE_BELOW: "Price ↓",
                    RSI_BELOW: "RSI(14) ↓",
                    RSI_ABOVE: "RSI(14) ↑",
                    VOLUME_SPIKE: "Vol Spike",
                  };
                  return (
                    <div key={al.id} className="flex items-center justify-between p-2 rounded bg-bg text-xs border border-border">
                      <div>
                        <strong className="text-neutralText font-mono">{al.ticker}</strong>
                        <div className="text-[10px] text-mutedText">
                          {conditionLabel[al.condition] || al.condition} · {al.threshold}
                        </div>
                      </div>
                      <span className="w-2 h-2 rounded-full bg-positive animate-pulse" />
                    </div>
                  );
                })}
            </div>
          </div>
        </div>
      </div>

    </div>
  );
}
