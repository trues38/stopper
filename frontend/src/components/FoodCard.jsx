/**
 * FoodCard 컴포넌트 - 식품 카드
 */
import React from 'react';
import { GaugeCompact } from './Gauge';

export default function FoodCard({ food, percentages, status, onClick }) {
  return (
    <div
      onClick={onClick}
      className="bg-white rounded-xl p-4 shadow-sm border border-gray-100
                 hover:shadow-md hover:border-gray-200 transition-all cursor-pointer
                 active:scale-[0.98]"
    >
      {/* 상단: 이름과 제조사 */}
      <div className="mb-3">
        <h3 className="font-semibold text-gray-900 line-clamp-1">
          {food.name}
        </h3>
        {food.manufacturer && (
          <p className="text-xs text-gray-500 mt-0.5">{food.manufacturer}</p>
        )}
      </div>

      {/* 게이지들 */}
      <div className="space-y-2">
        <GaugeCompact
          nutrient="calories"
          percentage={percentages?.calories || 0}
          status={status?.calories || 'safe'}
        />
        <GaugeCompact
          nutrient="protein"
          percentage={percentages?.protein || 0}
          status={status?.protein || 'low'}
        />
        <GaugeCompact
          nutrient="sugar"
          percentage={percentages?.sugar || 0}
          status={status?.sugar || 'safe'}
        />
      </div>

      {/* 1회 섭취량 */}
      {food.serving_size && (
        <p className="text-xs text-gray-400 mt-3 text-right">
          1회 {food.serving_size}
        </p>
      )}
    </div>
  );
}

/**
 * 스켈레톤 로딩
 */
export function FoodCardSkeleton() {
  return (
    <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 animate-pulse">
      <div className="h-5 bg-gray-200 rounded w-3/4 mb-2" />
      <div className="h-3 bg-gray-100 rounded w-1/2 mb-4" />
      <div className="space-y-3">
        <div className="h-2 bg-gray-100 rounded" />
        <div className="h-2 bg-gray-100 rounded" />
        <div className="h-2 bg-gray-100 rounded" />
      </div>
    </div>
  );
}

/**
 * 리스트 아이템 (검색 결과용)
 */
export function FoodListItem({ food, percentages, status, onClick }) {
  // 가장 높은 % 찾기
  const maxNutrient = Object.entries(percentages || {}).reduce(
    (max, [key, val]) => (val > max.value ? { key, value: val } : max),
    { key: 'calories', value: 0 }
  );

  const statusEmoji = {
    safe: '🟢',
    ok: '🟡',
    caution: '🟠',
    danger: '🔴',
    good: '🔵',
    low: '⚪',
  };

  return (
    <div
      onClick={onClick}
      className="flex items-center gap-3 p-3 bg-white rounded-lg border border-gray-100
                 hover:bg-gray-50 transition-colors cursor-pointer"
    >
      {/* 상태 이모지 */}
      <span className="text-xl">
        {statusEmoji[status?.[maxNutrient.key]] || '⚪'}
      </span>

      {/* 정보 */}
      <div className="flex-1 min-w-0">
        <p className="font-medium text-gray-900 truncate">{food.name}</p>
        <p className="text-xs text-gray-500">
          {food.calories}kcal · 단 {percentages?.protein || 0}% · 당 {percentages?.sugar || 0}%
        </p>
      </div>

      {/* 주요 % */}
      <div className="text-right">
        <span className="text-lg font-bold text-gray-900">
          {maxNutrient.value}%
        </span>
      </div>
    </div>
  );
}
