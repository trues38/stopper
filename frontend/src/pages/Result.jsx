/**
 * Result 페이지 - 스캔 결과
 */
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import useStore from '../store/useStore';
import { scanFood } from '../api/food';
import Gauge from '../components/Gauge';
import Verdict from '../components/Verdict';

export default function Result() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { settings, addRecord, getPercentage, getStatus } = useStore();

  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [quantity, setQuantity] = useState(1);

  useEffect(() => {
    const fetchResult = async () => {
      try {
        const data = await scanFood(id, settings);
        setResult(data);
      } catch (err) {
        setError('스캔 실패');
      } finally {
        setIsLoading(false);
      }
    };
    fetchResult();
  }, [id, settings]);

  const handleAddRecord = () => {
    if (!result?.food) return;

    addRecord({
      foodId: result.food.id,
      name: result.food.name,
      quantity,
      calories: result.food.calories,
      protein: result.food.protein,
      sugar: result.food.sugar,
      sodium: result.food.sodium,
    });

    navigate('/');
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin text-4xl mb-3">🔄</div>
          <p className="text-gray-500">스캔 중...</p>
        </div>
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-4xl mb-3">😵</p>
          <p className="text-gray-500">{error || '결과를 불러올 수 없어요'}</p>
          <button
            onClick={() => navigate(-1)}
            className="mt-4 text-red-500 underline"
          >
            돌아가기
          </button>
        </div>
      </div>
    );
  }

  const { food, percentages, messages, stopper_note } = result;

  // quantity에 따른 실제 값 계산
  const actualValues = {
    calories: Math.round(food.calories * quantity),
    protein: Math.round(food.protein_effective * quantity * 10) / 10,
    sugar: Math.round(food.sugar * quantity * 10) / 10,
    sodium: Math.round(food.sodium * quantity),
  };

  const actualPercentages = {
    calories: getPercentage('calories', actualValues.calories),
    protein: getPercentage('protein', actualValues.protein),
    sugar: getPercentage('sugar', actualValues.sugar),
    sodium: getPercentage('sodium', actualValues.sodium),
  };

  const actualStatuses = {
    calories: getStatus('calories', actualPercentages.calories),
    protein: getStatus('protein', actualPercentages.protein),
    sugar: getStatus('sugar', actualPercentages.sugar),
    sodium: getStatus('sodium', actualPercentages.sodium),
  };

  return (
    <div className="min-h-screen bg-gray-50 pb-24">
      {/* 헤더 */}
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-lg mx-auto px-4 py-4 flex items-center gap-3">
          <button
            onClick={() => navigate(-1)}
            className="text-gray-600 hover:text-gray-900"
          >
            ←
          </button>
          <h1 className="font-bold text-gray-900 flex-1 truncate">
            {food.name}
          </h1>
        </div>
      </header>

      <main className="max-w-lg mx-auto px-4 py-6">
        {/* STOPPER 판정 */}
        <Verdict
          messages={messages}
          mealType={food.meal_type}
          proteinCapped={stopper_note?.protein_capped}
        />

        {/* 수량 조절 */}
        <div className="bg-white rounded-xl p-4 mt-4 flex items-center justify-between">
          <span className="text-gray-700">수량</span>
          <div className="flex items-center gap-4">
            <button
              onClick={() => setQuantity(Math.max(0.5, quantity - 0.5))}
              className="w-10 h-10 rounded-full bg-gray-100 text-xl
                        hover:bg-gray-200 transition-colors"
            >
              −
            </button>
            <span className="text-xl font-bold w-12 text-center">{quantity}</span>
            <button
              onClick={() => setQuantity(quantity + 0.5)}
              className="w-10 h-10 rounded-full bg-gray-100 text-xl
                        hover:bg-gray-200 transition-colors"
            >
              +
            </button>
          </div>
        </div>

        {/* 영양성분 게이지 */}
        <div className="bg-white rounded-xl p-5 mt-4 space-y-4">
          <h3 className="font-bold text-gray-900 mb-2">영양성분</h3>

          <Gauge
            nutrient="calories"
            value={actualValues.calories}
            percentage={actualPercentages.calories}
            status={actualStatuses.calories}
          />
          <Gauge
            nutrient="protein"
            value={actualValues.protein}
            percentage={actualPercentages.protein}
            status={actualStatuses.protein}
          />
          <Gauge
            nutrient="sugar"
            value={actualValues.sugar}
            percentage={actualPercentages.sugar}
            status={actualStatuses.sugar}
          />
          <Gauge
            nutrient="sodium"
            value={actualValues.sodium}
            percentage={actualPercentages.sodium}
            status={actualStatuses.sodium}
          />
        </div>

        {/* 식품 정보 */}
        <div className="bg-white rounded-xl p-4 mt-4">
          <h3 className="font-bold text-gray-900 mb-3">식품 정보</h3>
          <dl className="space-y-2 text-sm">
            {food.manufacturer && (
              <div className="flex justify-between">
                <dt className="text-gray-500">제조사</dt>
                <dd className="text-gray-900">{food.manufacturer}</dd>
              </div>
            )}
            {food.category_large && (
              <div className="flex justify-between">
                <dt className="text-gray-500">분류</dt>
                <dd className="text-gray-900">
                  {food.category_large}
                  {food.category_medium && ` > ${food.category_medium}`}
                </dd>
              </div>
            )}
            {food.serving_size && (
              <div className="flex justify-between">
                <dt className="text-gray-500">1회 섭취량</dt>
                <dd className="text-gray-900">{food.serving_size}</dd>
              </div>
            )}
            {stopper_note?.protein_capped && (
              <div className="flex justify-between items-start mt-3 pt-3 border-t">
                <dt className="text-gray-500">단백질</dt>
                <dd className="text-gray-900 text-right">
                  <div className="flex items-center gap-2">
                    <span className="line-through text-gray-400">{food.protein_raw}g</span>
                    <span className="font-bold text-emerald-600">{food.protein_effective}g</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    {stopper_note.protein_cap_reason}
                  </p>
                </dd>
              </div>
            )}
          </dl>
        </div>
      </main>

      {/* 하단 버튼 */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 p-4 safe-area-pb">
        <div className="max-w-lg mx-auto">
          <button
            onClick={handleAddRecord}
            className="w-full py-4 bg-red-500 text-white font-bold rounded-xl
                      hover:bg-red-600 transition-colors shadow-lg"
          >
            오늘 먹은 거에 추가 ✓
          </button>
        </div>
      </div>
    </div>
  );
}
