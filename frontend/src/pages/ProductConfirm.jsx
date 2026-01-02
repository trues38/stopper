import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { matchBarcode, quickRegisterBarcode } from '../api/food';

export default function ProductConfirm() {
  const location = useLocation();
  const navigate = useNavigate();
  const { barcode } = location.state || {};

  const [loading, setLoading] = useState(true);
  const [matchResult, setMatchResult] = useState(null);
  const [registering, setRegistering] = useState(false);

  useEffect(() => {
    if (!barcode) {
      alert('바코드 정보가 없습니다.');
      navigate('/search');
      return;
    }

    // 바코드 매칭
    const fetchMatch = async () => {
      try {
        const data = await matchBarcode(barcode);
        setMatchResult(data);

        if (!data.matched) {
          // 매칭 실패 → 수동 등록 화면으로
          const confirmManual = confirm(
            `식약처 DB: ${data.i2570_name}\n\n편의점 DB에서 이 제품을 찾을 수 없습니다.\n수동으로 등록하시겠습니까?`
          );

          if (confirmManual) {
            navigate('/product-register', { state: { barcode } });
          } else {
            navigate('/search');
          }
        }
      } catch (err) {
        console.error('매칭 실패:', err);
        alert('바코드 매칭에 실패했습니다.');
        navigate('/search');
      } finally {
        setLoading(false);
      }
    };

    fetchMatch();
  }, [barcode, navigate]);

  const handleConfirm = async () => {
    if (!matchResult || !matchResult.product) return;

    setRegistering(true);

    try {
      const result = await quickRegisterBarcode(barcode, matchResult.product);
      alert(result.message);
      navigate(`/result/${result.id}`);
    } catch (err) {
      alert('등록 실패: ' + err.message);
    } finally {
      setRegistering(false);
    }
  };

  const handleCancel = () => {
    navigate('/search');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 mx-auto mb-4"></div>
          <p className="text-gray-600">제품 정보 확인 중...</p>
        </div>
      </div>
    );
  }

  if (!matchResult || !matchResult.matched) {
    return null;
  }

  const { product, i2570_name, i2570_manufacturer } = matchResult;

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Header */}
      <div className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-4 flex items-center gap-3">
          <button onClick={handleCancel} className="text-2xl">
            ←
          </button>
          <h1 className="text-xl font-bold">제품 등록 확인</h1>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">
        {/* 바코드 정보 */}
        <div className="bg-green-50 border border-green-200 rounded-xl p-4">
          <p className="text-sm text-gray-600 mb-1">바코드</p>
          <p className="text-xl font-mono font-bold text-green-600 mb-3">{barcode}</p>

          <p className="text-xs text-gray-600 mb-1">식약처 DB</p>
          <p className="text-sm text-gray-800">{i2570_name}</p>
          {i2570_manufacturer && (
            <p className="text-xs text-gray-500">{i2570_manufacturer}</p>
          )}

          <p className="text-xs text-green-600 mt-3 font-medium">
            ✓ 편의점 DB에서 제품을 찾았습니다
          </p>
        </div>

        {/* 제품 정보 */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="bg-orange-500 text-white px-4 py-3">
            <h2 className="font-bold text-lg">등록할 제품 정보</h2>
            <p className="text-xs text-orange-100">
              {product.calories || product.protein
                ? '영양정보가 자동으로 입력됩니다'
                : '제품명과 가격 정보가 자동 입력됩니다 (데모)'}
            </p>
          </div>

          <div className="p-4 space-y-4">
            {/* 제품 이미지 */}
            {product.image_file && (
              <div className="flex justify-center bg-gray-50 rounded-lg p-4">
                <img
                  src={`${import.meta.env.VITE_API_URL}/images/${product.image_file}`}
                  alt={product.name}
                  className="max-h-48 object-contain rounded-lg shadow-sm"
                  onError={(e) => {
                    e.target.style.display = 'none';
                  }}
                />
              </div>
            )}

            {/* 제품명 */}
            <div>
              <p className="text-xs text-gray-500 mb-1">제품명</p>
              <p className="text-base font-bold text-gray-900">{product.name}</p>
            </div>

            {/* 제조사 */}
            {product.manufacturer && (
              <div>
                <p className="text-xs text-gray-500 mb-1">제조사</p>
                <p className="text-sm text-gray-700">{product.manufacturer}</p>
              </div>
            )}

            {/* 가격 */}
            {product.price && (
              <div>
                <p className="text-xs text-gray-500 mb-1">가격</p>
                <p className="text-sm font-bold text-orange-600">{product.price}원</p>
              </div>
            )}

            {/* 1회 제공량 */}
            {product.serving_size && (
              <div>
                <p className="text-xs text-gray-500 mb-1">1회 제공량</p>
                <p className="text-sm text-gray-700">{product.serving_size}</p>
              </div>
            )}

            {/* 영양정보 (있는 경우만 표시) */}
            {(product.calories || product.protein) && (
              <div className="border-t pt-4">
                <p className="text-sm font-bold text-gray-800 mb-3">영양정보</p>

                <div className="grid grid-cols-2 gap-3">
                  {product.calories && (
                    <div className="bg-gray-50 rounded-lg p-3">
                      <p className="text-xs text-gray-500 mb-1">칼로리</p>
                      <p className="text-lg font-bold text-gray-900">{product.calories} <span className="text-sm text-gray-500">kcal</span></p>
                    </div>
                  )}

                  {product.protein && (
                    <div className="bg-blue-50 rounded-lg p-3">
                      <p className="text-xs text-blue-600 mb-1">단백질</p>
                      <p className="text-lg font-bold text-blue-600">{product.protein} <span className="text-sm text-blue-400">g</span></p>
                    </div>
                  )}

                  {product.sugar && (
                    <div className="bg-gray-50 rounded-lg p-3">
                      <p className="text-xs text-gray-500 mb-1">당류</p>
                      <p className="text-base font-bold text-gray-900">{product.sugar} <span className="text-sm text-gray-500">g</span></p>
                    </div>
                  )}

                  {product.sodium && (
                    <div className="bg-gray-50 rounded-lg p-3">
                      <p className="text-xs text-gray-500 mb-1">나트륨</p>
                      <p className="text-base font-bold text-gray-900">{product.sodium} <span className="text-sm text-gray-500">mg</span></p>
                    </div>
                  )}

                  {product.fat > 0 && (
                    <div className="bg-gray-50 rounded-lg p-3">
                      <p className="text-xs text-gray-500 mb-1">지방</p>
                      <p className="text-base font-bold text-gray-900">{product.fat} <span className="text-sm text-gray-500">g</span></p>
                    </div>
                  )}

                  {product.carbohydrate > 0 && (
                    <div className="bg-gray-50 rounded-lg p-3">
                      <p className="text-xs text-gray-500 mb-1">탄수화물</p>
                      <p className="text-base font-bold text-gray-900">{product.carbohydrate} <span className="text-sm text-gray-500">g</span></p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* 영양정보 없는 경우 안내 */}
            {!product.calories && !product.protein && (
              <div className="border-t pt-4">
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <p className="text-sm text-yellow-800">
                    ⚠️ 영양정보 없음<br/>
                    <span className="text-xs text-yellow-700">등록 후 수동으로 영양정보를 추가할 수 있습니다.</span>
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 안내 메시지 */}
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
          <p className="text-sm text-blue-800">
            ✨ 위 정보로 제품을 등록합니다.<br/>
            {product.calories || product.protein ? (
              <span>등록 후에는 바코드 스캔만으로 STOPPER 분석을 받을 수 있습니다.</span>
            ) : (
              <span>영양정보는 나중에 추가하거나 수동 입력 화면에서 등록할 수 있습니다.</span>
            )}
          </p>
        </div>

        {/* 액션 버튼 */}
        <div className="flex gap-3">
          <button
            onClick={handleCancel}
            disabled={registering}
            className="flex-1 bg-gray-300 text-gray-700 py-4 rounded-xl font-bold text-lg hover:bg-gray-400 disabled:opacity-50"
          >
            취소
          </button>
          <button
            onClick={handleConfirm}
            disabled={registering}
            className="flex-1 bg-orange-500 text-white py-4 rounded-xl font-bold text-lg hover:bg-orange-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            {registering ? '등록 중...' : '이 제품 등록하기'}
          </button>
        </div>
      </div>
    </div>
  );
}
