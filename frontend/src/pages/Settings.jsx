/**
 * Settings 페이지 - 사용자 목표 설정
 */
import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import useStore from '../store/useStore';

const goalOptions = [
  { id: 'diet', emoji: '🥗', label: '다이어트', desc: '칼로리/당류 제한' },
  { id: 'bulk', emoji: '💪', label: '벌크업', desc: '단백질 위주' },
  { id: 'maintain', emoji: '⚖️', label: '유지', desc: '균형 잡힌 식단' },
  { id: 'diabetes', emoji: '💉', label: '당뇨관리', desc: '당류/나트륨 제한' },
];

const presets = {
  diet: { calorieGoal: 1500, proteinGoal: 60, sugarLimit: 25, sodiumLimit: 2000 },
  bulk: { calorieGoal: 2500, proteinGoal: 120, sugarLimit: 50, sodiumLimit: 2300 },
  maintain: { calorieGoal: 2000, proteinGoal: 60, sugarLimit: 50, sodiumLimit: 2000 },
  diabetes: { calorieGoal: 1800, proteinGoal: 60, sugarLimit: 20, sodiumLimit: 1500 },
};

export default function Settings() {
  const navigate = useNavigate();
  const { settings, updateSettings } = useStore();

  const [goalType, setGoalType] = useState(settings.goalType);
  const [calorieGoal, setCalorieGoal] = useState(settings.calorieGoal);
  const [proteinGoal, setProteinGoal] = useState(settings.proteinGoal);
  const [sugarLimit, setSugarLimit] = useState(settings.sugarLimit);
  const [sodiumLimit, setSodiumLimit] = useState(settings.sodiumLimit);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleGoalChange = (newGoal) => {
    setGoalType(newGoal);
    const preset = presets[newGoal];
    setCalorieGoal(preset.calorieGoal);
    setProteinGoal(preset.proteinGoal);
    setSugarLimit(preset.sugarLimit);
    setSodiumLimit(preset.sodiumLimit);
  };

  const handleSave = () => {
    updateSettings({
      goalType,
      calorieGoal,
      proteinGoal,
      sugarLimit,
      sodiumLimit,
    });
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-gray-50 pb-24">
      {/* 헤더 */}
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-lg mx-auto px-4 py-4 flex items-center gap-3">
          <button onClick={() => navigate(-1)} className="text-gray-600">
            ←
          </button>
          <h1 className="font-bold text-gray-900">목표 설정</h1>
        </div>
      </header>

      <main className="max-w-lg mx-auto px-4 py-6 space-y-6">
        {/* 목표 타입 선택 */}
        <section className="bg-white rounded-xl p-4">
          <h2 className="font-bold text-gray-900 mb-3">나의 목표</h2>
          <div className="grid grid-cols-2 gap-3">
            {goalOptions.map((goal) => (
              <button
                key={goal.id}
                onClick={() => handleGoalChange(goal.id)}
                className={`p-4 rounded-xl border-2 transition-all text-left
                  ${goalType === goal.id
                    ? 'border-red-500 bg-red-50'
                    : 'border-gray-200 hover:border-gray-300'}`}
              >
                <span className="text-2xl">{goal.emoji}</span>
                <p className="font-medium text-gray-900 mt-1">{goal.label}</p>
                <p className="text-xs text-gray-500">{goal.desc}</p>
              </button>
            ))}
          </div>
        </section>

        {/* 기본 설정 표시 */}
        <section className="bg-white rounded-xl p-4">
          <div className="flex justify-between items-center mb-3">
            <h2 className="font-bold text-gray-900">일일 목표</h2>
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-sm text-red-500"
            >
              {showAdvanced ? '접기' : '상세 설정'}
            </button>
          </div>

          {/* 요약 보기 */}
          {!showAdvanced && (
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-500">칼로리</p>
                <p className="text-lg font-bold text-gray-900">{calorieGoal}kcal</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-500">단백질</p>
                <p className="text-lg font-bold text-gray-900">{proteinGoal}g</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-500">당류 제한</p>
                <p className="text-lg font-bold text-gray-900">{sugarLimit}g</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-500">나트륨 제한</p>
                <p className="text-lg font-bold text-gray-900">{sodiumLimit}mg</p>
              </div>
            </div>
          )}

          {/* 상세 설정 */}
          {showAdvanced && (
            <div className="space-y-4">
              <div>
                <label className="text-sm text-gray-600 mb-1 block">
                  일일 칼로리 목표 (kcal)
                </label>
                <input
                  type="range"
                  min="1000"
                  max="4000"
                  step="100"
                  value={calorieGoal}
                  onChange={(e) => setCalorieGoal(Number(e.target.value))}
                  className="w-full accent-red-500"
                />
                <div className="flex justify-between text-xs text-gray-400">
                  <span>1000</span>
                  <span className="font-bold text-gray-900">{calorieGoal}</span>
                  <span>4000</span>
                </div>
              </div>

              <div>
                <label className="text-sm text-gray-600 mb-1 block">
                  일일 단백질 목표 (g)
                </label>
                <input
                  type="range"
                  min="30"
                  max="200"
                  step="5"
                  value={proteinGoal}
                  onChange={(e) => setProteinGoal(Number(e.target.value))}
                  className="w-full accent-red-500"
                />
                <div className="flex justify-between text-xs text-gray-400">
                  <span>30</span>
                  <span className="font-bold text-gray-900">{proteinGoal}</span>
                  <span>200</span>
                </div>
              </div>

              <div>
                <label className="text-sm text-gray-600 mb-1 block">
                  일일 당류 제한 (g)
                </label>
                <input
                  type="range"
                  min="10"
                  max="100"
                  step="5"
                  value={sugarLimit}
                  onChange={(e) => setSugarLimit(Number(e.target.value))}
                  className="w-full accent-red-500"
                />
                <div className="flex justify-between text-xs text-gray-400">
                  <span>10</span>
                  <span className="font-bold text-gray-900">{sugarLimit}</span>
                  <span>100</span>
                </div>
              </div>

              <div>
                <label className="text-sm text-gray-600 mb-1 block">
                  일일 나트륨 제한 (mg)
                </label>
                <input
                  type="range"
                  min="1000"
                  max="3000"
                  step="100"
                  value={sodiumLimit}
                  onChange={(e) => setSodiumLimit(Number(e.target.value))}
                  className="w-full accent-red-500"
                />
                <div className="flex justify-between text-xs text-gray-400">
                  <span>1000</span>
                  <span className="font-bold text-gray-900">{sodiumLimit}</span>
                  <span>3000</span>
                </div>
              </div>

              {/* 프리셋 리셋 버튼 */}
              <button
                onClick={() => handleGoalChange(goalType)}
                className="w-full py-2 text-sm text-gray-500 hover:text-gray-700"
              >
                기본값으로 초기화
              </button>
            </div>
          )}
        </section>

        {/* % 계산 방식 안내 */}
        <section className="bg-blue-50 rounded-xl p-4 border border-blue-100">
          <h3 className="font-medium text-blue-900 mb-2">💡 % 계산 방식</h3>
          <ul className="text-sm text-blue-800 space-y-1">
            <li>• 칼로리: 목표 대비 섭취 비율</li>
            <li>• 단백질: 목표 달성률 (높을수록 👍)</li>
            <li>• 당류/나트륨: 제한 대비 섭취 비율</li>
          </ul>
        </section>
      </main>

      {/* 저장 버튼 */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 p-4 safe-area-pb">
        <div className="max-w-lg mx-auto">
          <button
            onClick={handleSave}
            className="w-full py-4 bg-red-500 text-white font-bold rounded-xl
                      hover:bg-red-600 transition-colors shadow-lg"
          >
            저장하기
          </button>
        </div>
      </div>

      {/* 하단 네비게이션 */}
      <nav className="fixed bottom-16 left-0 right-0 bg-white border-t border-gray-200">
        <div className="max-w-lg mx-auto px-4 py-3 flex justify-around">
          <Link to="/" className="flex flex-col items-center text-gray-400">
            <span className="text-xl">🏠</span>
            <span className="text-xs">홈</span>
          </Link>
          <Link to="/search" className="flex flex-col items-center text-gray-400">
            <span className="text-xl">🔍</span>
            <span className="text-xs">검색</span>
          </Link>
          <Link to="/recommendations" className="flex flex-col items-center text-gray-400">
            <span className="text-xl">⭐</span>
            <span className="text-xs">추천</span>
          </Link>
          <Link to="/combos" className="flex flex-col items-center text-gray-400">
            <span className="text-xl">📦</span>
            <span className="text-xs">조합</span>
          </Link>
          <Link to="/settings" className="flex flex-col items-center text-red-500">
            <span className="text-xl">⚙️</span>
            <span className="text-xs">설정</span>
          </Link>
        </div>
      </nav>
    </div>
  );
}
