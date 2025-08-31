/* ---------------------------------
 Section 1: 新增第二章核心内容
--------------------------------- */

-- Table: maps (地图信息)
-- 确保加油站咖啡馆的地图数据存在
INSERT OR IGNORE INTO "maps" ("id", "map_name", "map_info", "accessible_locations") VALUES
(4, '加油站咖啡馆', '这是一个位于阿卡姆郊外，24小时营业的加油站附属咖啡馆。现在是深夜，只有一位昏昏欲睡的店员在柜台后面打盹。窗外狂风暴雨，屋内温暖明亮，但气氛却因为艾米利亚的出现而显得紧张。', '[1]');

-- Table: interactable_objects (场景实体/可交互物)
-- 确保吧台和玻璃门的实体数据存在
INSERT OR IGNORE INTO "interactable_objects" ("object_id", "map_id", "object_name", "description_initial", "current_state") VALUES
(103, 4, '吧台', '一个油腻的木制吧台，上面放着几份过时的报纸和一把脏兮兮的咖啡壶。', '{"has_newspaper": true, "has_coffee": false}'),
(104, 4, '玻璃门', '咖啡馆的玻璃门，被雨水冲刷着，可以透过它看到外面的风雨。', '{"is_locked": false}');

-- Table: characters (角色信息总表)
-- 批量新增或更新咖啡馆内的角色信息
INSERT INTO "characters" ("id", "name", "if_npc", "gender", "description", "current_location_id", "current_vehicle_id", "current_goal", "status") VALUES
('sam_kelhan', '萨姆·凯尔汉', 1, '男', '加油站经理，一个年近50的超重男人，有着扫帚状大胡子。表面固执，但实则缺乏主见。', 4, NULL, '确保加油站正常运营。', '警惕，喧哗'),
('mary_lake', '玛丽·雷克', 1, '女', '一个精心打扮过的年轻女子，运动员般的身材，浅金色短发。她的态度紧张而心不在焉，似乎隐藏着秘密。', 4, NULL, '完成当天的班次并掩盖自己的计划。', '焦虑'),
('winifred_braille', '维妮弗蕾德·布雷尔', 1, '女', '一位在这里避雨的老年女士。她驼背、戴着眼镜，是位虔诚的家庭主妇。', 4, NULL, '等待风暴过去。', '担忧'),
('teddy_braille', '泰迪·布雷尔', 1, '男', '一位在这里避雨的老年男士，维妮弗蕾德的丈夫。一位退休的银行职员，看起来宁静而慷慨。', 4, NULL, '安慰他的妻子并等待风暴过去。', '冷静'),
('jack_bohns', '杰克·邦恩斯', 1, '男', '一个因贫穷和酗酒而显得比实际年龄老了20岁的农夫。他爱怨天尤人，神色慌张，声称被一道“死光”追逐。', 4, NULL, '寻求帮助和庇护。', '愤怒'),
('billy_easthous', '比利·伊斯特霍斯', 1, '男', '一个体格强壮的本地小混混，因为目睹死光吞噬朋友而精神崩溃。他正处于极度恐惧中，心智倒退到儿童水平。', 1, NULL, '盲目逃窜，躲避死光。', '精神崩溃，恐慌')
ON CONFLICT("id") DO UPDATE SET
  "name" = excluded."name",
  "if_npc" = excluded."if_npc",
  "gender" = excluded."gender",
  "description" = excluded."description",
  "current_location_id" = excluded."current_location_id",
  "current_vehicle_id" = excluded."current_vehicle_id",
  "current_goal" = excluded."current_goal",
  "status" = excluded."status";


-- 填充新角色的详细属性和背景
-- Sam Kelhan
INSERT INTO "attributes" ("character_id", "strength", "constitution", "size", "dexterity", "appearance", "intelligence", "power", "education", "luck", "credit_rating") VALUES
('sam_kelhan', 40, 50, 50, 50, 70, 80, 45, 60, 45, 45);

INSERT INTO "derived_attributes" ("character_id", "sanity", "magic_points", "interest_points", "hit_points", "move_rate", "damage_bonus", "build", "professional_points") VALUES
('sam_kelhan', 45, 9, 80, 10, 7, '0', 0, 60);

INSERT INTO "skills" ("character_id", "mechanics", "history", "persuade", "psychology", "investigate", "stealth", "electronics") VALUES
('sam_kelhan', 50, 40, 40, 30, 40, 30, 20);

INSERT INTO "backgrounds" ("character_id", "beliefs", "traits") VALUES
('sam_kelhan', '枪打出头鸟', '喧吵，自以为是，迂腐');


-- Jack Bohns
INSERT INTO "attributes" ("character_id", "strength", "constitution", "size", "dexterity", "appearance", "intelligence", "power", "education", "luck", "credit_rating") VALUES
('jack_bohns', 80, 70, 55, 50, 45, 40, 55, 50, 55, 20);

INSERT INTO "derived_attributes" ("character_id", "sanity", "magic_points", "interest_points", "hit_points", "move_rate", "damage_bonus", "build", "professional_points") VALUES
('jack_bohns', 55, 11, 40, 12, 7, '+1D4', 1, 50);

INSERT INTO "skills" ("character_id", "mechanics", "persuade", "psychology", "investigate", "stealth") VALUES
('jack_bohns', 60, 35, 20, 30, 40);

INSERT INTO "backgrounds" ("character_id", "beliefs", "traits") VALUES
('jack_bohns', '谁爱干活谁去干', '大男子主义、无知、粗俗');


-- Mary Lake
INSERT INTO "attributes" ("character_id", "strength", "constitution", "size", "dexterity", "appearance", "intelligence", "power", "education", "luck", "credit_rating") VALUES
('mary_lake', 40, 50, 45, 70, 60, 80, 50, 85, 50, 70);

INSERT INTO "derived_attributes" ("character_id", "sanity", "magic_points", "interest_points", "hit_points", "move_rate", "damage_bonus", "build", "professional_points") VALUES
('mary_lake', 50, 10, 85, 9, 8, '0', 0, 85);

INSERT INTO "skills" ("character_id", "art", "persuade", "psychology", "sleight_of_hand", "investigate", "stealth", "medicine") VALUES
('mary_lake', 40, 50, 40, 40, 30, 35, 35);

INSERT INTO "backgrounds" ("character_id", "beliefs", "important_people", "traits") VALUES
('mary_lake', '保全自己重于一切', '克莱姆·泰勒', '警惕、狡猾、工于心计');


-- Teddy Braille
INSERT INTO "attributes" ("character_id", "strength", "constitution", "size", "dexterity", "appearance", "intelligence", "power", "education", "luck", "credit_rating") VALUES
('teddy_braille', 35, 65, 50, 40, 60, 70, 65, 66, 65, 60);

INSERT INTO "derived_attributes" ("character_id", "sanity", "magic_points", "interest_points", "hit_points", "move_rate", "damage_bonus", "build", "professional_points") VALUES
('teddy_braille', 65, 13, 70, 11, 3, '0', 0, 66);

INSERT INTO "skills" ("character_id", "history", "mechanics", "psychology", "investigate") VALUES
('teddy_braille', 60, 40, 40, 70);

INSERT INTO "backgrounds" ("character_id", "beliefs", "traits") VALUES
('teddy_braille', '生命的奇迹无所不在', '慷慨，宁静，爱留余地');


-- Winifred Braille
INSERT INTO "attributes" ("character_id", "strength", "constitution", "size", "dexterity", "appearance", "intelligence", "power", "education", "luck", "credit_rating") VALUES
('winifred_braille', 20, 70, 35, 45, 55, 60, 60, 43, 60, 60);

INSERT INTO "derived_attributes" ("character_id", "sanity", "magic_points", "interest_points", "hit_points", "move_rate", "damage_bonus", "build", "professional_points") VALUES
('winifred_braille', 60, 12, 43, 10, 4, '-2', -2, 43);

INSERT INTO "skills" ("character_id", "persuade", "medicine", "occult", "psychology", "investigate") VALUES
('winifred_braille', 55, 60, 40, 60, 50);

INSERT INTO "backgrounds" ("character_id", "beliefs", "traits") VALUES
('winifred_braille', '虔诚的基督教徒', '慷慨，恬静，矜持');


-- Billy Easthous
INSERT INTO "attributes" ("character_id", "strength", "constitution", "size", "dexterity", "appearance", "intelligence", "power", "education", "luck", "credit_rating") VALUES
('billy_easthous', 70, 70, 85, 50, 60, 65, 40, 60, 40, 10);

INSERT INTO "derived_attributes" ("character_id", "sanity", "magic_points", "interest_points", "hit_points", "move_rate", "damage_bonus", "build", "professional_points") VALUES
('billy_easthous', 32, 8, 60, 15, 7, '+1D4', 1, 60);

INSERT INTO "skills" ("character_id", "occult", "mechanics", "persuade", "psychology", "stealth") VALUES
('billy_easthous', 5, 30, 70, 15, 25);

INSERT INTO "backgrounds" ("character_id", "beliefs", "important_people", "traits") VALUES
('billy_easthous', '某种可怕的东西就要来吃掉所有人了', '克莱姆·泰勒', '恐慌、天真、害怕');


-- Table: events (事件)
-- 新增或更新加油站咖啡馆的事件
INSERT INTO "events" ("event_id", "event_info", "map_id", "if_unique", "pre_event_ids", "preconditions", "effects") VALUES
-- Event 17: 玩家进入咖啡馆时的初始场景
(17, '玩家进入咖啡馆', 4, 1, NULL,
'{"player_action": {"intent": "enter_location", "target_location_id": 4}}',
'{
  "narrative_injection": "当你推开咖啡馆的门，一股温暖的空气扑面而来。柜台后的店员和女招待、一对老夫妇以及一名农夫都在场。那位农夫神色慌张，正激动地对人群说着什么。你听到他断断续续地重复着：“...一道死光...它在追我！”"
}'),
-- Event 18: 玩家观察杰克·邦恩斯
(18, '玩家观察杰克·邦恩斯', 4, 0, '[17]',
'{"player_action": {"intent": "inspect", "target": "杰克·邦恩斯"}}',
'{
  "skill_check": {"required": true, "character_id": -1, "skill_id": 27, "difficulty": 1},
  "outcomes": {
    "suspense_narrative": "你决定更仔细地观察这位名为杰克·邦恩斯的农夫。",
    "success": { "narrative": "尽管他竭力压抑，你还是能从他颤抖的双手和不断闪避的眼神中看出他明显被吓坏了，他的恐慌不是伪装的。" },
    "failure": { "narrative": "杰克的语无伦次让你感到困惑，除了他很惊慌以外，你无法判断更多细节。" }
  }
}'),
-- Event 19: 玩家尝试和杰克·邦恩斯交谈
(19, '和杰克·邦恩斯交谈', 4, 0, '[17]',
'{"player_action": {"intent": "talk", "target": "杰克·邦恩斯"}}',
'{
  "skill_check": {"required": true, "character_id": -1, "skill_id": 16, "difficulty": 2},
  "outcomes": {
    "suspense_narrative": "你试图安抚杰克·邦恩斯的情绪，让他冷静下来。",
    "success": { "narrative": "你的真诚打动了杰克，他终于平静了一些，断断续续地回忆道：“...那东西...那东西是道白光...就像泼出来的墨汁...它在林子里...它跟踪我...它...它把我的卡车都弄得打滑了...”" },
    "failure": { "narrative": "你的话似乎让杰克更加烦躁，他开始变得愤怒，并声称如果你不相信他，那就“用拳头说话”，他的手已经握紧了拳头。" }
  }
}'),
-- Event 20: 玩家与萨姆·凯尔汉交谈
(20, '与萨姆·凯尔汉交谈', 4, 0, '[17]',
'{"player_action": {"intent": "talk", "target": "萨姆·凯尔汉"}}',
'{
  "skill_check": {"required": true, "character_id": -1, "skill_id": 16, "difficulty": 1},
  "outcomes": {
    "suspense_narrative": "你向萨姆打招呼，他警惕地看着你和艾米利亚。",
    "success": {
      "narrative": "萨姆的警惕心在你真诚的交谈中逐渐放松下来，他一眼就认出了艾米利亚，并告诉你她来自韦伯家族，是韦伯医生的孙女，但对他们一家最近发生的事一无所知。他表示会关照她，并告诉你他认识杰克·邦恩斯，认为杰克的话不值得相信。",
      "npc_state_change": [{"character_id": "sam_kelhan", "new_status": "放松"}]
    },
    "failure": { "narrative": "萨姆只是含糊地应了一声，表示他很忙，对你和艾米利亚的态度十分警惕。" }
  }
}');
