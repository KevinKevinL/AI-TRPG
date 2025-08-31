/*
 ==========================================================
    AI跑团系统 - 创世最终脚本 (结构修改版)
 ==========================================================
*/

-- 开启外键约束功能 (推荐)
PRAGMA foreign_keys=ON;

/* ---------------------------------
 Section 1: 创建核心表结构
---------------------------------
*/

-- Table: world_state (全局世界状态)
DROP TABLE IF EXISTS "world_state";
CREATE TABLE "world_state" (
  "state_key" TEXT PRIMARY KEY NOT NULL,
  "state_value" TEXT NULL,
  "last_updated" DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Table: maps (地图信息)
DROP TABLE IF EXISTS "maps";
CREATE TABLE "maps" (
  "id" INTEGER PRIMARY KEY,
  "map_name" TEXT NULL,
  "map_info" TEXT NULL,
  "accessible_locations" TEXT NULL -- JSON array of map IDs
);

-- Table: interactable_objects (场景实体/可交互物)
DROP TABLE IF EXISTS "interactable_objects";
CREATE TABLE "interactable_objects" (
  "object_id" INTEGER PRIMARY KEY,
  "map_id" INTEGER,
  "object_name" TEXT NULL,
  "description_initial" TEXT NULL,
  "is_interactive" INTEGER DEFAULT 1,
  "current_state" TEXT NULL, -- JSON
  FOREIGN KEY ("map_id") REFERENCES "maps" ("id")
);

-- Table: events (事件)
DROP TABLE IF EXISTS "events";
CREATE TABLE "events" (
  "event_id" INTEGER PRIMARY KEY,
  "event_info" TEXT NULL,
  "map_id" INTEGER NULL,
  "if_unique" INTEGER NULL,
  "pre_event_ids" TEXT NULL,  -- JSON array
  "preconditions" TEXT NULL,   -- JSON
  "effects" TEXT NULL          -- JSON
);

-- Table: npc_memories (NPC记忆)
DROP TABLE IF EXISTS "npc_memories";
CREATE TABLE "npc_memories" (
  "memory_id" INTEGER PRIMARY KEY AUTOINCREMENT,
  "character_id" TEXT NOT NULL,
  "timestamp" DATETIME DEFAULT CURRENT_TIMESTAMP,
  "memory_text" TEXT NOT NULL,
  "type" TEXT NOT NULL,  -- 'observation', 'conversation', 'reflection'
  "importance" INTEGER DEFAULT 5,
  FOREIGN KEY ("character_id") REFERENCES "characters" ("id") ON DELETE CASCADE
);

-- Table: professions (职业)
DROP TABLE IF EXISTS "professions";
CREATE TABLE "professions" (
  "id" INTEGER PRIMARY KEY,
  "title" TEXT NULL,
  "description" TEXT NULL
);

-- Table: characters (角色信息总表)
DROP TABLE IF EXISTS "characters";
CREATE TABLE "characters" (
  "id" TEXT PRIMARY KEY NOT NULL,
  "name" TEXT NULL,
  "if_npc" INTEGER NULL,
  "gender" TEXT NULL,
  "residence" TEXT NULL,
  "birthplace" TEXT NULL,
  "profession_id" INTEGER NULL,
  "description" TEXT NULL,
  "current_location_id" INTEGER NULL,
  "current_vehicle_id" INTEGER NULL,
  "current_goal" TEXT NULL,
  "status" TEXT NULL,
  "relationships" TEXT NULL, -- JSON
  FOREIGN KEY ("profession_id") REFERENCES "professions" ("id") ON DELETE SET NULL,
  FOREIGN KEY ("current_location_id") REFERENCES "maps" ("id") ON DELETE SET NULL
);

-- ==========================================================
-- Section 1.1: 新增的角色数据表 (根据旧数据库结构)
-- ==========================================================

-- Table: attributes (核心属性)
DROP TABLE IF EXISTS "attributes";
CREATE TABLE "attributes" (
  "character_id" char(64) NULL,
  "strength" int NULL,
  "constitution" int NULL,
  "size" int NULL,
  "dexterity" int NULL,
  "appearance" int NULL,
  "intelligence" int NULL,
  "power" int NULL,
  "education" int NULL,
  "luck" int NULL,
  "credit_rating" int NULL,
  UNIQUE ("character_id")
);

-- Table: derived_attributes (衍生属性)
DROP TABLE IF EXISTS "derived_attributes";
CREATE TABLE "derived_attributes" (
  "character_id" char(64) NULL,
  "sanity" int NULL,
  "magic_points" int NULL,
  "interest_points" int NULL,
  "hit_points" int NULL,
  "move_rate" int NULL,
  "damage_bonus" text NULL,
  "build" int NULL,
  "professional_points" int NULL,
  UNIQUE ("character_id")
);

-- Table: skills (技能)
DROP TABLE IF EXISTS "skills";
CREATE TABLE "skills" (
  "character_id" char(64) NULL,
  "fighting" int NULL,
  "firearms" int NULL,
  "dodge" int NULL,
  "mechanics" int NULL,
  "drive" int NULL,
  "stealth" int NULL,
  "investigate" int NULL,
  "sleight_of_hand" int NULL,
  "electronics" int NULL,
  "history" int NULL,
  "science" int NULL,
  "medicine" int NULL,
  "occult" int NULL,
  "library_use" int NULL,
  "art" int NULL,
  "persuade" int NULL,
  "psychology" int NULL,
  UNIQUE ("character_id"),
  CONSTRAINT "Skills_ibfk_1" FOREIGN KEY ("character_id") REFERENCES "characters" ("id") ON DELETE RESTRICT ON UPDATE RESTRICT
);

-- Table: backgrounds (背景)
DROP TABLE IF EXISTS "backgrounds";
CREATE TABLE "backgrounds" (
  "character_id" char(64) NULL,
  "beliefs" text NULL,
  "beliefs_details" text NULL,
  "important_people" text NULL,
  "important_people_details" text NULL,
  "reasons" text NULL,
  "reasons_details" text NULL,
  "places" text NULL,
  "places_details" text NULL,
  "possessions" text NULL,
  "possessions_details" text NULL,
  "traits" text NULL,
  "traits_details" text NULL,
  "keylink" text NULL,
  "keylink_details" text NULL,
  UNIQUE ("character_id"),
  CONSTRAINT "Backgrounds_ibfk_1" FOREIGN KEY ("character_id") REFERENCES "characters" ("id") ON DELETE RESTRICT ON UPDATE RESTRICT
);


/* ---------------------------------
 Section 2: 填充第一章基础设定数据
---------------------------------
*/

-- 填充世界初始状态
INSERT INTO "world_state" ("state_key", "state_value") VALUES
('weather', '"Raging Storm"'),
('time_of_day', '"Night"'),
('game_turn', '0');

-- 填充地图信息
INSERT INTO "maps" ("id", "map_name", "map_info", "accessible_locations") VALUES
(1, '阿卡姆郊外公路', '在风暴肆虐的黑夜中，调查员回到了阿卡姆郊外一条孤寂的名为园林大道的道路上。张牙舞爪的树林在风雨交加的夜色中，如同一场阴暗的噩梦般可怕。', '[2, 3]'),
(2, '加油站咖啡馆', '一个24小时营业的加油站附属咖啡馆，是附近唯一的灯光。', '[1]'),
(3, '阿卡姆市区方向', '返回阿卡姆的道路，但天气异常恶劣。', '[1]');

-- 填充场景实体
INSERT INTO "interactable_objects" ("object_id", "map_id", "object_name", "description_initial", "current_state") VALUES
(101, 1, '调查员的车', '调查员的座驾，现在正艰难地对抗着风暴。', '{"status": "running", "capacity": 4, "passengers": []}'),
(102, 1, '古老的金币式挂坠', '一条装饰着某个似乎是古代金币的老旧银质挂坠。', '{"owner": "amelia_weber"}');


/* ----------------------------------
 Section 3: 填充第一章核心角色数据
----------------------------------
*/
+ 
-- 填充角色: 艾米利亚·韦伯
INSERT INTO "characters" ("id", "name", "if_npc", "gender", "description", "current_location_id", "current_vehicle_id", "current_goal", "status") VALUES
('amelia_weber', '艾米利亚·韦伯', 1, '女',
'艾米利亚是个20出头，看起来又瘦又憔悴但是却不失魅力的女人。她正处于严重的创伤后应激状态，对外界刺激反应极大，语言能力减退，只会重复一些破碎的词语或发出无意义的呜咽声。她的所有行为都围绕着寻找安全感和躲避想象中的威胁。',
1, NULL, '(非理性)不惜一切代价寻找安全感，躲避看不见的威胁', '创伤后应激，精神恍惚，语言混乱');

-- 填充角色: 死光
INSERT INTO "characters" ("id", "name", "if_npc", "description", "current_location_id", "current_goal", "status") VALUES
('deathlight', '死光', 1,
'它看起来像一团会让观看者看起来又恶心又怪异的，泼洒出来的银白色墨汁。它是一个没有声带的掠食性实体，【无法说话】，只会通过无声的移动和散发出的非人气息来表达意图。在本章中，它处于【饱食状态】，没有强烈的攻击欲望。',
1, '保持隐蔽，观察并评估附近潜在的能量源', '饱食后潜伏，隐匿');

-- 填充 艾米利亚·韦伯 的数据
INSERT INTO "attributes" ("character_id", "strength", "constitution", "size", "dexterity", "appearance", "intelligence", "power", "education", "luck") VALUES
('amelia_weber', 40, 50, 45, 70, 60, 80, 50, 85, 50);

INSERT INTO "derived_attributes" ("character_id", "sanity", "hit_points", "move_rate", "damage_bonus", "build") VALUES
('amelia_weber', 50, 9, 8, '0', 0);

INSERT INTO "skills" ("character_id", "fighting", "firearms", "dodge", "mechanics", "drive", "stealth", "investigate", "sleight_of_hand", "electronics", "history", "science", "medicine", "occult", "library_use", "art", "persuade", "psychology") VALUES
('amelia_weber', 25, 20, 35, 10, 20, 40, 35, 10, 10, 40, 25, 30, 5, 20, 5, 45, 20);

INSERT INTO "backgrounds" ("character_id", "beliefs", "important_people", "possessions", "traits") VALUES
('amelia_weber', '科学揭示世界的真相', '她爷爷韦伯医生', '一串带着银质挂坠的古老项链', '忠诚');

-- 填充 死光 的数据
INSERT INTO "attributes" ("character_id", "strength", "constitution", "size", "dexterity", "power", "intelligence") VALUES
('deathlight', 70, 70, 90, 80, 100, 80);

INSERT INTO "derived_attributes" ("character_id", "hit_points", "damage_bonus", "build", "move_rate", "magic_points") VALUES
('deathlight', 16, '+1D6', 2, 6, 20);

INSERT INTO "skills" ("character_id", "fighting", "dodge", "stealth") VALUES
('deathlight', 70, 40, 25);


/* ----------------------------
 Section 4: 填充第一章事件
----------------------------
*/

INSERT INTO "events" ("event_id", "event_info", "map_id", "if_unique", "pre_event_ids", "preconditions", "effects") VALUES
-- Event 1: 遭遇艾米利亚·韦伯
(1, '遭遇艾米利亚·韦伯', 1, 1, NULL,
'{"agent_state": {"agent_id": "player", "current_location_id": 1, "current_vehicle_id": 101}}',
'{
  "skill_check": {"required": true, "character_id": -1, "skill_id": 22, "difficulty": 2},
  "outcomes": {
    "suspense_narrative": "有东西毫无预示的挡在了调查员的面前，这是一个如同凭空冒出来般的苍白身影。为避免撞上去，调查员下意识地转动方向盘并踩下刹车。",
    "success": {
      "narrative": "多亏调查员精准的操作，车子擦着她的身体停下，没有撞到她。那个女人睁着大大的眼睛，发出凄厉的惨叫声。",
      "npc_state_change": [{ "character_id": "amelia_weber", "new_status": "神志恍惚" }]
    },
    "failure": {
      "narrative": "调查员猛踩刹车，但车辆在积水路面上打滑。车身擦过她的身体，将她刮倒在地。",
      "npc_state_change": [{ "character_id": "amelia_weber", "new_status": "神志恍惚且受伤" }],
      "state_changes": [{ "target": "amelia_weber", "attribute_id": 13, "change": -1 }, { "target": "player", "attribute_id": 10, "change": -1 }]
    }
  }
}'),
-- Event 2: 玩家选择驱车离开
(2, '驱车离开', 1, 1, '[1]',
'{"player_action": {"intent": "leave_woman"}}',
'{
  "narrative_injection": "调查员将她留在身后，她的惨叫声被风雨声吞没，渐渐远去。调查员的心头涌上一丝不安，仿佛将一个无助的灵魂留给了黑暗。同时，调查员感到车后方似乎有什么东西跟了上来。",
  "state_changes": [{ "target": "player", "attribute_id": 10, "change": -5 }],
  "trigger_event": 3
}'),
-- Event 3: 死光开始追踪玩家
(3, '死光开始追踪玩家', 1, 1, '[2]', NULL,
'{
  "narrative_injection": "一股被监视的感觉袭来。调查员从后视镜瞥见一团模糊的白光正在迅速逼近，莫大的危机感让调查员心生恐惧。",
  "state_changes": [{ "target": "player", "attribute_id": 10, "change": -1 }]
}'),
-- Event 4: 玩家选择下车帮助
(4, '下车帮助艾米利亚', 1, 1, '[1]',
'{"player_action": {"intent": "help_woman"}}',
'{
  "narrative_injection": "调查员决定下车帮助她。她全身湿透，颤抖不止，显然处于极度惊吓之中。她并没携带任何的身份标示，仅带着一条装饰着某个似乎是古代金币的老旧银质挂坠。",
  "state_changes": [{ "target": "player", "set_state": {"current_vehicle_id": null} }]
}'),
-- Event 5: 回忆附近是否有避难所
(5, '回忆附近是否有避难所', 1, 0, '[4]',
'{"player_action": {"intent": "use_skill", "skill_check_request": ["intelligence"]}}',
'{
  "skill_check": {"required": true, "character_id": -1, "skill_id": 6, "difficulty": 1},
  "outcomes": {
    "suspense_narrative": "在这荒郊野外，调查员开始努力回忆这附近是否有什么避难所。",
    "success": { "narrative": "调查员猛然想起（知识检定成功），大约一英里外应该有一个带咖啡馆的加油站。" },
    "failure": { "narrative": "调查员对这片区域一无所知，脑中一片空白。" }
  }
}'),
-- Event 6: 搜寻丛林
(6, '搜寻丛林', 1, 0, '[4]',
'{"player_action": {"intent": "inspect", "target": "丛林"}, "agent_state": {"agent_id": "player", "current_vehicle_id": null}}',
'{
  "skill_check": {"required": true, "character_id": -1, "skill_id": 7, "difficulty": 2},
  "outcomes": {
    "suspense_narrative": "调查员决定进入路边的丛林搜寻线索。",
    "success": { "narrative": "调查员感到一种被某物注视的不快感，但除了湿透的树木和泥土，最终一无所获。" },
    "failure": {
      "narrative": "调查员感到一种被某物注视的不快感越来越强烈，仿佛有什么东西正在暗中跟随着调查员...",
      "trigger_event": 7
    }
  }
}'),
-- Event 7: 在丛林中遭遇死光
(7, '在丛林中遭遇死光', 1, 1, '[6]', NULL,
'{
  "narrative_injection": "正当调查员因一无所获而准备放弃时，那股被注视的感觉猛然增强！一团怪异而模糊的白光从树林深处向调查员逼近，调查员感受到了前所未有的恐惧。",
  "state_changes": [{ "target": "player", "attribute_id": 10, "change": -3 }]
}'),
-- Event 8: 观察古老的金币式挂坠
(8, '观察古老的金币式挂坠', 1, 0, '[4]',
'{"player_action": {"intent": "inspect", "target": "古老的金币式挂坠"}}',
'{
  "skill_check": {"required": true, "character_id": -1, "skill_id": 30, "difficulty": 3},
  "outcomes": {
    "suspense_narrative": "调查员凑近观察那条被艾米利亚视作珍宝的旧银质挂坠，上面的符号看起来非常古怪，似乎蕴含着某种不祥的意味。",
    "success": { "narrative": "调查员的神秘学知识告诉你，这些不规则的符号是古老的阿克洛语，通常用于祭司阶层的皇家典礼。这绝非凡物。" },
    "failure": { "narrative": "调查员无法辨认上面的符号，只能感觉到它的年代久远，散发着一丝难以言喻的古怪气息。" }
  }
}'),
-- Event 9: 让艾米利亚上车
(9, '让艾米利亚上车', 1, 1, '[4]',
'{"player_action": {"intent": "take_amelia_in_car"}}',
'{
  "narrative_injection": "调查员搀扶着艾米利亚上了车，她缩在副驾驶座上，依然在微微颤抖。",
  "state_changes": [
      { "target": "player", "set_state": {"current_vehicle_id": 101} },
      { "target": "amelia_weber", "set_state": {"current_vehicle_id": 101} }
  ]
}'),
-- Event 10: 观察到林中白光
(10, '观察到林中白光', 1, 0, '[9]',
'{"player_action": {"intent": "inspect", "target": "树林"}, "agent_state": {"agent_id": "player", "current_vehicle_id": 101}}',
'{
  "skill_check": {"required": true, "character_id": -1, "skill_id": 24, "difficulty": 3},
  "outcomes": {
      "suspense_narrative": "调查员顶着风雨，眯起眼睛仔细观察路边的树林。",
      "success": { "narrative": "在一道闪电划破夜空时，调查员敏锐地瞥见树林深处有一道转瞬即逝的古怪白光。它似乎在跟踪你们，让调查员感到一阵不安。" },
      "failure": { "narrative": "风雨太大了，调查员什么也看不清。" }
    }
}'),
-- Event 11: 大树挡住去路
(11, '大树挡住去路', 1, 1, NULL,
'{"player_action": {"intent": "move", "target_location_id": 3}}',
'{
  "narrative_injection": "当调查员试图掉头返回阿卡姆时，一道耀眼的闪电撕裂夜空，猛地劈在路边的一棵大树上！大树轰然倒下，沉重地横亙在路上，彻底断绝了调查员的退路。",
  "world_state_change": {"location_3_accessible": "false"},
  "trigger_event": 12
}'),
-- Event 12: 艾米利亚对倒下的大树的反应
(12, '艾米利亚对倒下的大树的反应', 1, 1, '[11]', NULL,
'{
  "skill_check": {"required": true, "character_id": "amelia_weber", "skill_id": 7, "difficulty": 1},
  "outcomes": {
    "suspense_narrative": "巨大的声响在耳边炸响。",
    "success": {
      "narrative": "这声巨响让艾米利亚浑身一颤，但她只是抓紧了衣袖，强忍住了尖叫。",
      "npc_state_change": [{"character_id": "amelia_weber", "new_status": "受惊但镇定"}]
    },
    "failure": {
      "narrative": "这声巨响击溃了艾米利亚脆弱的神经，她发出一声遏制不住的尖叫，蜷缩在座位上瑟瑟发抖。",
      "npc_state_change": [{"character_id": "amelia_weber", "new_status": "惊恐发作"}]
    }
  }
}'),
-- Event 13: 艾米利亚尝试回忆祖父的事
(13, '艾米利亚尝试回忆祖父的事', 1, 0, '[9]',
'{"player_action": {"target": "amelia_weber", "topic": "祖父"}}',
'{
  "skill_check": {"required": true, "character_id": "amelia_weber", "skill_id": 6, "difficulty": 2},
  "outcomes": {
      "suspense_narrative": "听到‘祖父’这个词，艾米利亚的眼神有了一丝波动，她努力地在混乱的记忆中搜索着什么。",
      "success": { "narrative": "她似乎想起了一些事情，断断续续地说：‘……他的钥匙……总是在……怀表口袋里……’" },
      "failure": { "narrative": "她痛苦地摇了摇头，‘……我……想不起来……一片混乱……’" }
    }
}');
