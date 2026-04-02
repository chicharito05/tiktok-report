"use client";

import { Users, FileText, Film, TrendingUp } from "lucide-react";

const iconMap = {
  users: Users,
  fileText: FileText,
  film: Film,
  trendingUp: TrendingUp,
};

type IconName = keyof typeof iconMap;

interface StatCardProps {
  iconName: IconName;
  label: string;
  value: string | number;
  sub?: string;
  color?: "accent" | "blue" | "emerald" | "amber";
}

const colorMap = {
  accent: {
    bg: "bg-red-50",
    icon: "text-accent",
  },
  blue: {
    bg: "bg-blue-50",
    icon: "text-blue-600",
  },
  emerald: {
    bg: "bg-emerald-50",
    icon: "text-emerald-600",
  },
  amber: {
    bg: "bg-amber-50",
    icon: "text-amber-600",
  },
};

export default function StatCard({
  iconName,
  label,
  value,
  sub,
  color = "accent",
}: StatCardProps) {
  const colors = colorMap[color];
  const Icon = iconMap[iconName];
  return (
    <div className="bg-white rounded-xl border border-gray-200/80 p-5 card-hover">
      <div className="flex items-center gap-3 mb-3">
        <div
          className={`w-10 h-10 ${colors.bg} rounded-xl flex items-center justify-center`}
        >
          <Icon size={20} className={colors.icon} />
        </div>
        <span className="text-sm text-gray-500">{label}</span>
      </div>
      <p className="text-2xl font-bold text-primary tabular-nums">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}
