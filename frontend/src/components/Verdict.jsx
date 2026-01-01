/**
 * Verdict 컴포넌트 - STOPPER 메시지 시스템
 */
import React from 'react';

/**
 * 판정 레벨 결정 (이모지 기반)
 */
function getVerdictLevel(verdict) {
  if (verdict.includes('👍')) return 'excellent';
  if (verdict.includes('✅')) return 'good';
  if (verdict.includes('⚠️')) return 'caution';
  if (verdict.includes('🛑') || verdict.includes('❌')) return 'stop';
  return 'ok';
}

const verdictConfig = {
  excellent: {
    color: 'text-emerald-600',
    bg: 'bg-emerald-50',
    border: 'border-emerald-200',
  },
  good: {
    color: 'text-blue-600',
    bg: 'bg-blue-50',
    border: 'border-blue-200',
  },
  ok: {
    color: 'text-gray-600',
    bg: 'bg-gray-50',
    border: 'border-gray-200',
  },
  caution: {
    color: 'text-orange-600',
    bg: 'bg-orange-50',
    border: 'border-orange-200',
  },
  stop: {
    color: 'text-red-600',
    bg: 'bg-red-50',
    border: 'border-red-200',
  },
};

/**
 * 마크다운 볼드 처리
 */
function renderText(text) {
  if (!text) return text;
  // **텍스트** → <strong>텍스트</strong>
  return text.split(/(\*\*.*?\*\*)/).map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} className="font-bold">{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

export default function Verdict({ messages, mealType, proteinCapped }) {
  if (!messages) return null;

  const { overall, protein, calorie, sugar } = messages;

  // 종합 판정 레벨
  const overallLevel = getVerdictLevel(overall || '');
  const config = verdictConfig[overallLevel];

  return (
    <div className={`rounded-2xl p-5 ${config.bg} border-2 ${config.border}`}>
      {/* 종합 판정 */}
      <div className="mb-4">
        <h2 className={`text-xl font-bold ${config.color} mb-1`}>
          {renderText(overall)}
        </h2>
        {mealType && (
          <p className="text-xs text-gray-500">
            {mealType === 'MEAL' && '식사'}
            {mealType === 'LIQUID' && '음료'}
            {mealType === 'SINGLE_PROTEIN' && '단백질'}
            {mealType === 'SNACK' && '간식'}
          </p>
        )}
      </div>

      {/* 상세 판정 */}
      <div className="space-y-3">
        {/* 단백질 */}
        {protein && (
          <div className="bg-white/60 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-base font-bold">{protein.verdict}</span>
              {proteinCapped && (
                <span className="text-xs px-2 py-0.5 bg-yellow-100 text-yellow-700 rounded-full">
                  현실 기준
                </span>
              )}
            </div>
            <p className="text-sm text-gray-700 mb-1">{renderText(protein.detail)}</p>
            <p className="text-xs text-gray-500">{renderText(protein.percentage)}</p>
          </div>
        )}

        {/* 칼로리 */}
        {calorie && (
          <div className="bg-white/60 rounded-lg p-3">
            <p className="text-base font-bold mb-1">{calorie.verdict}</p>
            <p className="text-sm text-gray-700 mb-1">{calorie.detail}</p>
            <p className="text-xs text-gray-500">{renderText(calorie.percentage)}</p>
          </div>
        )}

        {/* 당류 */}
        {sugar && (
          <div className="bg-white/60 rounded-lg p-3">
            <p className="text-base font-bold mb-1">{sugar.verdict}</p>
            <p className="text-sm text-gray-700 mb-1">{sugar.detail}</p>
            <p className="text-xs text-gray-500">{renderText(sugar.percentage)}</p>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * 미니 버전 (리스트용)
 */
export function VerdictBadge({ overall }) {
  if (!overall) return null;

  const level = getVerdictLevel(overall);
  const config = verdictConfig[level];

  // 이모지 추출
  const emoji = overall.match(/[\u{1F300}-\u{1F9FF}]/u)?.[0] || '';
  const text = overall.replace(/[\u{1F300}-\u{1F9FF}]/gu, '').trim().substring(0, 15);

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${config.bg} ${config.color}`}>
      {emoji && <span>{emoji}</span>}
      <span>{text}</span>
    </span>
  );
}
