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

interface DataConfidence {
  value?: "none" | "low" | "high";
  future?: "none" | "low" | "high";
  past?: "none" | "low" | "high";
  health?: "none" | "low" | "high";
  dividend?: "none" | "low" | "high";
}

interface SnowflakeScores {
  value: number;
  future: number;
  past: number;
  health: number;
  dividend: number;
  data_confidence?: DataConfidence;
}

interface SnowflakeChartProps {
  scores: SnowflakeScores;
}

const AXIS_KEY_MAP: Record<string, keyof DataConfidence> = {
  VALUE: "value",
  FUTURE: "future",
  PAST: "past",
  HEALTH: "health",
  DIVIDEND: "dividend",
};

// Custom tick that appends ? or * badges based on data confidence
function ConfidenceTick(props: {
  x?: number;
  y?: number;
  payload?: { value: string };
  dataConfidence?: DataConfidence;
}) {
  const { x = 0, y = 0, payload, dataConfidence } = props;
  if (!payload) return null;

  const label = payload.value;
  const confKey = AXIS_KEY_MAP[label];
  const conf = confKey && dataConfidence ? dataConfidence[confKey] : "high";

  const badge = conf === "none" ? " ?" : conf === "low" ? " *" : "";
  const badgeColor = conf === "none" ? "#f59e0b" : "#facc15";

  return (
    <text
      x={x}
      y={y}
      textAnchor="middle"
      dominantBaseline="central"
      style={{ fontSize: 11, fontWeight: 600 }}
    >
      <tspan fill="#E6EDEA">{label}</tspan>
      {badge && (
        <tspan fill={badgeColor} fontSize={13} fontWeight={700}>
          {badge}
        </tspan>
      )}
    </text>
  );
}

export default function SnowflakeChart({ scores }: SnowflakeChartProps) {
  const conf = scores.data_confidence;

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

  const hasUncertainty =
    conf && Object.values(conf).some((v) => v === "none" || v === "low");

  return (
    <div className="flex flex-col items-center justify-center p-4 relative">
      <div className="w-full h-[280px]">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="75%" data={data}>
            <PolarGrid stroke="#223028" />
            <PolarAngleAxis
              dataKey="subject"
              tick={(tickProps) => (
                <ConfidenceTick {...tickProps} dataConfidence={conf} />
              )}
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

      {/* Confidence legend — only shown if there is at least one uncertain axis */}
      {hasUncertainty && (
        <div className="mt-2 flex items-center gap-3 text-[10px] text-mutedText">
          {conf && Object.values(conf).includes("none") && (
            <span>
              <span className="text-amber-400 font-bold">?</span> = No data
            </span>
          )}
          {conf && Object.values(conf).includes("low") && (
            <span>
              <span className="text-yellow-300 font-bold">*</span> = Partial
              data
            </span>
          )}
        </div>
      )}
    </div>
  );
}
