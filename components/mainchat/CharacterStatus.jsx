// components/mainchat/CharacterStatus.jsx
import React, { useEffect, useState } from 'react';
import Image from 'next/image';
import DatabaseManager from '@components/coc/DatabaseManager';

export default function CharacterStatus({ characterId }) {
  const [characterData, setCharacterData] = useState(null);
  const [loading, setLoading] = useState(true);

  // 从 DatabaseManager 钩子中获取加载数据的方法
  // DatabaseManager 钩子内部应使用 useCallback 来确保此函数是稳定的
  const { loadCharacterAttributes } = DatabaseManager();

  useEffect(() => {
    const loadCharacterData = async () => {
      // 检查 characterId 是否有效，如果无效则停止加载
      if (!characterId) {
        setLoading(false);
        return;
      }

      setLoading(true);
      try {
        // 使用传入的 characterId 加载角色的所有属性
        const data = await loadCharacterAttributes(characterId);
        setCharacterData(data);
      } catch (err) {
        console.error("加载角色状态失败:", err);
      } finally {
        setLoading(false);
      }
    };

    loadCharacterData();
    // 将 characterId 和 loadCharacterAttributes 添加到依赖项数组中
    // 假设 loadCharacterAttributes 是一个稳定的函数
  }, [characterId, loadCharacterAttributes]);

  // 如果正在加载或没有角色数据，不渲染任何内容
  if (loading || !characterData) {
    return null;
  }

  const { derivedAttributes, characterInfo } = characterData;

  // 为了防止除以零的错误，当 derivedAttributes?.hitPoints 为 0 时，设置默认值为 1
  const hitPoints = derivedAttributes?.hitPoints || 1;
  const magicPoints = derivedAttributes?.magicPoints || 1;
  const sanity = derivedAttributes?.sanity || 1;

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
            <span className="text-sm text-emerald-400">Hp</span>
            <span className="text-sm text-emerald-400">
              {derivedAttributes?.hitPoints || 0}/{derivedAttributes?.hitPoints || 0}
            </span>
          </div>
          <div className="w-full h-3 bg-slate-700/50 rounded-full overflow-hidden">
            <div 
              className="h-full bg-red-500 transition-all duration-300" 
              style={{ width: `${(derivedAttributes?.hitPoints || 0) / hitPoints * 100}%` }}
            ></div>
          </div>
        </div>

        {/* MP Bar */}
        <div className="flex flex-col gap-1">
          <div className="flex justify-between">
            <span className="text-sm text-emerald-400">Mp</span>
            <span className="text-sm text-emerald-400">
              {derivedAttributes?.magicPoints || 0}/{derivedAttributes?.magicPoints || 0}
            </span>
          </div>
          <div className="w-full h-3 bg-slate-700/50 rounded-full overflow-hidden">
            <div 
              className="h-full bg-purple-500 transition-all duration-300" 
              style={{ width: `${(derivedAttributes?.magicPoints || 0) / magicPoints * 100}%` }}
            ></div>
          </div>
        </div>

        {/* Sanity Bar */}
        <div className="flex flex-col gap-1">
          <div className="flex justify-between">
            <span className="text-sm text-emerald-400">San</span>
            <span className="text-sm text-emerald-400">
              {derivedAttributes?.sanity || 0}/{derivedAttributes?.sanity || 0}
            </span>
          </div>
          <div className="w-full h-3 bg-slate-700/50 rounded-full overflow-hidden">
            <div 
              className="h-full bg-blue-500 transition-all duration-300" 
              style={{ width: `${(derivedAttributes?.sanity || 0) / sanity * 100}%` }}
            ></div>
          </div>
        </div>
      </div>
    </div>
  );
}