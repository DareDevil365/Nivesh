"use client";

import React from "react";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from "recharts";

interface SnowflakeScores {
  value: number;
  future: number;
  past: number;
  health: number;
  dividend: number;
}

interface SnowflakeChartProps {
  scores: SnowflakeScores;
}

export default function SnowflakeChart({ scores }: SnowflakeChartProps) {
  const data = [
    { subject: "VALUE", score: scores.value, full: 6 },
    { subject: "FUTURE", score: scores.future, full: 6 },
    { subject: "PAST", score: scores.past, full: 6 },
    { subject: "HEALTH", score: scores.health, full: 6 },
    { subject: "DIVIDEND", score: scores.dividend, full: 6 },
  ];

  const totalScore =
    (scores.value || 0) +
    (scores.future || 0) +
    (scores.past || 0) +
    (scores.health || 0) +
    (scores.dividend || 0);


  return (
    <div className="flex flex-col items-center justify-center p-4 relative">
      <div className="w-full h-[280px]">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="75%" data={data}>
            <PolarGrid stroke="#223028" />
            <PolarAngleAxis
              dataKey="subject"
              tick={{ fill: "#E6EDEA", fontSize: 11, fontWeight: 600 }}
            />
            <PolarRadiusAxis
              angle={90}
              domain={[0, 6]}
              tick={false}
              axisLine={false}
            />
            <Radar
              name="Snowflake"
              dataKey="score"
              stroke="#2ECC71"
              strokeWidth={2}
              fill="#1E7A4C"
              fillOpacity={0.5}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-2 text-center">
        <span className="text-xs text-mutedText uppercase font-semibold tracking-wider">
          Snowflake Score:{" "}
        </span>
        <span className="font-heading font-bold text-lg text-positive ml-1">
          {totalScore} / 30
        </span>
      </div>
    </div>
  );
}
