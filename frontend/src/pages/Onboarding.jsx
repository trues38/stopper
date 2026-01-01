/**
 * Onboarding 페이지 - 목표 선택
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import useStore from '../store/useStore';

const goals = [
  {
    id: 'diet',
    emoji: '🥗',
    title: '다이어트',
    desc: '칼로리와 당류를 줄이고 싶어요',
    color: 'from-green-400 to-emerald-500',
  },
  {
    id: 'bulk',
    emoji: '💪',
    title: '벌크업',
    desc: '단백질 위주로 챙기고 싶어요',
    color: 'from-blue-400 to-indigo-500',
  },
  {
    id: 'maintain',
    emoji: '⚖️',
    title: '유지',
    desc: '균형 잡힌 식단을 원해요',
    color: 'from-purple-400 to-pink-500',
  },
  {
    id: 'diabetes',
    emoji: '💉',
    title: '당뇨 관리',
    desc: '당류와 나트륨을 조절해야 해요',
    color: 'from-orange-400 to-red-500',
  },
];

export default function Onboarding() {
  const navigate = useNavigate();
  const completeOnboarding = useStore((s) => s.completeOnboarding);

  const handleSelect = (goalId) => {
    completeOnboarding(goalId);
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white p-6 flex flex-col">
      {/* 로고 영역 */}
      <div className="text-center py-8">
        <h1 className="text-4xl font-black text-gray-900 tracking-tight">
          STOP<span className="text-red-500">%</span>
        </h1>
        <p className="text-gray-500 mt-2">멈추면 보이는 한 끼의 %</p>
      </div>

      {/* 질문 */}
      <div className="text-center mb-8">
        <h2 className="text-xl font-bold text-gray-900">
          어떤 목표를 가지고 계신가요?
        </h2>
        <p className="text-gray-500 text-sm mt-1">
          선택에 따라 % 기준이 달라져요
        </p>
      </div>

      {/* 목표 카드들 */}
      <div className="flex-1 grid grid-cols-2 gap-4 max-w-lg mx-auto w-full">
        {goals.map((goal) => (
          <button
            key={goal.id}
            onClick={() => handleSelect(goal.id)}
            className={`bg-gradient-to-br ${goal.color} p-5 rounded-2xl text-white
                       shadow-lg hover:shadow-xl transition-all hover:scale-105
                       flex flex-col items-center justify-center text-center
                       active:scale-95`}
          >
            <span className="text-4xl mb-2">{goal.emoji}</span>
            <span className="font-bold text-lg">{goal.title}</span>
            <span className="text-xs opacity-80 mt-1">{goal.desc}</span>
          </button>
        ))}
      </div>

      {/* 하단 안내 */}
      <p className="text-center text-xs text-gray-400 mt-8">
        언제든 설정에서 변경할 수 있어요
      </p>
    </div>
  );
}
