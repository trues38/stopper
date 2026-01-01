/**
 * Search 페이지 - 식품 검색
 */
import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import useStore from '../store/useStore';
import { searchFoods } from '../api/food';
import { FoodListItem, FoodCardSkeleton } from '../components/FoodCard';
import debounce from '../utils/debounce';

export default function Search() {
  const navigate = useNavigate();
  const { settings, getPercentage, getStatus } = useStore();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  // 검색 실행 (디바운스)
  const doSearch = useCallback(
    debounce(async (q) => {
      if (q.length < 2) {
        setResults([]);
        setHasSearched(false);
        return;
      }

      setIsLoading(true);
      try {
        const data = await searchFoods(q);
        setResults(data.items || []);
        setHasSearched(true);
      } catch (err) {
        console.error('검색 실패:', err);
        setResults([]);
      } finally {
        setIsLoading(false);
      }
    }, 300),
    []
  );

  const handleInput = (e) => {
    const value = e.target.value;
    setQuery(value);
    doSearch(value);
  };

  const handleSelect = (food) => {
    navigate(`/result/${food.id}`);
  };

  // % 계산
  const calculatePercentages = (food) => ({
    calories: getPercentage('calories', food.calories),
    protein: getPercentage('protein', food.protein),
    sugar: getPercentage('sugar', food.sugar),
    sodium: getPercentage('sodium', food.sodium),
  });

  const calculateStatus = (percentages) => ({
    calories: getStatus('calories', percentages.calories),
    protein: getStatus('protein', percentages.protein),
    sugar: getStatus('sugar', percentages.sugar),
    sodium: getStatus('sodium', percentages.sodium),
  });

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 검색 헤더 */}
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-lg mx-auto px-4 py-3">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate(-1)}
              className="text-gray-600 hover:text-gray-900"
            >
              ←
            </button>
            <div className="flex-1 relative">
              <input
                type="text"
                value={query}
                onChange={handleInput}
                placeholder="식품명으로 검색 (예: 삼각김밥)"
                className="w-full px-4 py-3 bg-gray-100 rounded-xl
                          focus:outline-none focus:ring-2 focus:ring-red-500
                          placeholder-gray-400"
                autoFocus
              />
              {query && (
                <button
                  onClick={() => {
                    setQuery('');
                    setResults([]);
                    setHasSearched(false);
                  }}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"
                >
                  ✕
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-lg mx-auto px-4 py-4">
        {/* 로딩 상태 */}
        {isLoading && (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <FoodCardSkeleton key={i} />
            ))}
          </div>
        )}

        {/* 검색 결과 */}
        {!isLoading && results.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm text-gray-500 mb-3">
              {results.length}개 결과
            </p>
            {results.map((food) => {
              const percentages = calculatePercentages(food);
              const status = calculateStatus(percentages);
              return (
                <FoodListItem
                  key={food.id}
                  food={food}
                  percentages={percentages}
                  status={status}
                  onClick={() => handleSelect(food)}
                />
              );
            })}
          </div>
        )}

        {/* 결과 없음 */}
        {!isLoading && hasSearched && results.length === 0 && (
          <div className="text-center py-12">
            <p className="text-4xl mb-3">🔍</p>
            <p className="text-gray-500">
              "{query}"에 대한 결과가 없어요
            </p>
            <p className="text-gray-400 text-sm mt-1">
              다른 검색어로 시도해보세요
            </p>
          </div>
        )}

        {/* 초기 상태 */}
        {!isLoading && !hasSearched && (
          <div className="text-center py-12">
            <p className="text-4xl mb-3">🍙</p>
            <p className="text-gray-500">
              편의점 음식, 과자, 음료 등<br />
              무엇이든 검색해보세요
            </p>

            {/* 인기 검색어 */}
            <div className="mt-8">
              <p className="text-sm text-gray-400 mb-3">인기 검색어</p>
              <div className="flex flex-wrap justify-center gap-2">
                {['삼각김밥', '프로틴바', '제로콜라', '닭가슴살', '초코파이'].map((word) => (
                  <button
                    key={word}
                    onClick={() => {
                      setQuery(word);
                      doSearch(word);
                    }}
                    className="px-3 py-1.5 bg-white rounded-full text-sm text-gray-600
                              border border-gray-200 hover:border-red-300 hover:text-red-500
                              transition-colors"
                  >
                    {word}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
