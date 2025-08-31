// components/mainchat/CharacterStatus.jsx
import React, { useEffect, useState, useRef } from 'react';
import Image from 'next/image';
// import DatabaseManager from '@components/coc/DatabaseManager';

export default function CharacterStatus({ characterId }) {
  const [characterData, setCharacterData] = useState(null);
  const [loading, setLoading] = useState(true);
  const wsRef = useRef(null);

  // 从 DatabaseManager 钩子中获取加载数据的方法 - 修复：只在组件初始化时调用一次
  // const databaseManager = DatabaseManager();
  // const { loadCharacterAttributes } = databaseManager;

  const loadCharacterData = async () => {
    // 检查 characterId 是否有效，如果无效则停止加载
    if (!characterId) {
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      // 直接从后端获取 Redis 中的数据
      const resp = await fetch(`/api/characterData?character_id=${characterId}`);
      if (resp.ok) {
        const data = await resp.json();
        // 适配为原本使用的数据结构字段名
        const adapted = {
          derivedAttributes: {
            hit_points: data?.status?.hit_points || data?.derived_attributes?.hit_points,
            magic_points: data?.status?.magic_points || data?.derived_attributes?.magic_points,
            sanity: data?.status?.sanity || data?.derived_attributes?.sanity,
          },
          characterInfo: {
            name: data?.info?.name || '未知',
          }
        };
        setCharacterData(adapted);
      } else {
        console.error('获取Redis角色数据失败');
      }
    } catch (err) {
      console.error("加载角色状态失败:", err);
    } finally {
      setLoading(false);
    }
  };

  // WebSocket连接监听角色状态刷新
  useEffect(() => {
    // 创建WebSocket连接
    const ws = new WebSocket('ws://localhost:8000/ws/dice');
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('角色状态WebSocket连接已建立');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'character_state_refresh' && data.character_id === characterId) {
          console.log('收到角色状态刷新通知，自动刷新数据');
          loadCharacterData(); // 自动刷新角色状态
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
  }, [characterId]);

  useEffect(() => {
    loadCharacterData();
    
    // 移除定时器，改为通过WebSocket实时刷新
    // 当收到character_state_refresh消息时自动刷新
  }, [characterId]);

  // 如果正在加载或没有角色数据，不渲染任何内容
  if (loading || !characterData) {
    return null;
  }

  const { derivedAttributes, characterInfo } = characterData;

  // 兼容 snake_case 与 camelCase
  const currentHp = (derivedAttributes?.hit_points ?? derivedAttributes?.hitPoints ?? 0);
  const currentMp = (derivedAttributes?.magic_points ?? derivedAttributes?.magicPoints ?? 0);
  const currentSan = (derivedAttributes?.sanity ?? 0);

  // 防止除以 0
  const hpDenominator = currentHp || 1;
  const mpDenominator = currentMp || 1;
  const sanDenominator = currentSan || 1;

  return (
    <div className="bg-emerald-950/80 rounded-lg p-4 relative min-h-40">
      {/* 角色肖像和姓名 */}
      <div className="absolute top-3 right-3 flex flex-col items-center">
        <div className="relative w-20 h-24 rounded overflow-hidden">
          <Image 
            src="/images/Amilia.png"
            alt="Character Portrait"
            fill
            className="object-cover"
            sizes="80px"
            priority
          />
        </div>
        <h3 className="mt-2 text-sm font-medium text-emerald-400 text-center">
          {characterInfo?.name || '未知'}
        </h3>
      </div>

      {/* 状态条 */}
      <div className="pr-28 space-y-3">
        {/* HP Bar */}
        <div className="flex flex-col gap-1">
          <div className="flex justify-between">
            <span className="text-sm text-emerald-400">HP</span>
            <span className="text-sm text-emerald-400">{currentHp}/{currentHp}</span>
          </div>
          <div className="w-full h-3 bg-slate-700/50 rounded-full overflow-hidden">
            <div 
              className="h-full bg-red-500 transition-all duration-300" 
              style={{ width: `${(currentHp) / hpDenominator * 100}%` }}
            ></div>
          </div>
        </div>

        {/* MP Bar */}
        <div className="flex flex-col gap-1">
          <div className="flex justify-between">
            <span className="text-sm text-emerald-400">MP</span>
            <span className="text-sm text-emerald-400">{currentMp}/{currentMp}</span>
          </div>
          <div className="w-full h-3 bg-slate-700/50 rounded-full overflow-hidden">
            <div 
              className="h-full bg-purple-500 transition-all duration-300" 
              style={{ width: `${(currentMp) / mpDenominator * 100}%` }}
            ></div>
          </div>
        </div>

        {/* Sanity Bar */}
        <div className="flex flex-col gap-1">
          <div className="flex justify-between">
            <span className="text-sm text-emerald-400">SAN</span>
            <span className="text-sm text-emerald-400">{currentSan}/{currentSan}</span>
          </div>
          <div className="w-full h-3 bg-slate-700/50 rounded-full overflow-hidden">
            <div 
              className="h-full bg-blue-500 transition-all duration-300" 
              style={{ width: `${(currentSan) / sanDenominator * 100}%` }}
            ></div>
          </div>
        </div>
      </div>
    </div>
  );
}