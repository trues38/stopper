import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { registerProduct, lookupBarcode } from '../api/food';

export default function ProductRegister() {
  const location = useLocation();
  const navigate = useNavigate();
  const { barcode } = location.state || {};

  const [loading, setLoading] = useState(true);
  const [formData, setFormData] = useState({
    barcode: barcode || '',
    name: '',
    manufacturer: '',
    category_small: '',
    serving_size: '100g',
    calories: '',
    protein: '',
    fat: '',
    carbohydrate: '',
    sugar: '',
    sodium: '',
    saturated_fat: ''
  });

  const [i2570Found, setI2570Found] = useState(false);

  useEffect(() => {
    if (!barcode) {
      alert('바코드 정보가 없습니다.');
      navigate('/search');
      return;
    }

    // I2570에서 제품명 조회
    const fetchProductName = async () => {
      try {
        const data = await lookupBarcode(barcode);
        if (data.found) {
          setFormData(prev => ({
            ...prev,
            name: data.name || '',
            manufacturer: data.manufacturer || ''
          }));
          setI2570Found(true);
        }
      } catch (err) {
        console.error('I2570 조회 실패:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchProductName();
  }, [barcode, navigate]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // 필수 필드 검증
    if (!formData.name || !formData.calories || !formData.protein) {
      alert('제품명, 칼로리, 단백질은 필수 입력입니다.');
      return;
    }

    try {
      setLoading(true);
      const result = await registerProduct({
        ...formData,
        calories: parseFloat(formData.calories) || 0,
        protein: parseFloat(formData.protein) || 0,
        fat: parseFloat(formData.fat) || 0,
        carbohydrate: parseFloat(formData.carbohydrate) || 0,
        sugar: parseFloat(formData.sugar) || 0,
        sodium: parseFloat(formData.sodium) || 0,
        saturated_fat: parseFloat(formData.saturated_fat) || 0
      });

      alert(result.message);
      navigate(`/result/${result.id}`);
    } catch (err) {
      alert('등록 실패: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading && !i2570Found) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 mx-auto mb-4"></div>
          <p className="text-gray-600">식약처 DB에서 제품명 조회 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Header */}
      <div className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-4 flex items-center gap-3">
          <button
            onClick={() => navigate('/search')}
            className="text-2xl"
          >
            ←
          </button>
          <h1 className="text-xl font-bold">새 제품 등록</h1>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-6">
        {/* 바코드 표시 */}
        <div className="bg-orange-50 border border-orange-200 rounded-xl p-4 mb-6">
          <p className="text-sm text-gray-600 mb-1">바코드</p>
          <p className="text-xl font-mono font-bold text-orange-600">{barcode}</p>
          {i2570Found && (
            <p className="text-xs text-green-600 mt-2">✓ 식약처 DB에서 제품명을 찾았습니다</p>
          )}
          {!i2570Found && (
            <p className="text-xs text-gray-500 mt-2">⚠️ 식약처 DB에 없는 제품입니다. 수동으로 입력해주세요.</p>
          )}
        </div>

        {/* 등록 폼 */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* 제품명 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              제품명 <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              name="name"
              value={formData.name}
              onChange={handleChange}
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-transparent"
              placeholder="예: 삼립 메가불고기버거"
              required
            />
          </div>

          {/* 제조사 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              제조사
            </label>
            <input
              type="text"
              name="manufacturer"
              value={formData.manufacturer}
              onChange={handleChange}
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-transparent"
              placeholder="예: 삼립식품"
            />
          </div>

          {/* 1회 제공량 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              1회 제공량
            </label>
            <input
              type="text"
              name="serving_size"
              value={formData.serving_size}
              onChange={handleChange}
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-transparent"
              placeholder="예: 100g, 1개(200g)"
            />
          </div>

          {/* 영양정보 안내 */}
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
            <p className="text-sm font-medium text-blue-800 mb-2">📸 영양정보 입력 팁</p>
            <ul className="text-xs text-blue-700 space-y-1">
              <li>• 제품 뒷면 영양성분표를 참고하세요</li>
              <li>• <strong>1회 제공량당</strong> 영양정보를 입력해주세요</li>
              <li>• 필수 항목: 칼로리, 단백질</li>
            </ul>
          </div>

          {/* 칼로리 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              칼로리 (kcal) <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              step="0.1"
              name="calories"
              value={formData.calories}
              onChange={handleChange}
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-transparent"
              placeholder="예: 320"
              required
            />
          </div>

          {/* 단백질 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              단백질 (g) <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              step="0.1"
              name="protein"
              value={formData.protein}
              onChange={handleChange}
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-transparent"
              placeholder="예: 12.5"
              required
            />
          </div>

          {/* 당류 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              당류 (g)
            </label>
            <input
              type="number"
              step="0.1"
              name="sugar"
              value={formData.sugar}
              onChange={handleChange}
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-transparent"
              placeholder="예: 8.5"
            />
          </div>

          {/* 나트륨 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              나트륨 (mg)
            </label>
            <input
              type="number"
              step="0.1"
              name="sodium"
              value={formData.sodium}
              onChange={handleChange}
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-transparent"
              placeholder="예: 450"
            />
          </div>

          {/* 선택 항목 (접기/펼치기 가능) */}
          <details className="bg-gray-50 rounded-xl p-4">
            <summary className="cursor-pointer text-sm font-medium text-gray-700">
              추가 영양정보 (선택)
            </summary>
            <div className="mt-4 space-y-4">
              {/* 지방 */}
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1">
                  지방 (g)
                </label>
                <input
                  type="number"
                  step="0.1"
                  name="fat"
                  value={formData.fat}
                  onChange={handleChange}
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl"
                  placeholder="예: 15.5"
                />
              </div>

              {/* 탄수화물 */}
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1">
                  탄수화물 (g)
                </label>
                <input
                  type="number"
                  step="0.1"
                  name="carbohydrate"
                  value={formData.carbohydrate}
                  onChange={handleChange}
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl"
                  placeholder="예: 45.2"
                />
              </div>

              {/* 포화지방 */}
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1">
                  포화지방 (g)
                </label>
                <input
                  type="number"
                  step="0.1"
                  name="saturated_fat"
                  value={formData.saturated_fat}
                  onChange={handleChange}
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl"
                  placeholder="예: 5.2"
                />
              </div>
            </div>
          </details>

          {/* 등록 버튼 */}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-orange-500 text-white py-4 rounded-xl font-bold text-lg hover:bg-orange-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            {loading ? '등록 중...' : '제품 등록하기'}
          </button>
        </form>
      </div>
    </div>
  );
}
