import React, { useState, useEffect, useRef } from 'react';
import { DiceAnimation } from '@components/coc/DiceAnimation';

const DicePanel = ({ onDiceRoll }) => {
  const [isRolling, setIsRolling] = useState(false);
  const [result, setResult] = useState(null);
  const [rollHistory, setRollHistory] = useState([]);
  const wsRef = useRef(null);

  // WebSocket连接
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/dice');
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('骰子WebSocket连接已建立');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'skill_check_result') {
          const { skill_name, dice_roll, threshold, success, hard_level } = data;
          setIsRolling(true);
          setResult(null);
          setTimeout(() => {
            setResult(dice_roll);
            setIsRolling(false);
            const newRoll = {
              id: Date.now(),
              skill: skill_name,
              result: dice_roll,
              threshold: threshold,
              success: success,
              difficulty: hard_level,
              timestamp: new Date().toLocaleTimeString()
            };
            setRollHistory(prev => [newRoll, ...prev.slice(0, 4)]);
            if (onDiceRoll) onDiceRoll(newRoll);
          }, 1000);
        }
      } catch (error) {
        console.error('解析WebSocket消息失败:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket错误:', error);
    };

    ws.onclose = () => {
      console.log('WebSocket连接已关闭');
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [onDiceRoll]);

  const rollDice = (sides = 100) => {
    setIsRolling(true);
    setResult(null);
    setTimeout(() => {
      const roll = Math.floor(Math.random() * sides) + 1;
      setResult(roll);
      setIsRolling(false);
      const newRoll = {
        id: Date.now(),
        skill: `D${sides}`,
        result: roll,
        threshold: null,
        success: null,
        difficulty: null,
        timestamp: new Date().toLocaleTimeString()
      };
      setRollHistory(prev => [newRoll, ...prev.slice(0, 4)]);
      if (onDiceRoll) onDiceRoll(newRoll);
    }, 1000);
  };

  return (
    <div className="p-4">
      <h2 className="text-xl font-bold text-emerald-900 mb-4">骰子面板</h2>
      <div className="flex flex-col items-center space-y-4">
        <div className="flex items-center justify-center w-16 h-16 bg-emerald-950/50 rounded-lg">
          <DiceAnimation isRolling={isRolling} />
        </div>
        {result && !isRolling && (
          <div className="text-2xl font-bold text-emerald-900">{result}</div>
        )}
        <div className="grid grid-cols-2 gap-2 w-full">
          <button onClick={() => rollDice(100)} className="px-4 py-2 bg-emerald-950/90 hover:bg-emerald-900/90 text-emerald-400 rounded-lg transition-colors">D100</button>
          <button onClick={() => rollDice(20)} className="px-4 py-2 bg-emerald-950/90 hover:bg-emerald-900/90 text-emerald-400 rounded-lg transition-colors">D20</button>
        </div>
        {rollHistory.length > 0 && (
          <div className="w-full mt-4">
            <h3 className="text-sm font-semibold text-emerald-800 mb-2">最近检定</h3>
            <div className="space-y-2 max-h-32 overflow-y-auto">
              {rollHistory.map((roll) => (
                <div key={roll.id} className={`text-xs p-2 rounded ${roll.success === true ? 'bg-green-100 text-green-800' : roll.success === false ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800'}`}>
                  <div className="flex justify-between items-center">
                    <span className="font-medium">{roll.skill}: {roll.result}{roll.threshold && `/${roll.threshold}`}</span>
                    <span className="text-xs opacity-75">{roll.timestamp}</span>
                  </div>
                  {roll.success !== null && (
                    <div className="text-xs mt-1">{roll.success ? '✅ 成功' : '❌ 失败'}{roll.difficulty && ` (难度: ${roll.difficulty})`}</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DicePanel;