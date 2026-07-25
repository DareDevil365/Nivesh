"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Star, Bell, Plus, Trash2, ArrowUpRight, ArrowDownRight, ShieldCheck, AlertCircle } from "lucide-react";

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

  const fetchWatchlist = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/watchlist");
      if (res.ok) {
        const data = await res.json();
        setItems(data.items || []);
      }
    } catch (err) {
      setItems([
        { ticker: "RELIANCE.NS", name: "Reliance Industries", sector: "Energy", current_price: 2980.5, day_change: 36.8, day_change_pct: 1.25, pe: 24.5, roe: 16.5 },
        { ticker: "TCS.NS", name: "Tata Consultancy Services", sector: "IT Services", current_price: 3940.0, day_change: 33.1, day_change_pct: 0.85, pe: 28.2, roe: 48.5 },
        { ticker: "INFY.NS", name: "Infosys Ltd", sector: "IT Services", current_price: 1620.4, day_change: -6.5, day_change_pct: -0.40, pe: 23.4, roe: 31.2 },
        { ticker: "HDFCBANK.NS", name: "HDFC Bank Ltd", sector: "Banking", current_price: 1440.15, day_change: 8.5, day_change_pct: 0.60, pe: 18.5, roe: 16.8 },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const fetchAlerts = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/watchlist/alerts");
      if (res.ok) {
        const data = await res.json();
        setAlerts(data.alerts || []);
      }
    } catch (err) {
      setAlerts([
        { id: "alert-1", ticker: "RELIANCE.NS", condition: "PRICE_ABOVE", threshold: 3100.0, active: true },
        { id: "alert-2", ticker: "TCS.NS", condition: "RSI_BELOW", threshold: 30.0, active: true },
      ]);
    }
  };

  useEffect(() => {
    fetchWatchlist();
    fetchAlerts();
  }, []);

  const handleAddStock = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTicker.trim()) return;
    try {
      await fetch("http://localhost:8000/api/watchlist/item", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker: newTicker.trim() }),
      });
      setNewTicker("");
      fetchWatchlist();
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateAlert = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await fetch("http://localhost:8000/api/watchlist/alerts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticker: alertTicker,
          condition: alertCondition,
          threshold: parseFloat(alertThreshold),
        }),
      });
      fetchAlerts();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="bg-surface border border-border rounded-card p-6 md:p-8 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2">
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
        <form onSubmit={handleAddStock} className="flex gap-2">
          <input
            type="text"
            placeholder="Add ticker (e.g. INFY)..."
            value={newTicker}
            onChange={(e) => setNewTicker(e.target.value)}
            className="bg-bg border border-border rounded-lg px-3 py-2 text-xs text-neutralText focus:outline-none focus:border-primary"
          />
          <button
            type="submit"
            className="bg-primary hover:bg-primary/90 text-white font-semibold text-xs px-4 py-2 rounded-lg flex items-center gap-1 transition-colors"
          >
            <Plus className="w-4 h-4" /> Add
          </button>
        </form>
      </div>

      {/* Grid: Watchlist Table + Create Alert Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Watchlist Table */}
        <div className="lg:col-span-2 bg-surface border border-border rounded-card p-6 space-y-4">
          <h2 className="font-heading font-bold text-lg text-neutralText">
            Your Tracked Stocks ({items.length})
          </h2>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
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
                {items.map((stk) => {
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
                      <td className="py-3.5 px-3 text-right">
                        <Link href={`/stock/${stk.ticker}`} className="text-xs text-primary font-medium hover:underline">
                          View →
                        </Link>
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
                  value={alertTicker}
                  onChange={(e) => setAlertTicker(e.target.value)}
                  className="w-full bg-bg border border-border rounded-lg p-2 text-neutralText focus:outline-none focus:border-primary"
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
                <label className="text-mutedText block mb-1 font-semibold">Threshold Value</label>
                <input
                  type="number"
                  value={alertThreshold}
                  onChange={(e) => setAlertThreshold(e.target.value)}
                  className="w-full bg-bg border border-border rounded-lg p-2 text-neutralText focus:outline-none focus:border-primary"
                />
              </div>

              <button
                type="submit"
                className="w-full bg-primary hover:bg-primary/90 text-white font-semibold py-2.5 rounded-lg transition-colors flex items-center justify-center gap-1.5"
              >
                <Bell className="w-4 h-4" /> Create Alert Trigger
              </button>
            </form>
          </div>

          {/* Active Alerts List */}
          <div className="pt-4 border-t border-border space-y-2">
            <div className="text-xs font-semibold text-mutedText">Active Trigger List</div>
            <div className="space-y-1.5">
              {alerts.map((al) => (
                <div key={al.id} className="flex items-center justify-between p-2 rounded bg-bg text-xs border border-border">
                  <div>
                    <strong className="text-neutralText">{al.ticker}</strong>
                    <div className="text-[10px] text-mutedText">{al.condition} {al.threshold}</div>
                  </div>
                  <span className="w-2 h-2 rounded-full bg-positive animate-pulse" />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
