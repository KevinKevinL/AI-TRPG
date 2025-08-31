// components/mainchat/CharacterCard.jsx
import React, { useEffect, useState, useRef } from 'react';
import Image from 'next/image';
// import DatabaseManager from '@components/coc/DatabaseManager';

// 接受 characterId prop
export default function CharacterCard({ characterId }) {
  const [characterData, setCharacterData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);

  // 只需要调用一次 DatabaseManager 来获取方法（此处不再使用 DB 加载）- 修复：只在组件初始化时调用一次
  // const databaseManager = DatabaseManager();

  const loadCharacterData = async () => {
    // 检查 characterId 是否存在，如果不存在则停止
    if (!characterId) {
      setLoading(false);
      return;
    }

    try {
      console.log('加载角色数据:', characterId);
      // 通过前端代理从后端 Redis 获取数据
      const resp = await fetch(`/api/characterData?character_id=${characterId}`);
      if (!resp.ok) throw new Error('获取 Redis 角色数据失败');
      const data = await resp.json();

      // 适配为本组件使用的数据结构
      const adapted = {
        attributes: data?.attributes || {},
        derivedAttributes: {
          hit_points: data?.status?.hit_points || data?.derived_attributes?.hit_points,
          magic_points: data?.status?.magic_points || data?.derived_attributes?.magic_points,
          sanity: data?.status?.sanity || data?.derived_attributes?.sanity,
          move_rate: data?.derived_attributes?.move_rate,
          damage_bonus: data?.derived_attributes?.damage_bonus,
          build: data?.derived_attributes?.build,
        },
        skills: data?.skills || {},
        characterInfo: data?.info || {},
      };
      setCharacterData(adapted);
    } catch (err) {
      setError(err.message);
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
      console.log('角色卡片WebSocket连接已建立');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'character_state_refresh' && data.character_id === characterId) {
          console.log('收到角色状态刷新通知，自动刷新角色卡片数据');
          loadCharacterData(); // 自动刷新角色数据
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
  }, [characterId]); // 依赖项为 characterId，当它变化时重新加载

  if (loading) {
    return <p className="text-emerald-900">Loading...</p>;
  }

  if (error) {
    return <p className="text-red-500">Error: {error}</p>;
  }

  if (!characterData) {
    return <p className="text-emerald-900">Character data not found</p>;
  }

  const { attributes, derivedAttributes, skills, characterInfo } = characterData;

  return (
    <div className="pl-20 pt-8">
      <div>
        <div className="flex gap-8 mb-2">
          <div className="relative w-32 h-40 overflow-hidden">
            <Image 
              src="/images/Amilia.png"
              alt="Character Portrait"
              fill
              className="object-cover"
              sizes="128px"
              priority
            />
          </div>

          <div className="flex flex-col justify-center gap-3 text-emerald-900">
            <p>Name: {characterInfo?.name || 'Unknown'}</p>
            <p>Gender: {characterInfo?.gender || 'Unknown'}</p>
            <p>Residence: {characterInfo?.residence || 'Unknown'}</p>
            <p>Birthplace: {characterInfo?.birthplace || 'Unknown'}</p>
          </div>
        </div>

        <div className="mb-2">
          <h3 className="text-base font-semibold text-emerald-900 mb-2">Base Attributes</h3>
          <div className="grid grid-cols-3 gap-3 text-emerald-900">
            <p>Strength: {attributes?.strength || 0}</p>
            <p>Constitution: {attributes?.constitution || 0}</p>
            <p>Size: {attributes?.size || 0}</p>
            <p>Dexterity: {attributes?.dexterity || 0}</p>
            <p>Appearance: {attributes?.appearance || 0}</p>
            <p>Intelligence: {attributes?.intelligence || 0}</p>
            <p>Power: {attributes?.power || 0}</p>
            <p>Education: {attributes?.education || 0}</p>
            <p>Luck: {attributes?.luck || 0}</p>
          </div>
        </div>

        <div className="mb-2">
          <h3 className="text-base font-semibold text-emerald-900 mb-2">Derived Attributes</h3>
          <div className="grid grid-cols-3 gap-3 text-emerald-900">
            <p>Hit Points: {derivedAttributes?.hit_points || 0}</p>
            <p>Magic Points: {derivedAttributes?.magic_points || 0}</p>
            <p>Sanity: {derivedAttributes?.sanity || 0}</p>
            <p>Move Rate: {derivedAttributes?.move_rate || 0}</p>
            <p>Damage Bonus: {derivedAttributes?.damage_bonus || 0}</p>
            <p>Build: {derivedAttributes?.build || 0}</p>
          </div>
        </div>

        <div className="mb-2">
          <h3 className="text-base font-semibold text-emerald-900 mb-2">Skills</h3>
          <div className="grid grid-cols-3 gap-3 text-emerald-900">
            <p>Fighting: {skills?.fighting || 0}</p>
            <p>Firearms: {skills?.firearms || 0}</p>
            <p>Dodge: {skills?.dodge || 0}</p>
            <p>Mechanics: {skills?.mechanics || 0}</p>
            <p>Drive: {skills?.drive || 0}</p>
            <p>Stealth: {skills?.stealth || 0}</p>
            <p>Investigate: {skills?.investigate || 0}</p>
            <p>Sleight of Hand: {skills?.sleight_of_hand || 0}</p>
            <p>Electronics: {skills?.electronics || 0}</p>
            <p>History: {skills?.history || 0}</p>
            <p>Science: {skills?.science || 0}</p>
            <p>Medicine: {skills?.medicine || 0}</p>
            <p>Occult: {skills?.occult || 0}</p>
            <p>Library Use: {skills?.library_use || 0}</p>
            <p>Art: {skills?.art || 0}</p>
            <p>Persuade: {skills?.persuade || 0}</p>
            <p>Psychology: {skills?.psychology || 0}</p>
          </div>
        </div>
      </div>
    </div>
  );
}