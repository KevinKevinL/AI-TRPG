-- 为 NPC 角色添加初始知识和扮演须知
UPDATE "characters" 
SET "initial_knowledge" = '艾米利亚知道附近有一个加油站咖啡馆，她曾经去过那里。她知道死光的存在，但无法清晰表达。她记得自己的爷爷韦伯医生，以及一些关于古老银质挂坠的记忆。',
    "roleplay_guidelines" = '扮演艾米利亚时，始终保持创伤后应激状态的特征：语言破碎、重复词语、极度敏感、寻求安全感。她的反应应该是不理性的，对外界刺激过度敏感。她不会主动攻击，只会躲避和寻求帮助。她的语言应该包含"爷爷"、"项链"、"安全"等关键词。与玩家的对话应断断续续，通过只言片语透露她对死光、爷爷和挂坠的记忆。'
WHERE "id" = 'amelia_weber';

UPDATE "characters" 
SET "initial_knowledge" = '死光知道艾米利亚·韦伯的存在，知道她身上有银质挂坠。它了解附近的地形，知道加油站咖啡馆的位置。它知道自己的掠食本能，但当前处于饱食状态。',
    "roleplay_guidelines" = '扮演死光时，始终保持非人实体的特征：无法说话，只能通过移动和气息表达意图。当前处于饱食状态，不会主动攻击，只会观察和评估。它的行为应该表现出对银质挂坠的兴趣，以及对艾米利亚的关注。它的移动应该是无声的，带有威胁性的，但不会立即采取行动。'
WHERE "id" = 'deathlight';

UPDATE "characters"
SET "initial_knowledge" = '萨姆认识艾米利亚·韦伯，知道她来自韦伯医生家族。他知道玛丽和克莱姆的关系，以及比利和克莱姆的关系。他认为他们都是“不值得理会的本地麻烦精”。他认识杰克·邦恩斯，认为杰克的话不足为信。',
    "roleplay_guidelines" = '扮演萨姆时，言行固执且喧哗，但行动上畏首畏脚。当情况变得危险时，他会要求别人做事，自己则抱着手躲在一旁。当玩家进入咖啡馆时，他对艾米利亚的到来会表现出警惕，但在真诚交谈后会认出她并愿意照顾她。他会表现出对杰克·邦恩斯的话的怀疑。即使加油站受到攻击，他也会以“这是我的职责”为由拒绝离开。'
WHERE "id" = 'sam_kelhan';

UPDATE "characters"
SET "initial_knowledge" = '玛丽知道她和男友克莱姆·泰勒的抢劫计划，以及他们的计划如何被“死光”的出现所破坏。她知道艾米利亚·韦伯和她身上的挂坠，并认为艾米利亚的到来是计划败露的证据。她知道比利和克莱姆被困在外面。',
    "roleplay_guidelines" = '扮演玛丽时，保持紧张和心不在焉的状态。当玩家进入咖啡馆时，她会异常警惕，尤其是在看到艾米利亚时。她会不时地盯着停滞的时钟，她的眼神闪烁着焦虑。当有人和她交谈时，她会敷衍地回答并试图转移话题，如果感到被识破，会不惜一切代价（包括撒谎、逃跑甚至使用收银台里的手枪）来保护自己。'
WHERE "id" = 'mary_lake';

UPDATE "characters"
SET "initial_knowledge" = '维妮弗蕾德对当前的超自然事件一无所知。她只知道自己和丈夫泰迪被风暴困在这里。',
    "roleplay_guidelines" = '扮演维妮弗蕾德时，表现出一位无辜、天真且虔诚的老妇人形象。她会显得担忧，并偶尔和丈夫泰迪进行简单而温馨的对话。在事态恶化时，她会感到极度恐惧，并可能提议报警。'
WHERE "id" = 'winifred_braille';

UPDATE "characters"
SET "initial_knowledge" = '泰迪对当前的超自然事件一无所知。他只知道自己和妻子维妮弗蕾德被风暴困在这里。',
    "roleplay_guidelines" = '扮演泰迪时，保持冷静和慷慨的形象。他会安抚妻子，并观察咖啡馆内的其他人。当玩家进入咖啡馆时，他会对玩家友好地打招呼，并解释他们去博尔顿探望亲戚后，在回家的路上被暴风雨困住了。在事态恶化时，他会感到极度恐惧，但可能会试图保持镇静。'
WHERE "id" = 'teddy_braille';

UPDATE "characters"
SET "initial_knowledge" = '杰克目击了“死光”追逐他的全过程，因此他深信“死光”是真实存在的。他知道自己因为惊慌而几乎撞上了加油站。他对萨姆的怀疑感到不满。',
    "roleplay_guidelines" = '扮演杰克时，表现出因恐惧而引发的愤怒和烦躁。当玩家进入咖啡馆时，他正在向萨姆语无伦次地描述他的遭遇。当有人质疑他的经历时，他会变得好斗。他更倾向于“用拳头说话”。当再次目击“死光”时，他的胆怯和恶毒将显露出来，可能会做出偷车等自杀性行为。'
WHERE "id" = 'jack_bohns';

UPDATE "characters"
SET "initial_knowledge" = '比利亲眼目睹了“死光”吞噬了他的朋友克莱姆。他知道死光就在附近。他现在心智倒退，但仍然记得一切，包括他和克莱姆的犯罪行为。',
    "roleplay_guidelines" = '扮演比利时，始终处于精神崩溃和极度恐慌的状态。他的行为像个孩子，情绪无法处理。当被问及任何事时，他会毫不顾忌地透露真相，因为他已经无法理解行为的后果。每一道闪电和雷鸣都会让他感到恐慌。'
WHERE "id" = 'billy_easthous';


-- Event 23: 玩家试图让杰克·邦恩斯闭嘴
INSERT OR REPLACE INTO "events" ("event_id", "event_info", "map_id", "if_unique", "pre_event_ids", "preconditions", "effects") VALUES
(23, '让杰克·邦恩斯闭嘴', 2, 0, '[14]',
'{"player_action": {"intent": "force_shut_up", "target": "杰克·邦恩斯"}}',
'{
  "skill_check": {"required": true, "character_id": -1, "skill_id": 18, "difficulty": 2},
  "outcomes": {
    "suspense_narrative": "你决定用强硬手段让杰克闭嘴，他似乎被你的态度激怒了，摆出了防备的姿势。",
    "success": {
      "narrative": "你一拳打在杰克的脸上，他踉跄着向后退了几步，鼻子开始流血。他大声咒骂着，但暂时被你震慑住了，闭上了嘴。",
      "state_changes": [
        { "target": "jack_bohns", "attribute_id": 13, "change": -1 },
        { "target": "jack_bohns", "attribute_id": 10, "change": -10 }
      ],
      "npc_state_change": [{"character_id": "jack_bohns", "new_status": "被震慑，安静下来"}]
    },
    "failure": {
      "narrative": "你试图用拳头教训杰克，但他反应迅速，避开了你的攻击，并挥拳反击。在场的其他人发出了惊恐的尖叫。",
      "state_changes": [
        { "target": "player", "attribute_id": 13, "change": -1 },
        { "target": "jack_bohns", "attribute_id": 10, "change": -5 },
        { "target": "player", "attribute_id": 10, "change": -5 }
      ],
      "npc_state_change": [{"character_id": "jack_bohns", "new_status": "愤怒，攻击"}]
    }
  }
}'),
-- Event 24: 玩家尝试威慑杰克·邦恩斯
(24, '威慑杰克·邦恩斯', 2, 0, '[14]',
'{"player_action": {"intent": "intimidate", "target": "杰克·邦恩斯"}}',
'{
  "skill_check": {"required": true, "character_id": -1, "skill_id": 18, "difficulty": 1},
  "outcomes": {
    "suspense_narrative": "你用强硬的态度试图震慑杰克，让他停止喧哗。",
    "success": { 
      "narrative": "你的气势让杰克感到不安，他停下了喋喋不休，紧张地看着你，但他的眼神中充满了怨恨。萨姆·凯尔汉轻声对你表示了感谢。",
      "npc_state_change": [{"character_id": "jack_bohns", "new_status": "被震慑，安静下来"}]
    },
    "failure": { 
      "narrative": "你的威慑似乎完全不起作用，杰克嗤之以鼻，并且变得更加愤怒，他开始大声抱怨你不相信他的遭遇，并准备向你挥拳。",
      "npc_state_change": [{"character_id": "jack_bohns", "new_status": "愤怒"}]
    }
  }
}'),
-- Event 25: 玩家向萨姆举报杰克
(25, '向萨姆举报杰克', 2, 0, '[14]',
'{"player_action": {"intent": "report", "target": "杰克·邦恩斯", "recipient": "萨姆·凯尔汉"}}',
'{
  "narrative_injection": "你走到萨姆·凯尔汉面前，轻声告诉他，你认为杰克·邦恩斯的神志有问题，他的行为可能对其他人构成威胁。萨姆听了你的话后，警惕地看了一眼杰克，然后点了点头表示他会处理这件事。",
  "npc_state_change": [{"character_id": "sam_kelhan", "new_status": "警惕"}]
}');