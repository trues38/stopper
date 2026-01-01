/**
 * Search 페이지 - 식품 검색
 */
import React, { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import useStore from '../store/useStore';
import { searchFoods, getCategories, scanBarcode } from '../api/food';
import { FoodListItem, FoodCardSkeleton } from '../components/FoodCard';
import BarcodeScanner from '../components/BarcodeScanner';
import debounce from '../utils/debounce';

export default function Search() {
  const navigate = useNavigate();
  const { settings, getPercentage, getStatus } = useStore();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [showBarcodeScanner, setShowBarcodeScanner] = useState(false);

  // 카테고리 목록 로드
  useEffect(() => {
    getCategories()
      .then(data => setCategories(data.categories || []))
      .catch(console.error);
  }, []);

  // 검색 실행
  const executeSearch = async (q, category) => {
    if (q.length < 2) {
      setResults([]);
      setHasSearched(false);
      return;
    }

    setIsLoading(true);
    try {
      const data = await searchFoods(q, { category, limit: 50 });
      setResults(data.items || []);
      setHasSearched(true);
    } catch (err) {
      console.error('검색 실패:', err);
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  };

  // 검색 실행 (디바운스)
  const doSearch = useCallback(
    debounce((q, category) => executeSearch(q, category), 300),
    []
  );

  // 카테고리 변경시 재검색
  const handleCategoryChange = (cat) => {
    const newCategory = selectedCategory === cat ? null : cat;
    setSelectedCategory(newCategory);
    if (query.length >= 2) {
      executeSearch(query, newCategory);
    }
  };

  const handleInput = (e) => {
    const value = e.target.value;
    setQuery(value);
    doSearch(value, selectedCategory);
  };

  const handleSelect = (food) => {
    navigate(`/result/${food.id}`);
  };

  const handleBarcodeScan = async (barcode) => {
    setShowBarcodeScanner(false);
    setIsLoading(true);

    try {
      const data = await scanBarcode(barcode, settings);

      // STOPPER DB에 있는 제품이면 ID로 이동
      if (data.source === 'stopper_db' || data.source === 'matched') {
        navigate(`/result/${data.food.id}`);
      } else {
        // Open Food Facts 제품은 바코드 결과 페이지로
        navigate('/barcode-result', { state: { data, barcode } });
      }
    } catch (err) {
      console.error('바코드 스캔 실패:', err);

      // 바코드를 찾을 수 없는 경우 → 등록 화면으로
      const confirmRegister = confirm(
        '이 바코드는 등록되지 않은 제품입니다.\n직접 등록하시겠습니까?'
      );

      if (confirmRegister) {
        navigate('/product-register', { state: { barcode } });
      }
    } finally {
      setIsLoading(false);
    }
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
                    setSelectedCategory(null);
                  }}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"
                >
                  ✕
                </button>
              )}
            </div>
            <button
              onClick={() => setShowBarcodeScanner(true)}
              className="p-3 bg-red-500 text-white rounded-xl hover:bg-red-600
                        transition-colors text-xl"
              title="바코드 스캔"
            >
              📷
            </button>
          </div>
        </div>

        {/* 카테고리 필터 */}
        {categories.length > 0 && (
          <div className="mt-2 -mx-4 px-4 overflow-x-auto scrollbar-hide">
            <div className="flex gap-2 pb-1" style={{ width: 'max-content' }}>
              <button
                onClick={() => handleCategoryChange(null)}
                className={`px-3 py-1 rounded-full text-sm whitespace-nowrap transition-colors
                  ${!selectedCategory
                    ? 'bg-red-500 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
              >
                전체
              </button>
              {categories.slice(0, 10).map((cat) => (
                <button
                  key={cat.name}
                  onClick={() => handleCategoryChange(cat.name)}
                  className={`px-3 py-1 rounded-full text-sm whitespace-nowrap transition-colors
                    ${selectedCategory === cat.name
                      ? 'bg-red-500 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
                >
                  {cat.name}
                </button>
              ))}
            </div>
          </div>
        )}
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
                      doSearch(word, selectedCategory);
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

      {/* 바코드 스캐너 모달 */}
      {showBarcodeScanner && (
        <BarcodeScanner
          onScan={handleBarcodeScan}
          onClose={() => setShowBarcodeScanner(false)}
        />
      )}
    </div>
  );
}
