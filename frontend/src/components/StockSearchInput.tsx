"use client";

import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Search, ArrowRight, TrendingUp, Loader2 } from "lucide-react";

interface SearchResultItem {
  ticker: string;
  symbol: string;
  name: string;
  sector: string;
  industry: string;
}

interface StockSearchInputProps {
  placeholder?: string;
  className?: string;
  onSelectTicker?: (ticker: string) => void;
  initialValue?: string;
  buttonText?: string;
}

export default function StockSearchInput({
  placeholder = "Type symbol or company (e.g. TA for Tata Motors, Tata Steel, Tata Power, TCS)...",
  className = "",
  onSelectTicker,
  initialValue = "",
  buttonText = "Analyze",
}: StockSearchInputProps) {
  const [query, setQuery] = useState(initialValue);
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const router = useRouter();
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!query || query.trim().length < 1) {
      setResults([]);
      setIsOpen(false);
      setSelectedIndex(-1);
      return;
    }

    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await fetch(`http://localhost:8000/api/companies/search?q=${encodeURIComponent(query.trim())}`);
        if (res.ok) {
          const data = await res.json();
          setResults(data.results || []);
          setIsOpen(true);
          setSelectedIndex(-1);
        }
      } catch (err) {
        // Fallback client lookup for candidate ticker
        const qUpper = query.trim().toUpperCase();
        const fallbackTicker = qUpper.endsWith(".NS") || qUpper.endsWith(".BO") ? qUpper : `${qUpper}.NS`;
        setResults([
          { ticker: fallbackTicker, symbol: qUpper, name: `${qUpper} (NSE Listed)`, sector: "NSE Equity", industry: "Real-time Live Fetch" }
        ]);
        setIsOpen(true);
        setSelectedIndex(-1);
      } finally {
        setLoading(false);
      }
    }, 150);

    return () => clearTimeout(timer);
  }, [query]);

  // Handle click outside to close dropdown
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelect = (ticker: string) => {
    setIsOpen(false);
    setQuery(ticker.replace(".NS", "").replace(".BO", ""));
    if (onSelectTicker) {
      onSelectTicker(ticker);
    } else {
      router.push(`/stock/${ticker}`);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen || results.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev < results.length - 1 ? prev + 1 : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev > 0 ? prev - 1 : results.length - 1));
    } else if (e.key === "Enter" && selectedIndex >= 0 && selectedIndex < results.length) {
      e.preventDefault();
      handleSelect(results[selectedIndex].ticker);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    
    if (selectedIndex >= 0 && selectedIndex < results.length) {
      handleSelect(results[selectedIndex].ticker);
      return;
    }

    let ticker = query.trim().toUpperCase();
    if (!ticker.endsWith(".NS") && !ticker.endsWith(".BO")) {
      ticker = `${ticker}.NS`;
    }
    handleSelect(ticker);
  };

  return (
    <div ref={dropdownRef} className={`relative w-full ${className}`}>
      <form onSubmit={handleSubmit} className="flex gap-2 w-full">
        <div className="relative flex-1">
          <input
            type="text"
            placeholder={placeholder}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => query.trim().length >= 1 && setIsOpen(true)}
            onKeyDown={handleKeyDown}
            className="w-full bg-bg border border-border rounded-lg pl-9 pr-9 py-2.5 text-xs sm:text-sm text-neutralText placeholder:text-mutedText focus:outline-none focus:border-primary transition-colors font-sans"
          />
          <Search className="w-4 h-4 text-mutedText absolute left-3 top-3" />
          {loading && (
            <Loader2 className="w-4 h-4 text-primary absolute right-3 top-3 animate-spin" />
          )}
        </div>
        {buttonText && (
          <button
            type="submit"
            className="bg-primary hover:bg-primary/90 text-white font-medium px-4 sm:px-5 py-2.5 rounded-lg text-xs sm:text-sm transition-colors flex items-center gap-1.5 shrink-0 shadow"
          >
            {buttonText} <ArrowRight className="w-4 h-4" />
          </button>
        )}
      </form>

      {/* Typeahead Dropdown list */}
      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-1.5 bg-surface border border-border rounded-lg shadow-2xl z-50 overflow-hidden max-h-80 overflow-y-auto animate-in fade-in">
          {results.length > 0 ? (
            <div className="divide-y divide-border/60">
              <div className="px-3 py-1.5 bg-bg/50 text-[10px] uppercase tracking-wider text-mutedText font-semibold flex justify-between items-center">
                <span>Matching Equities</span>
                <span>{results.length} matches</span>
              </div>
              {results.map((item, idx) => {
                const isSelected = idx === selectedIndex;
                return (
                  <div
                    key={item.ticker}
                    onClick={() => handleSelect(item.ticker)}
                    onMouseEnter={() => setSelectedIndex(idx)}
                    className={`p-3 cursor-pointer transition-colors flex items-center justify-between group ${
                      isSelected ? "bg-primary/10 border-l-2 border-primary" : "hover:bg-bg/80"
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <div className={`w-7 h-7 rounded flex items-center justify-center font-bold text-xs transition-colors ${
                        isSelected ? "bg-primary text-white" : "bg-primary/20 text-positive group-hover:bg-primary group-hover:text-white"
                      }`}>
                        <TrendingUp className="w-3.5 h-3.5" />
                      </div>
                      <div>
                        <div className="font-heading font-bold text-xs sm:text-sm text-neutralText group-hover:text-primary transition-colors">
                          {item.name}
                        </div>
                        <div className="text-[11px] text-mutedText flex items-center gap-1.5">
                          <span className="font-mono text-positive font-semibold">{item.symbol}</span>
                          <span>•</span>
                          <span>{item.sector}</span>
                          <span>•</span>
                          <span className="text-[10px]">{item.industry}</span>
                        </div>
                      </div>
                    </div>
                    <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded bg-bg text-mutedText border border-border group-hover:border-primary/40">
                      {item.ticker}
                    </span>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="p-4 text-center text-xs text-mutedText">
              No matching NSE symbol found. Press enter to search live.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
