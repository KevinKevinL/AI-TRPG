// pages/coc/mainplay.js
import { useState, useEffect } from 'react';
import DialogueBox from '@components/mainchat/DialogueBox';
import CharacterCard from '@components/mainchat/CharacterCard';
import CharacterStatus from '@components/mainchat/CharacterStatus';
import DicePanel from '@components/mainchat/DicePanel';
import MapPanel from '@components/mainchat/MapPanel';
import Image from 'next/image';
import RainEffect from '@components/mainchat/RainEffect';
import { Menu, X } from 'lucide-react';
import DatabaseManager from '@components/coc/DatabaseManager';

export default function MainPlay() {
  // 硬编码使用指定的角色ID进行测试
  const currentCharacterId = "bf4cacb2cfe76cacf804fc87bb7913e32e4fc05ace2a7a906c0fb621853bffff";
  
  // 从 DatabaseManager 获取当前角色ID - 修复：只在组件初始化时调用一次
  // const databaseManager = DatabaseManager();
  // const { currentCharacterId } = databaseManager;
  
  const [messages, setMessages] = useState([
    { 
      type: 'narrative', 
      content: '夜幕如同黑色的裹尸布，将世界包裹得严严实实。你从阿卡姆启程，正驱车前往外地处理一桩棘手的委托。然而，一场突如其来的风暴彻底打乱了你的计划。豆大的雨点疯狂地砸向车顶，闪电撕裂漆黑的夜空，照亮了车窗上扭曲的雨痕。你的车只能像一只爬行的甲虫，在泥泞的道路上缓慢挪动，努力用前灯的光穿透雨幕，避免迷失方向......' 
    },
  ]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  
  // 新增：骰子相关状态
  const [diceRollData, setDiceRollData] = useState(null);
  const [diceHistory, setDiceHistory] = useState([]);
  
  // 新增：NPC选择状态
  const [selectedNPCs, setSelectedNPCs] = useState([]);
  
  // NPC选择回调函数
  const handleNPCSelect = (npcIds) => {
    setSelectedNPCs(npcIds);
    console.log('选中的NPC:', npcIds);
  };

  useEffect(() => {
    const handleEsc = (event) => {
      if (event.keyCode === 27) {
        setIsModalOpen(false);
      }
    };
    window.addEventListener('keydown', handleEsc);
    return () => {
      window.removeEventListener('keydown', handleEsc);
    };
  }, []);

  // 新增：当角色ID存在时，发送到后端（FastAPI）并后续读取Redis
  useEffect(() => {
    if (currentCharacterId) {
      const sendCharacterIdToBackend = async () => {
        try {
          const response = await fetch('/api/characterEntered', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              character_id: currentCharacterId
            })
          });

          if (response.ok) {
            const data = await response.json();
            console.log('角色ID已发送到后端:', data);
          } else {
            console.error('发送角色ID到后端失败:', response.status);
          }
        } catch (error) {
          console.error('发送角色ID到后端时出错:', error);
        }
      };

      sendCharacterIdToBackend();
    }
  }, [currentCharacterId]);

  // 新增：处理骰子结果
  const handleDiceRoll = (rollData) => {
    setDiceHistory(prev => [rollData, ...prev.slice(0, 9)]); // 保留最近10次
    
    // 如果是技能检定结果，添加到聊天消息
    if (rollData.skill && rollData.threshold) {
      const message = {
        type: 'system',
        content: `🎲 ${rollData.skill}检定: ${rollData.result}/${rollData.threshold} - ${rollData.success ? '成功' : '失败'} (难度: ${rollData.difficulty})`,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, message]);
    }
  };


  return (
    <div className="flex h-screen bg-slate-950">
      {/* Main Content Area */}
      <div className="flex-1 flex">
        {/* Left Chat Section */}
        <div className="flex-1 relative">
          {/* Top Bar */}
          <div className="absolute top-0 left-0 right-0 z-20 p-4 flex justify-between items-center">
            <button
              className="p-2 rounded-lg bg-emerald-800/80 hover:bg-emerald-700/80 transition-colors"
              onClick={() => setIsModalOpen(true)}
            >
              <Menu className="text-white" size={24} />
            </button>
            <div className="text-emerald-700/80 font-lovecraft">CALL OF CTHULHU</div>
          </div>

          {/* Main Chat Container */}
          <div className="absolute inset-0 pt-16 px-6 pb-6">
            <div className="relative h-full rounded-lg overflow-hidden">
              {/* Background Image Layer */}
              <div className="absolute inset-0">
                <Image
                  src="/images/forest-background.png"
                  alt="Forest Background"
                  fill
                  className="object-cover object-bottom"
                  priority
                  quality={100}
                />
                <div className="absolute inset-0 bg-gradient-to-r from-slate-950/80 to-slate-950/60" />
                <RainEffect intensity={3} color="rgba(204, 230, 255, 0.4)" speed={70} />
              </div>

              {/* Chat Interface Layer */}
              <div className="relative h-full z-10">
                <DialogueBox
                  messages={messages}
                  setMessages={setMessages}
                  selectedNPCs={selectedNPCs}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Right Panel Section */}
        <div className="w-64 p-4 space-y-4 bg-slate-900/60 backdrop-blur-sm flex flex-col">
          <div className="bg-emerald-0 rounded-lg">
            <DicePanel 
              onDiceRoll={handleDiceRoll}
              externalRollData={diceRollData}
            />
          </div>
          <div className="bg-emerald-0 rounded-lg">
            <MapPanel characterId={currentCharacterId} onNPCSelect={handleNPCSelect} />
          </div>
          {/* Add flex-grow to push the character status to the bottom */}
          <div className="flex-grow"></div>
          <div className="bg-emerald-0 rounded-lg">
            {/* 将 currentCharacterId 传递给 CharacterStatus */}
            <CharacterStatus characterId={currentCharacterId} />
          </div>
        </div>
      </div>

      {/* Modal */}
      <div
        className={`fixed inset-y-0 left-0 z-50 w-3/7 transition-transform duration-300 ease-in-out transform ${
          isModalOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="relative h-full w-full">
          <button
            className="absolute top-4 right-4 z-10 p-1 rounded-full bg-emerald-800/80 hover:bg-emerald-700/80 transition-colors"
            onClick={() => setIsModalOpen(false)}
          >
            <X className="text-white" size={20} />
          </button>

          <div className="absolute inset-0">
            <Image
              src="/images/takingthepad2.png"
              alt="Paper Background"
              fill
              className="object-cover opacity-90"
              priority
              quality={100}
            />
            <div className="absolute inset-0 bg-emerald-10/40" />
          </div>

          <div className="relative h-full p-6 pt-4 pl-12 overflow-y-auto">
            <div className="mb-8 ml-auto mr-2 pl-12">
              {/* 将 currentCharacterId 传递给 CharacterCard */}
              <CharacterCard characterId={currentCharacterId} />
            </div>
          </div>
        </div>
      </div>

      {isModalOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 transition-opacity duration-300"
          onClick={() => setIsModalOpen(false)}
        />
      )}
    </div>
  );
}