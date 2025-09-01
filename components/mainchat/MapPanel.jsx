import { useState, useEffect, useRef } from 'react';

export default function MapPanel({ characterId, onNPCSelect }) {
  const [accessibleMaps, setAccessibleMaps] = useState([]);
  const [currentMap, setCurrentMap] = useState(null);
  const [currentNPCs, setCurrentNPCs] = useState([]);
  const [selectedNPCs, setSelectedNPCs] = useState([]);
  const [loading, setLoading] = useState(true);
  const wsRef = useRef(null);
  
  console.log('MapPanel 组件接收到的 characterId:', characterId);

  // WebSocket连接监听地图状态刷新
  useEffect(() => {
    // 创建WebSocket连接
    const ws = new WebSocket('ws://localhost:8000/ws/dice');
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('地图面板WebSocket连接已建立');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'map_state_refresh' && data.character_id === characterId) {
          console.log('收到地图状态刷新通知，自动刷新地图信息');
          fetchMapInfo(); // 自动刷新地图数据
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
    if (characterId) {
      fetchMapInfo();
    }
  }, [characterId]);

  const fetchMapInfo = async () => {
    try {
      setLoading(true);
      console.log('开始获取地图信息，角色ID:', characterId);
      
      // 通过前端代理从后端获取数据
      const sessionResponse = await fetch(`/api/session_state/${characterId}`);
      console.log('session_state API响应状态:', sessionResponse.status);
      
      if (sessionResponse.ok) {
        const sessionData = await sessionResponse.json();
        console.log('session_state 数据:', sessionData);
        
        const currentMapId = sessionData.current_map_id || 1;
        console.log('当前地图ID:', currentMapId);
        setCurrentMap(currentMapId);
        
        // 获取当前地图状态（包含可访问地图）
        console.log('准备调用 map_state API，地图ID:', currentMapId);
        const mapResponse = await fetch(`/api/map_state/${currentMapId}`);
        console.log('map_state API响应状态:', mapResponse.status);
        
        if (mapResponse.ok) {
          const mapData = await mapResponse.json();
          console.log('map_state 数据:', mapData);
          
          const accessible = mapData.accessible_maps || [];
          console.log('可访问地图:', accessible);
          setAccessibleMaps(accessible);
          
          // 获取当前地图的NPC信息
          const npcIds = mapData.npcs || [];
          console.log('当前地图NPC IDs:', npcIds);
          
          // 获取NPC详细信息
          const npcPromises = npcIds.map(async (npcId) => {
            try {
              const npcResponse = await fetch(`/api/character/${npcId}`);
              if (npcResponse.ok) {
                const npcData = await npcResponse.json();
                return {
                  id: npcId,
                  name: npcData.info?.name || npcId,
                  status: npcData.info?.status || '正常'
                };
              }
            } catch (error) {
              console.error(`获取NPC ${npcId} 信息失败:`, error);
            }
            return {
              id: npcId,
              name: npcId,
              status: '未知'
            };
          });
          
          const npcs = await Promise.all(npcPromises);
          console.log('当前地图NPC信息:', npcs);
          setCurrentNPCs(npcs);
        } else {
          console.error('map_state API调用失败:', mapResponse.status, mapResponse.statusText);
          const errorText = await mapResponse.text();
          console.error('错误详情:', errorText);
        }
      } else {
        console.error('session_state API调用失败:', sessionResponse.status, sessionResponse.statusText);
      }
    } catch (error) {
      console.error('获取地图信息失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const getMapName = (mapId) => {
    const mapNames = {
      1: '阿卡姆郊外公路',
      2: '加油站咖啡馆',
      3: '前往阿卡姆的道路'
    };
    return mapNames[mapId] || `地图${mapId}`;
  };

  const getMapDescription = (mapId) => {
    const descriptions = {
      1: '离开阿卡姆的郊外公路，天气恶劣',
      2: '加油站咖啡馆',
      3: '返回阿卡姆的道路，但可能被阻断'
    };
    return descriptions[mapId] || '未知地点';
  };

  if (loading) {
    return (
      <div className="p-4">
        <h3 className="text-lg font-semibold text-emerald-800 mb-3">地图信息</h3>
        <div className="text-sm text-gray-600">加载中...</div>
      </div>
    );
  }

  return (
    <div className="p-4">
      <h3 className="text-lg font-semibold text-emerald-800 mb-3">地图信息</h3>
      
      {/* 当前位置 */}
      <div className="mb-4 p-3 bg-emerald-50 rounded-lg border border-emerald-200">
        <div className="text-sm font-medium text-emerald-700">当前位置</div>
        <div className="text-lg font-bold text-emerald-800">{getMapName(currentMap)}</div>
        <div className="text-xs text-emerald-600 mt-1">{getMapDescription(currentMap)}</div>
      </div>

      {/* 当前地图NPC */}
      <div className="mb-3">
        <div className="text-sm font-medium text-emerald-700 mb-2">当前地图NPC</div>
        {currentNPCs.length > 0 ? (
          <div className="space-y-2">
            {currentNPCs.map((npc) => (
              <div 
                key={npc.id}
                className={`p-2 rounded border transition-colors cursor-pointer ${
                  selectedNPCs.includes(npc.id)
                    ? 'bg-blue-100 border-blue-300 text-blue-800'
                    : 'bg-gray-100 border-gray-200 hover:bg-gray-200'
                }`}
                onClick={() => {
                  const newSelected = selectedNPCs.includes(npc.id)
                    ? selectedNPCs.filter(id => id !== npc.id)
                    : [...selectedNPCs, npc.id];
                  setSelectedNPCs(newSelected);
                  
                  // 通知父组件选中的NPC
                  if (onNPCSelect) {
                    onNPCSelect(newSelected);
                  }
                }}
              >
                <div className="text-sm font-medium">{npc.name}</div>
                <div className="text-xs text-gray-600">状态: {npc.status}</div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-sm text-gray-500 italic">当前地图没有NPC</div>
        )}
        
        {selectedNPCs.length > 0 && (
          <div className="mt-2 p-2 bg-blue-50 rounded border border-blue-200">
            <div className="text-xs text-blue-700">
              已选择 {selectedNPCs.length} 个NPC进行互动
            </div>
            <button
              onClick={() => {
                setSelectedNPCs([]);
                if (onNPCSelect) {
                  onNPCSelect([]);
                }
              }}
              className="mt-1 text-xs text-blue-600 hover:text-blue-800 underline"
            >
              清除选择
            </button>
          </div>
        )}
      </div>

      {/* 可前往的地点 */}
      <div className="mb-3">
        <div className="text-sm font-medium text-emerald-700 mb-2">可前往的地点</div>
        {accessibleMaps.length > 0 ? (
          <div className="space-y-2">
            {accessibleMaps.map((mapId) => (
              <div 
                key={mapId}
                className="p-2 bg-emerald-100 rounded border border-emerald-200 hover:bg-emerald-200 transition-colors cursor-pointer"
                onClick={() => {
                  // 这里可以添加点击前往的逻辑
                  console.log(`前往地图${mapId}: ${getMapName(mapId)}`);
                }}
              >
                <div className="text-sm font-medium text-emerald-800">{getMapName(mapId)}</div>
                <div className="text-xs text-emerald-600">{getMapDescription(mapId)}</div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-sm text-gray-500 italic">当前无法前往任何地方</div>
        )}
      </div>

      {/* 刷新按钮 */}
      <button
        onClick={fetchMapInfo}
        className="w-full px-3 py-2 text-sm bg-emerald-600 text-white rounded hover:bg-emerald-700 transition-colors"
      >
        刷新地图信息
      </button>
    </div>
  );
}
