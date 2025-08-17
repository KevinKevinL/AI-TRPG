import random
from databaseManager import db_manager
import skillCheck
import json

def get_mapid_from_agentstate(current_character_id):
    character_id = current_character_id
    if not character_id:
        return None
    return db_manager.select_mapid_by_characterid(character_id)


def get_events_from_mapid(map_id):
    events = db_manager.select_eventinfo_by_mapid(map_id)
    # events 是字典列表 [{'eventInfo': ..., 'rate': ..., 'result': ...}]
    return events if events else []


def weighted_random_event(events):
    if not events:
        return None
    total = sum(event['rate'] for event in events)
    r = random.uniform(0, total)
    upto = 0
    for event in events:
        upto += event['rate']
        if upto >= r:
            return event
    return events[-1]  # 兜底


def get_random_event_result(current_character_id):
    map_id = get_mapid_from_agentstate(current_character_id)
    print(f"当前角色对应的ID: {current_character_id}")
    if not map_id:
        return "未找到角色对应的地图ID"
    events = get_events_from_mapid(map_id)
    if not events:
        return "未找到对应地图的事件"
    selected_event = weighted_random_event(events)
    if not selected_event:
        return "未能随机选出事件"
    skill_name = skillCheck.get_key_by_testRequired(selected_event['testRequired'])
    character_data = db_manager.get_character_data(current_character_id)
    skill_check_result = skillCheck.check_skill(character_data, skill_name, selected_event['hard_level'])
    print(f"技能检定结果: {skill_check_result}")
    skill_check_result['event_info'] = selected_event['event_info']
    if skill_check_result['result'] == '失败':
        skill_check_result['failsureResult'] = selected_event.get('failsureResult', "事件无失败结果字段")
    elif skill_check_result['result'] == '成功':
        skill_check_result['successResult'] = selected_event.get('successResult', "事件无成功结果字段")
    return json.dumps(skill_check_result, ensure_ascii=False)
