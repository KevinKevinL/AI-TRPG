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
