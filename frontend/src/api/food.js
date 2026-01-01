/**
 * API 클라이언트 - STOPPER
 */

// Production: VPS API, Dev: localhost
const API_BASE = import.meta.env.VITE_API_URL ||
  (import.meta.env.PROD ? 'http://141.164.35.214:8003' : 'http://localhost:8003');

/**
 * 식품 검색
 */
export async function searchFoods(query, limit = 20) {
  const params = new URLSearchParams({ q: query, limit: limit.toString() });
  const res = await fetch(`${API_BASE}/api/foods/search?${params}`);
  if (!res.ok) throw new Error('검색 실패');
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
  });
  const res = await fetch(`${API_BASE}/api/foods/${id}/scan?${params}`);
  if (!res.ok) throw new Error('스캔 실패');
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
