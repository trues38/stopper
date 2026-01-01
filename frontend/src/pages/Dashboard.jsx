/**
 * Dashboard 페이지 - 오늘의 현황
 */
import React from 'react';
import { Link } from 'react-router-dom';
import useStore from '../store/useStore';
import { GaugeCircle } from '../components/Gauge';

const goalEmojis = {
  diet: '🥗',
  bulk: '💪',
  maintain: '⚖️',
  diabetes: '💉',
};

const goalLabels = {
  diet: '다이어트',
  bulk: '벌크업',
  maintain: '균형 유지',
  diabetes: '당뇨 관리',
};

export default function Dashboard() {
  const { settings, todayTotals, todayRecords, getPercentage, getStatus, removeRecord } = useStore();

  const percentages = {
    calories: getPercentage('calories', todayTotals.calories),
    protein: getPercentage('protein', todayTotals.protein),
    sugar: getPercentage('sugar', todayTotals.sugar),
    sodium: getPercentage('sodium', todayTotals.sodium),
  };

  const statuses = {
    calories: getStatus('calories', percentages.calories),
    protein: getStatus('protein', percentages.protein),
    sugar: getStatus('sugar', percentages.sugar),
    sodium: getStatus('sodium', percentages.sodium),
  };

  return (
    <div className="min-h-screen bg-gray-50 pb-24">
      {/* 헤더 */}
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-lg mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-black text-gray-900">
              STOP<span className="text-red-500">%</span>
            </h1>
            <p className="text-xs text-gray-500">
              {goalEmojis[settings.goalType]} {goalLabels[settings.goalType]}
            </p>
          </div>
          <Link
            to="/search"
            className="bg-red-500 text-white px-4 py-2 rounded-full font-medium
                       shadow-md hover:bg-red-600 transition-colors flex items-center gap-2"
          >
            <span>🔍</span>
            <span>스캔</span>
          </Link>
        </div>
      </header>

      <main className="max-w-lg mx-auto px-4 py-6">
        {/* 오늘의 % */}
        <section className="bg-white rounded-2xl p-6 shadow-sm mb-6">
          <h2 className="font-bold text-gray-900 mb-4">오늘 먹은 양</h2>

          <div className="grid grid-cols-4 gap-4">
            <GaugeCircle
              nutrient="calories"
              percentage={percentages.calories}
              status={statuses.calories}
            />
            <GaugeCircle
              nutrient="protein"
              percentage={percentages.protein}
              status={statuses.protein}
            />
            <GaugeCircle
              nutrient="sugar"
              percentage={percentages.sugar}
              status={statuses.sugar}
            />
            <GaugeCircle
              nutrient="sodium"
              percentage={percentages.sodium}
              status={statuses.sodium}
            />
          </div>

          {/* 요약 문구 */}
          <div className="mt-4 text-center text-sm text-gray-600">
            {todayRecords.length === 0 ? (
              <p>아직 기록이 없어요. 첫 식품을 스캔해보세요!</p>
            ) : percentages.calories > 80 ? (
              <p>오늘 칼로리 거의 다 찼어요! 🛑</p>
            ) : percentages.sugar > 50 ? (
              <p>당류 섭취에 주의하세요 ⚠️</p>
            ) : (
              <p>잘 하고 있어요! 👍</p>
            )}
          </div>
        </section>

        {/* 오늘의 기록 */}
        <section>
          <div className="flex justify-between items-center mb-3">
            <h2 className="font-bold text-gray-900">오늘의 기록</h2>
            <span className="text-sm text-gray-500">{todayRecords.length}개</span>
          </div>

          {todayRecords.length === 0 ? (
            <div className="bg-white rounded-xl p-8 text-center text-gray-400">
              <p className="text-3xl mb-2">🍽️</p>
              <p>아직 기록이 없어요</p>
            </div>
          ) : (
            <div className="space-y-2">
              {todayRecords.map((record, index) => (
                <div
                  key={index}
                  className="bg-white rounded-xl p-4 shadow-sm flex items-center gap-3"
                >
                  <div className="flex-1">
                    <p className="font-medium text-gray-900">{record.name}</p>
                    <p className="text-xs text-gray-500">
                      {record.calories}kcal · 단백질 {record.protein}g · 당 {record.sugar}g
                    </p>
                  </div>
                  <button
                    onClick={() => removeRecord(index)}
                    className="text-gray-400 hover:text-red-500 transition-colors p-1"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* 추천 조합 (v2) */}
        <section className="mt-8">
          <div className="flex justify-between items-center mb-3">
            <h2 className="font-bold text-gray-900">추천 조합</h2>
            <Link to="/combos" className="text-sm text-red-500">
              더보기 →
            </Link>
          </div>

          <div className="bg-gradient-to-r from-red-50 to-orange-50 rounded-xl p-4 border border-red-100">
            <p className="text-sm text-gray-600">
              🎯 {goalLabels[settings.goalType]} 목표에 맞는 조합을 추천받아보세요
            </p>
          </div>
        </section>
      </main>

      {/* 하단 네비게이션 */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 safe-area-pb">
        <div className="max-w-lg mx-auto px-4 py-3 flex justify-around">
          <Link to="/" className="flex flex-col items-center text-red-500">
            <span className="text-xl">🏠</span>
            <span className="text-xs">홈</span>
          </Link>
          <Link to="/search" className="flex flex-col items-center text-gray-400 hover:text-gray-600">
            <span className="text-xl">🔍</span>
            <span className="text-xs">검색</span>
          </Link>
          <Link to="/recommendations" className="flex flex-col items-center text-gray-400 hover:text-gray-600">
            <span className="text-xl">⭐</span>
            <span className="text-xs">추천</span>
          </Link>
          <Link to="/combos" className="flex flex-col items-center text-gray-400 hover:text-gray-600">
            <span className="text-xl">📦</span>
            <span className="text-xs">조합</span>
          </Link>
          <Link to="/settings" className="flex flex-col items-center text-gray-400 hover:text-gray-600">
            <span className="text-xl">⚙️</span>
            <span className="text-xs">설정</span>
          </Link>
        </div>
      </nav>
    </div>
  );
}
