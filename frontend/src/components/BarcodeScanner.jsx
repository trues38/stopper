/**
 * BarcodeScanner 컴포넌트 - 바코드/QR 스캔
 */
import React, { useEffect, useRef, useState } from 'react';
import { Html5Qrcode } from 'html5-qrcode';

export default function BarcodeScanner({ onScan, onClose }) {
  const scannerRef = useRef(null);
  const [isScanning, setIsScanning] = useState(false);
  const [manualInput, setManualInput] = useState('');

  useEffect(() => {
    // 스캐너 초기화
    const scanner = new Html5Qrcode('barcode-reader');
    scannerRef.current = scanner;

    return () => {
      // 클린업
      if (scanner.isScanning) {
        scanner.stop().catch(console.error);
      }
    };
  }, []);

  const startScan = async () => {
    try {
      setIsScanning(true);
      await scannerRef.current.start(
        { facingMode: 'environment' }, // 후면 카메라
        {
          fps: 10,
          qrbox: { width: 250, height: 150 },
        },
        (decodedText) => {
          // 스캔 성공
          stopScan();
          onScan(decodedText);
        },
        (errorMessage) => {
          // 스캔 진행 중 (오류 무시)
        }
      );
    } catch (err) {
      console.error('카메라 시작 실패:', err);
      alert('카메라를 사용할 수 없습니다. 수동 입력을 이용해주세요.');
      setIsScanning(false);
    }
  };

  const stopScan = () => {
    if (scannerRef.current?.isScanning) {
      scannerRef.current.stop().catch(console.error);
    }
    setIsScanning(false);
  };

  const handleManualSubmit = (e) => {
    e.preventDefault();
    if (manualInput.length >= 8) {
      onScan(manualInput);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-md w-full overflow-hidden">
        {/* 헤더 */}
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-bold">바코드 스캔</h2>
          <button
            onClick={() => {
              stopScan();
              onClose();
            }}
            className="text-gray-500 hover:text-gray-700 text-2xl"
          >
            ✕
          </button>
        </div>

        {/* 스캐너 영역 */}
        <div className="p-4">
          <div
            id="barcode-reader"
            className="w-full rounded-xl overflow-hidden bg-gray-100"
            style={{ minHeight: '250px' }}
          />

          {!isScanning && (
            <button
              onClick={startScan}
              className="w-full mt-4 py-3 bg-red-500 text-white font-bold rounded-xl
                        hover:bg-red-600 transition-colors"
            >
              📷 카메라로 스캔하기
            </button>
          )}

          {isScanning && (
            <button
              onClick={stopScan}
              className="w-full mt-4 py-3 bg-gray-500 text-white font-bold rounded-xl
                        hover:bg-gray-600 transition-colors"
            >
              ⏹️ 중지
            </button>
          )}

          {/* 수동 입력 */}
          <div className="mt-6 pt-6 border-t">
            <p className="text-sm text-gray-500 mb-3">또는 바코드 번호 직접 입력</p>
            <form onSubmit={handleManualSubmit} className="flex gap-2">
              <input
                type="text"
                value={manualInput}
                onChange={(e) => setManualInput(e.target.value)}
                placeholder="13자리 숫자 (예: 8801043020756)"
                className="flex-1 px-4 py-3 border rounded-xl focus:outline-none
                          focus:ring-2 focus:ring-red-500"
                pattern="[0-9]{8,13}"
              />
              <button
                type="submit"
                disabled={manualInput.length < 8}
                className="px-6 py-3 bg-red-500 text-white font-bold rounded-xl
                          hover:bg-red-600 disabled:bg-gray-300 disabled:cursor-not-allowed
                          transition-colors"
              >
                확인
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
