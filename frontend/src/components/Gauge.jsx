/**
 * Gauge 컴포넌트 - % 게이지 표시
 */
import React from 'react';

const statusColors = {
  safe: 'bg-emerald-500',
  ok: 'bg-yellow-400',
  caution: 'bg-orange-500',
  danger: 'bg-red-500',
  good: 'bg-blue-500',
  low: 'bg-gray-400',
};

const statusBgColors = {
  safe: 'bg-emerald-100',
  ok: 'bg-yellow-100',
  caution: 'bg-orange-100',
  danger: 'bg-red-100',
  good: 'bg-blue-100',
  low: 'bg-gray-100',
};

const labels = {
  calories: '칼로리',
  protein: '단백질',
  sugar: '당류',
  sodium: '나트륨',
};

const units = {
  calories: 'kcal',
  protein: 'g',
  sugar: 'g',
  sodium: 'mg',
};

export default function Gauge({ nutrient, value, percentage, status, showValue = true }) {
  const barWidth = Math.min(percentage, 100);
  const color = statusColors[status] || statusColors.safe;
  const bgColor = statusBgColors[status] || statusBgColors.safe;

  return (
    <div className="w-full">
      {/* 라벨과 값 */}
      <div className="flex justify-between items-baseline mb-1">
        <span className="text-sm font-medium text-gray-700">
          {labels[nutrient]}
        </span>
        <div className="text-right">
          <span className="text-lg font-bold text-gray-900">{percentage}%</span>
          {showValue && (
            <span className="text-xs text-gray-500 ml-1">
              ({value}{units[nutrient]})
            </span>
          )}
        </div>
      </div>

      {/* 게이지 바 */}
      <div className={`w-full h-3 rounded-full ${bgColor} overflow-hidden`}>
        <div
          className={`h-full rounded-full ${color} gauge-bar transition-all duration-500`}
          style={{ width: `${barWidth}%` }}
        />
      </div>
    </div>
  );
}

/**
 * 컴팩트 게이지 (검색 결과용)
 */
export function GaugeCompact({ nutrient, percentage, status }) {
  const color = statusColors[status] || statusColors.safe;
  const bgColor = statusBgColors[status] || statusBgColors.safe;

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-gray-600 w-12">{labels[nutrient]}</span>
      <div className={`flex-1 h-2 rounded-full ${bgColor} overflow-hidden`}>
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
      <span className="text-xs font-medium text-gray-700 w-8 text-right">
        {percentage}%
      </span>
    </div>
  );
}

/**
 * 원형 게이지 (대시보드용)
 */
export function GaugeCircle({ nutrient, percentage, status, size = 80 }) {
  const color = statusColors[status] || statusColors.safe;
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (Math.min(percentage, 100) / 100) * circumference;

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg className="transform -rotate-90" width={size} height={size}>
          {/* 배경 원 */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="#e5e7eb"
            strokeWidth="6"
          />
          {/* 진행 원 */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth="6"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className={color.replace('bg-', 'text-')}
            style={{ transition: 'stroke-dashoffset 0.5s ease-out' }}
          />
        </svg>
        {/* 중앙 텍스트 */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-lg font-bold text-gray-900">{percentage}%</span>
        </div>
      </div>
      <span className="text-xs text-gray-600 mt-1">{labels[nutrient]}</span>
    </div>
  );
}
