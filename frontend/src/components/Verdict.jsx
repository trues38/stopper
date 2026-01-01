/**
 * Verdict 컴포넌트 - 스캔 결과 판정
 */
import React from 'react';

const verdictConfig = {
  excellent: {
    emoji: '🎉',
    title: '완벽한 선택!',
    color: 'text-emerald-600',
    bg: 'bg-emerald-50',
    border: 'border-emerald-200',
  },
  good: {
    emoji: '👍',
    title: '좋은 선택',
    color: 'text-blue-600',
    bg: 'bg-blue-50',
    border: 'border-blue-200',
  },
  ok: {
    emoji: '🤔',
    title: '괜찮은 선택',
    color: 'text-yellow-600',
    bg: 'bg-yellow-50',
    border: 'border-yellow-200',
  },
  caution: {
    emoji: '⚠️',
    title: '주의 필요',
    color: 'text-orange-600',
    bg: 'bg-orange-50',
    border: 'border-orange-200',
  },
  stop: {
    emoji: '🛑',
    title: 'STOP!',
    color: 'text-red-600',
    bg: 'bg-red-50',
    border: 'border-red-200',
  },
};

/**
 * 판정 레벨 계산
 */
function getVerdictLevel(percentages, status) {
  const { calories, protein, sugar, sodium } = percentages;

  // 당류나 나트륨이 50% 초과 → STOP
  if (sugar > 50 || sodium > 50) return 'stop';

  // 칼로리가 40% 초과 → 주의
  if (calories > 40) return 'caution';

  // 당류가 30% 초과 → 주의
  if (sugar > 30) return 'caution';

  // 단백질이 높고 당류가 낮음 → excellent
  if (protein >= 20 && sugar <= 10) return 'excellent';

  // 모든 수치가 안전 → good
  if (calories <= 20 && sugar <= 15) return 'good';

  return 'ok';
}

/**
 * 상세 메시지 생성
 */
function getVerdictMessage(percentages, goalType) {
  const { calories, protein, sugar, sodium } = percentages;
  const messages = [];

  // 칼로리 관련
  if (calories <= 10) {
    messages.push('칼로리 부담 없이 즐겨도 좋아요');
  } else if (calories > 30) {
    messages.push(`한 끼 칼로리의 ${calories}%를 차지해요`);
  }

  // 단백질 관련
  if (protein >= 30) {
    messages.push('단백질이 풍부해요! 💪');
  } else if (protein < 5 && goalType === 'bulk') {
    messages.push('단백질이 부족해요');
  }

  // 당류 관련
  if (sugar > 30) {
    messages.push(`당류가 하루 권장량의 ${sugar}%예요`);
  } else if (sugar <= 5) {
    messages.push('당류 걱정 없어요');
  }

  // 나트륨 관련
  if (sodium > 40) {
    messages.push(`나트륨이 높아요 (${sodium}%)`);
  }

  return messages.length > 0 ? messages : ['균형 잡힌 선택이에요'];
}

export default function Verdict({ percentages, status, goalType = 'maintain' }) {
  const level = getVerdictLevel(percentages, status);
  const config = verdictConfig[level];
  const messages = getVerdictMessage(percentages, goalType);

  return (
    <div className={`rounded-2xl p-5 ${config.bg} border ${config.border}`}>
      {/* 헤더 */}
      <div className="flex items-center gap-3 mb-3">
        <span className="text-3xl">{config.emoji}</span>
        <h2 className={`text-xl font-bold ${config.color}`}>
          {config.title}
        </h2>
      </div>

      {/* 메시지 */}
      <ul className="space-y-1">
        {messages.map((msg, i) => (
          <li key={i} className="text-gray-700 text-sm flex items-start gap-2">
            <span className="text-gray-400">•</span>
            {msg}
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * 미니 버전 (리스트용)
 */
export function VerdictBadge({ percentages, status }) {
  const level = getVerdictLevel(percentages, status);
  const config = verdictConfig[level];

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${config.bg} ${config.color}`}>
      <span>{config.emoji}</span>
      <span>{config.title}</span>
    </span>
  );
}
