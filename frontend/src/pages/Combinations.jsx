/**
 * Combinations 페이지 - 조합 커뮤니티
 */
import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import useStore from '../store/useStore';
import { getCombinations, likeCombination } from '../api/food';

const goalLabels = {
  diet: '🥗 다이어트',
  bulk: '💪 벌크업',
  maintain: '⚖️ 균형유지',
  diabetes: '💉 당뇨관리',
};

export default function Combinations() {
  const navigate = useNavigate();
  const { settings, fingerprint } = useStore();
  const [combos, setCombos] = useState([]);
  const [filter, setFilter] = useState(settings.goalType);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchCombos = async () => {
      setIsLoading(true);
      try {
        const data = await getCombinations(filter);
        setCombos(data.items || []);
      } catch (err) {
        console.error('조합 로드 실패:', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchCombos();
  }, [filter]);

  const handleLike = async (comboId) => {
    try {
      await likeCombination(fingerprint, comboId);
      // 좋아요 수 업데이트
      setCombos((prev) =>
        prev.map((c) =>
          c.id === comboId ? { ...c, likes_count: c.likes_count + 1 } : c
        )
      );
    } catch (err) {
      console.error('좋아요 실패:', err);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 pb-24">
      {/* 헤더 */}
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-lg mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button onClick={() => navigate(-1)} className="text-gray-600">
                ←
              </button>
              <h1 className="font-bold text-gray-900">추천 조합</h1>
            </div>
          </div>

          {/* 필터 */}
          <div className="flex gap-2 mt-3 overflow-x-auto pb-2">
            {Object.entries(goalLabels).map(([key, label]) => (
              <button
                key={key}
                onClick={() => setFilter(key)}
                className={`px-3 py-1.5 rounded-full text-sm whitespace-nowrap transition-colors
                  ${
                    filter === key
                      ? 'bg-red-500 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </header>

      <main className="max-w-lg mx-auto px-4 py-4">
        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-white rounded-xl p-4 animate-pulse">
                <div className="h-5 bg-gray-200 rounded w-1/2 mb-2" />
                <div className="h-3 bg-gray-100 rounded w-3/4 mb-4" />
                <div className="flex gap-2">
                  <div className="h-8 bg-gray-100 rounded-full w-20" />
                  <div className="h-8 bg-gray-100 rounded-full w-20" />
                </div>
              </div>
            ))}
          </div>
        ) : combos.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-4xl mb-3">📦</p>
            <p className="text-gray-500">아직 조합이 없어요</p>
          </div>
        ) : (
          <div className="space-y-4">
            {combos.map((combo) => (
              <ComboCard
                key={combo.id}
                combo={combo}
                onLike={() => handleLike(combo.id)}
              />
            ))}
          </div>
        )}
      </main>

      {/* 하단 네비게이션 */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200">
        <div className="max-w-lg mx-auto px-4 py-3 flex justify-around">
          <Link to="/" className="flex flex-col items-center text-gray-400">
            <span className="text-xl">🏠</span>
            <span className="text-xs">홈</span>
          </Link>
          <Link to="/search" className="flex flex-col items-center text-gray-400">
            <span className="text-xl">🔍</span>
            <span className="text-xs">검색</span>
          </Link>
          <Link to="/combos" className="flex flex-col items-center text-red-500">
            <span className="text-xl">📦</span>
            <span className="text-xs">조합</span>
          </Link>
          <Link to="/settings" className="flex flex-col items-center text-gray-400">
            <span className="text-xl">⚙️</span>
            <span className="text-xs">설정</span>
          </Link>
        </div>
      </nav>
    </div>
  );
}

/**
 * 조합 카드 컴포넌트
 */
function ComboCard({ combo, onLike }) {
  const { result, items, tags, is_official } = combo;

  return (
    <div className="bg-white rounded-xl p-4 shadow-sm">
      {/* 헤더 */}
      <div className="flex items-start justify-between mb-2">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-bold text-gray-900">{combo.name}</h3>
            {is_official && (
              <span className="px-1.5 py-0.5 bg-red-100 text-red-600 text-xs rounded">
                공식
              </span>
            )}
          </div>
          {combo.description && (
            <p className="text-sm text-gray-500 mt-0.5">{combo.description}</p>
          )}
        </div>
      </div>

      {/* 아이템 목록 */}
      <div className="flex flex-wrap gap-1 mb-3">
        {items.map((item, i) => (
          <span
            key={i}
            className="px-2 py-1 bg-gray-100 rounded text-xs text-gray-600"
          >
            {item.name} {item.qty > 1 && `x${item.qty}`}
          </span>
        ))}
      </div>

      {/* 결과 영양정보 */}
      <div className="flex gap-4 text-sm text-gray-600 mb-3">
        <span>{result.calories}kcal</span>
        <span>단백질 {result.protein}g</span>
        <span>당류 {result.sugar}g</span>
      </div>

      {/* 태그와 좋아요 */}
      <div className="flex items-center justify-between">
        <div className="flex gap-1">
          {tags?.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="px-2 py-0.5 bg-gray-50 text-gray-500 text-xs rounded-full"
            >
              #{tag}
            </span>
          ))}
        </div>
        <button
          onClick={onLike}
          className="flex items-center gap-1 px-3 py-1.5 bg-gray-100 rounded-full
                    hover:bg-red-50 hover:text-red-500 transition-colors text-sm"
        >
          <span>❤️</span>
          <span>{combo.likes_count}</span>
        </button>
      </div>
    </div>
  );
}
