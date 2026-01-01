/**
 * STOPPER App - 메인 라우터
 */
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import useStore from './store/useStore';

// Pages
import Onboarding from './pages/Onboarding';
import Dashboard from './pages/Dashboard';
import Search from './pages/Search';
import Result from './pages/Result';
import Combinations from './pages/Combinations';
import Settings from './pages/Settings';

// 보호된 라우트 (온보딩 완료 필요)
function ProtectedRoute({ children }) {
  const isOnboarded = useStore((s) => s.isOnboarded);

  if (!isOnboarded) {
    return <Navigate to="/onboarding" replace />;
  }

  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* 온보딩 */}
        <Route path="/onboarding" element={<Onboarding />} />

        {/* 메인 페이지들 */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/search"
          element={
            <ProtectedRoute>
              <Search />
            </ProtectedRoute>
          }
        />
        <Route
          path="/result/:id"
          element={
            <ProtectedRoute>
              <Result />
            </ProtectedRoute>
          }
        />

        {/* 커뮤니티 */}
        <Route
          path="/combos"
          element={
            <ProtectedRoute>
              <Combinations />
            </ProtectedRoute>
          }
        />

        {/* 설정 */}
        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <Settings />
            </ProtectedRoute>
          }
        />

        {/* 404 */}
        <Route
          path="*"
          element={<Navigate to="/" replace />}
        />
      </Routes>
    </BrowserRouter>
  );
}
