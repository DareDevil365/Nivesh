"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { SearchAutocomplete } from "./SearchAutocomplete";
import { 
  TrendingUp, 
  Search, 
  BarChart2, 
  BrainCircuit, 
  BookOpen, 
  ShieldAlert, 
  Trophy, 
  Menu, 
  X 
} from "lucide-react";

export const Header: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const pathname = usePathname();

  const navLinks = [
    { href: "/stock/RELIANCE.NS", label: "Research", icon: BarChart2, color: "text-primary" },
    { href: "/screener", label: "Screener", icon: Search, color: "text-positive" },
    { href: "/watchlist", label: "Watchlist", icon: ShieldAlert, color: "text-amber-400" },
    { href: "/backtester", label: "Backtester", icon: BrainCircuit, color: "text-secondary" },
    { href: "/behavior", label: "Behavior", icon: BookOpen, color: "text-purple-400" },
    { href: "/leaderboard", label: "Leaderboard", icon: Trophy, color: "text-secondary" },
  ];

  return (
    <header className="sticky top-0 z-40 w-full bg-surface/90 backdrop-blur border-b border-border">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        {/* Brand Logo */}
        <Link href="/" className="flex items-center gap-2 flex-shrink-0 group">
          <div className="w-9 h-9 rounded-lg bg-primary/20 border border-primary/30 flex items-center justify-center text-primary group-hover:scale-105 transition-transform">
            <TrendingUp className="w-5 h-5" />
          </div>
          <span className="font-heading font-bold text-lg text-neutralText tracking-tight">
            NIVESH <span className="text-xs font-normal text-primary">NSE</span>
          </span>
        </Link>

        {/* Search Autocomplete */}
        <div className="hidden sm:block flex-1 max-w-md mx-2">
          <SearchAutocomplete />
        </div>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex items-center gap-1">
          {navLinks.map((link) => {
            const Icon = link.icon;
            const isActive = pathname.startsWith(link.href.split("?")[0]);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  isActive
                    ? "bg-primary/20 text-neutralText border border-primary/30"
                    : "text-mutedText hover:text-neutralText hover:bg-surface/50"
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${link.color}`} />
                <span>{link.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Data Honesty Badge & Mobile Hamburger */}
        <div className="flex items-center gap-2">
          <span className="hidden lg:inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
            Delayed ~15 min
          </span>

          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 rounded-lg text-mutedText hover:text-neutralText hover:bg-surface border border-border"
            aria-label="Toggle Navigation Menu"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden border-b border-border bg-surface px-4 pt-2 pb-4 space-y-3">
          <div className="mb-2">
            <SearchAutocomplete onSelect={() => setMobileMenuOpen(false)} />
          </div>
          <div className="grid grid-cols-2 gap-2">
            {navLinks.map((link) => {
              const Icon = link.icon;
              const isActive = pathname.startsWith(link.href.split("?")[0]);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-2 p-2.5 rounded-lg text-xs font-medium transition-colors ${
                    isActive
                      ? "bg-primary/20 text-neutralText border border-primary/30"
                      : "text-mutedText hover:text-neutralText bg-bg/50"
                  }`}
                >
                  <Icon className={`w-4 h-4 ${link.color}`} />
                  <span>{link.label}</span>
                </Link>
              );
            })}
          </div>
        </div>
      )}
    </header>
  );
};
