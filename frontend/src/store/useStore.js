/**
 * Zustand 스토어 - STOPPER 상태 관리
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const useStore = create(
  persist(
    (set, get) => ({
      // ============== 사용자 설정 ==============
      isOnboarded: false,
      fingerprint: null,
      settings: {
        goalType: 'maintain',  // diet, bulk, maintain, diabetes
        calorieGoal: 2000,
        proteinGoal: 60,
        sugarLimit: 50,
        sodiumLimit: 2000,
      },

      // 온보딩 완료
      completeOnboarding: (goalType) => {
        const presets = {
          diet: { calorieGoal: 1500, proteinGoal: 60, sugarLimit: 25, sodiumLimit: 2000 },
          bulk: { calorieGoal: 2500, proteinGoal: 120, sugarLimit: 50, sodiumLimit: 2300 },
          maintain: { calorieGoal: 2000, proteinGoal: 60, sugarLimit: 50, sodiumLimit: 2000 },
          diabetes: { calorieGoal: 1800, proteinGoal: 60, sugarLimit: 20, sodiumLimit: 1500 },
        };

        set({
          isOnboarded: true,
          fingerprint: `anon_${Date.now().toString(36)}`,
          settings: {
            goalType,
            ...presets[goalType],
          },
        });
      },

      // 설정 업데이트
      updateSettings: (newSettings) => {
        set((state) => ({
          settings: { ...state.settings, ...newSettings },
        }));
      },

      // ============== 오늘의 기록 ==============
      todayRecords: [],
      todayTotals: {
        calories: 0,
        protein: 0,
        sugar: 0,
        sodium: 0,
      },

      // 기록 추가
      addRecord: (record) => {
        set((state) => {
          const newRecords = [...state.todayRecords, record];
          const newTotals = {
            calories: newRecords.reduce((sum, r) => sum + r.calories * r.quantity, 0),
            protein: newRecords.reduce((sum, r) => sum + r.protein * r.quantity, 0),
            sugar: newRecords.reduce((sum, r) => sum + r.sugar * r.quantity, 0),
            sodium: newRecords.reduce((sum, r) => sum + r.sodium * r.quantity, 0),
          };
          return { todayRecords: newRecords, todayTotals: newTotals };
        });
      },

      // 기록 삭제
      removeRecord: (index) => {
        set((state) => {
          const newRecords = state.todayRecords.filter((_, i) => i !== index);
          const newTotals = {
            calories: newRecords.reduce((sum, r) => sum + r.calories * r.quantity, 0),
            protein: newRecords.reduce((sum, r) => sum + r.protein * r.quantity, 0),
            sugar: newRecords.reduce((sum, r) => sum + r.sugar * r.quantity, 0),
            sodium: newRecords.reduce((sum, r) => sum + r.sodium * r.quantity, 0),
          };
          return { todayRecords: newRecords, todayTotals: newTotals };
        });
      },

      // 오늘 기록 초기화
      clearTodayRecords: () => {
        set({
          todayRecords: [],
          todayTotals: { calories: 0, protein: 0, sugar: 0, sodium: 0 },
        });
      },

      // ============== 검색 상태 ==============
      searchQuery: '',
      searchResults: [],
      isSearching: false,

      setSearchQuery: (query) => set({ searchQuery: query }),
      setSearchResults: (results) => set({ searchResults: results }),
      setIsSearching: (isSearching) => set({ isSearching }),

      // ============== 스캔 결과 ==============
      lastScanResult: null,
      setLastScanResult: (result) => set({ lastScanResult: result }),

      // ============== % 계산 헬퍼 ==============
      getPercentage: (nutrient, value) => {
        const { settings } = get();
        const goals = {
          calories: settings.calorieGoal,
          protein: settings.proteinGoal,
          sugar: settings.sugarLimit,
          sodium: settings.sodiumLimit,
        };
        return Math.round((value / goals[nutrient]) * 100);
      },

      // 상태 판정 (safe, ok, caution, danger)
      getStatus: (nutrient, percentage) => {
        // 단백질은 높을수록 좋음
        if (nutrient === 'protein') {
          if (percentage >= 30) return 'good';
          if (percentage >= 15) return 'ok';
          return 'low';
        }
        // 나머지는 낮을수록 좋음
        if (percentage <= 15) return 'safe';
        if (percentage <= 30) return 'ok';
        if (percentage <= 50) return 'caution';
        return 'danger';
      },
    }),
    {
      name: 'stopper-storage',
      partialize: (state) => ({
        isOnboarded: state.isOnboarded,
        fingerprint: state.fingerprint,
        settings: state.settings,
      }),
    }
  )
);

export default useStore;
