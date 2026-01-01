/**
 * API 클라이언트 - STOPPER
 */

// Use Vercel proxy in production, direct in dev
const API_BASE = import.meta.env.DEV ? 'http://localhost:8003' : '';

/**
 * 식품 검색
 */
export async function searchFoods(query, options = {}) {
  const { limit = 20, category = null } = options;
  const params = new URLSearchParams({ q: query, limit: limit.toString() });
  if (category) params.append('category', category);
  const res = await fetch(`${API_BASE}/api/foods/search?${params}`);
  if (!res.ok) throw new Error('검색 실패');
  return res.json();
}

/**
 * 카테고리 목록 조회
 */
export async function getCategories() {
  const res = await fetch(`${API_BASE}/api/categories`);
  if (!res.ok) throw new Error('카테고리 조회 실패');
  return res.json();
}

/**
 * 식품 상세 조회
 */
export async function getFood(id) {
  const res = await fetch(`${API_BASE}/api/foods/${id}`);
  if (!res.ok) throw new Error('식품 조회 실패');
  return res.json();
}

/**
 * 식품 스캔 (% 계산)
 */
export async function scanFood(id, settings) {
  const params = new URLSearchParams({
    calorie_goal: settings.calorieGoal.toString(),
    protein_goal: settings.proteinGoal.toString(),
    sugar_limit: settings.sugarLimit.toString(),
    goal_type: settings.goalType || 'maintain',
  });
  const res = await fetch(`${API_BASE}/api/foods/${id}/scan?${params}`);
  if (!res.ok) throw new Error('스캔 실패');
  return res.json();
}

/**
 * 바코드 스캔
 */
export async function scanBarcode(barcode, settings) {
  const params = new URLSearchParams({
    calorie_goal: settings.calorieGoal.toString(),
    protein_goal: settings.proteinGoal.toString(),
    sugar_limit: settings.sugarLimit.toString(),
    goal_type: settings.goalType || 'maintain',
  });
  const res = await fetch(`${API_BASE}/api/barcode/${barcode}/scan?${params}`);
  if (!res.ok) throw new Error('바코드 스캔 실패');
  return res.json();
}

/**
 * 오늘의 기록 조회
 */
export async function getTodayRecords(fingerprint) {
  const res = await fetch(`${API_BASE}/api/records/today`, {
    headers: { 'X-Fingerprint': fingerprint },
  });
  if (!res.ok) throw new Error('기록 조회 실패');
  return res.json();
}

/**
 * 기록 추가
 */
export async function addRecord(fingerprint, foodId, quantity = 1, mealType = null) {
  const res = await fetch(`${API_BASE}/api/records`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Fingerprint': fingerprint,
    },
    body: JSON.stringify({
      food_id: foodId,
      quantity,
      meal_type: mealType,
    }),
  });
  if (!res.ok) throw new Error('기록 추가 실패');
  return res.json();
}

/**
 * 조합 목록 조회
 */
export async function getCombinations(goal = null, limit = 20) {
  const params = new URLSearchParams({ limit: limit.toString() });
  if (goal) params.append('goal', goal);
  const res = await fetch(`${API_BASE}/api/combinations?${params}`);
  if (!res.ok) throw new Error('조합 조회 실패');
  return res.json();
}

/**
 * 조합 상세 조회
 */
export async function getCombination(comboId) {
  const res = await fetch(`${API_BASE}/api/combinations/${comboId}`);
  if (!res.ok) throw new Error('조합 조회 실패');
  return res.json();
}

/**
 * 조합 생성
 */
export async function createCombination(fingerprint, data) {
  const res = await fetch(`${API_BASE}/api/combinations`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Fingerprint': fingerprint,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('조합 생성 실패');
  return res.json();
}

/**
 * 조합 좋아요
 */
export async function likeCombination(fingerprint, comboId) {
  const res = await fetch(`${API_BASE}/api/combinations/${comboId}/like`, {
    method: 'POST',
    headers: { 'X-Fingerprint': fingerprint },
  });
  if (!res.ok) throw new Error('좋아요 실패');
  return res.json();
}

/**
 * 추천용 카테고리 목록 조회 (벤치마크 포함)
 */
export async function getRecommendationCategories() {
  const res = await fetch(`${API_BASE}/api/recommendations/categories`);
  if (!res.ok) throw new Error('카테고리 조회 실패');
  return res.json();
}

/**
 * 카테고리별 추천 제품 조회
 */
export async function getRecommendations(categorySmall, options = {}) {
  const { goal = 'bulk', limit = 10, convenience_only = true } = options;
  const params = new URLSearchParams({
    goal,
    limit: limit.toString(),
    convenience_only: convenience_only.toString(),
  });
  const res = await fetch(`${API_BASE}/api/recommendations/${encodeURIComponent(categorySmall)}?${params}`);
  if (!res.ok) throw new Error('추천 제품 조회 실패');
  return res.json();
}
