/**
 * Recommendations 페이지 - 카테고리별 추천 제품
 */
import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import useStore from '../store/useStore';
import { getRecommendationCategories, getRecommendations } from '../api/food';

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

const goalDescriptions = {
  diet: '칼로리가 낮은 제품',
  bulk: '단백질이 높은 제품',
  maintain: '나트륨이 낮은 제품',
  diabetes: '당류가 낮은 제품',
};

export default function Recommendations() {
  const navigate = useNavigate();
  const { settings } = useStore();
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingProducts, setLoadingProducts] = useState(false);

  // 카테고리 목록 로드
  useEffect(() => {
    loadCategories();
  }, []);

  async function loadCategories() {
    try {
      setLoading(true);
      const data = await getRecommendationCategories();
      setCategories(data.categories || []);
    } catch (error) {
      console.error('카테고리 로드 실패:', error);
    } finally {
      setLoading(false);
    }
  }

  // 카테고리 클릭 시 추천 제품 로드
  async function handleCategoryClick(category) {
    if (selectedCategory?.name === category.name) {
      setSelectedCategory(null);
      setRecommendations([]);
      return;
    }

    setSelectedCategory(category);
    setLoadingProducts(true);

    try {
      const data = await getRecommendations(category.name, {
        goal: settings.goalType,
        limit: 10,
        convenience_only: true,
      });
      setRecommendations(data.products || []);
    } catch (error) {
      console.error('추천 제품 로드 실패:', error);
      setRecommendations([]);
    } finally {
      setLoadingProducts(false);
    }
  }

  // 제품 클릭 시 스캔 페이지로 이동
  function handleProductClick(product) {
    navigate(`/result/${product.id}`);
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-24">
      {/* 헤더 */}
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-lg mx-auto px-4 py-4">
          <div className="flex items-center gap-3 mb-2">
            <Link to="/" className="text-gray-400 hover:text-gray-600">
              ←
            </Link>
            <h1 className="text-xl font-black text-gray-900">
              추천 제품
            </h1>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-2xl">{goalEmojis[settings.goalType]}</span>
            <div>
              <p className="font-medium text-gray-900">{goalLabels[settings.goalType]}</p>
              <p className="text-xs text-gray-500">{goalDescriptions[settings.goalType]} 순으로 보여줍니다</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-lg mx-auto px-4 py-6">
        {/* 로딩 */}
        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin text-4xl mb-4">⏳</div>
            <p className="text-gray-500">카테고리 불러오는 중...</p>
          </div>
        ) : (
          <>
            {/* 카테고리 목록 */}
            <section className="mb-6">
              <h2 className="font-bold text-gray-900 mb-3">카테고리 선택</h2>
              <div className="grid grid-cols-2 gap-3">
                {categories.slice(0, 20).map((category) => (
                  <button
                    key={category.name}
                    onClick={() => handleCategoryClick(category)}
                    className={`
                      p-4 rounded-xl text-left transition-all
                      ${selectedCategory?.name === category.name
                        ? 'bg-red-500 text-white shadow-lg scale-105'
                        : 'bg-white text-gray-900 hover:shadow-md hover:scale-102'
                      }
                    `}
                  >
                    <p className="font-bold text-sm mb-1">{category.name}</p>
                    <p className={`text-xs ${selectedCategory?.name === category.name ? 'text-red-100' : 'text-gray-500'}`}>
                      {category.food_count}개 제품
                    </p>
                    {category.benchmarks && (
                      <div className={`text-xs mt-2 ${selectedCategory?.name === category.name ? 'text-red-100' : 'text-gray-600'}`}>
                        평균 단백질: {category.benchmarks.avg_protein}g
                      </div>
                    )}
                  </button>
                ))}
              </div>
            </section>

            {/* 추천 제품 목록 */}
            {selectedCategory && (
              <section className="mt-6">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="font-bold text-gray-900">
                    {selectedCategory.name} 추천 제품
                  </h2>
                  <span className="text-xs text-gray-500">
                    {settings.goalType === 'bulk' && '단백질 높은 순'}
                    {settings.goalType === 'diet' && '칼로리 낮은 순'}
                    {settings.goalType === 'diabetes' && '당류 낮은 순'}
                    {settings.goalType === 'maintain' && '나트륨 낮은 순'}
                  </span>
                </div>

                {loadingProducts ? (
                  <div className="text-center py-8">
                    <div className="animate-spin text-3xl mb-2">⏳</div>
                    <p className="text-sm text-gray-500">추천 제품 찾는 중...</p>
                  </div>
                ) : recommendations.length === 0 ? (
                  <div className="bg-white rounded-xl p-8 text-center text-gray-400">
                    <p className="text-3xl mb-2">😢</p>
                    <p>추천 제품이 없습니다</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {recommendations.map((product, index) => (
                      <button
                        key={product.id}
                        onClick={() => handleProductClick(product)}
                        className="w-full bg-white rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow text-left"
                      >
                        <div className="flex items-start gap-3">
                          {/* 순위 뱃지 */}
                          <div className={`
                            flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm
                            ${index === 0 ? 'bg-yellow-100 text-yellow-700' :
                              index === 1 ? 'bg-gray-100 text-gray-700' :
                              index === 2 ? 'bg-orange-100 text-orange-700' :
                              'bg-gray-50 text-gray-500'}
                          `}>
                            {index + 1}
                          </div>

                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-gray-900 truncate mb-1">
                              {product.name}
                            </p>
                            {product.manufacturer && (
                              <p className="text-xs text-gray-400 mb-2">
                                {product.manufacturer}
                              </p>
                            )}

                            {/* 영양 정보 */}
                            <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs">
                              <span className="text-gray-600">
                                {product.calories}kcal
                              </span>
                              <span className={settings.goalType === 'bulk' ? 'text-red-600 font-bold' : 'text-gray-600'}>
                                단백질 {product.protein}g
                              </span>
                              <span className={settings.goalType === 'diabetes' ? 'text-orange-600 font-bold' : 'text-gray-600'}>
                                당 {product.sugar}g
                              </span>
                              <span className={settings.goalType === 'maintain' ? 'text-blue-600 font-bold' : 'text-gray-600'}>
                                나트륨 {product.sodium}mg
                              </span>
                            </div>

                            {product.serving_size && (
                              <p className="text-xs text-gray-400 mt-1">
                                {product.serving_size}
                              </p>
                            )}
                          </div>

                          {/* 화살표 */}
                          <div className="flex-shrink-0 text-gray-300">
                            →
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </section>
            )}

            {/* 안내 메시지 */}
            {!selectedCategory && (
              <div className="mt-8 bg-gradient-to-r from-red-50 to-orange-50 rounded-xl p-4 border border-red-100">
                <p className="text-sm text-gray-700 font-medium mb-2">
                  💡 추천 제품 보는 법
                </p>
                <ul className="text-xs text-gray-600 space-y-1">
                  <li>• 카테고리를 선택하면 목표에 맞는 제품을 추천해드려요</li>
                  <li>• 편의점에서 쉽게 구할 수 있는 제품 위주로 보여줍니다</li>
                  <li>• 제품을 클릭하면 자세한 영양 정보를 볼 수 있어요</li>
                </ul>
              </div>
            )}
          </>
        )}
      </main>

      {/* 하단 네비게이션 */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 safe-area-pb">
        <div className="max-w-lg mx-auto px-4 py-3 flex justify-around">
          <Link to="/" className="flex flex-col items-center text-gray-400 hover:text-gray-600">
            <span className="text-xl">🏠</span>
            <span className="text-xs">홈</span>
          </Link>
          <Link to="/search" className="flex flex-col items-center text-gray-400 hover:text-gray-600">
            <span className="text-xl">🔍</span>
            <span className="text-xs">검색</span>
          </Link>
          <Link to="/recommendations" className="flex flex-col items-center text-red-500">
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
