import random
from backend.DatabaseManager import select_mapid_by_characterid, select_eventinfo_by_mapid

def get_mapid_from_agentstate(agent_state):
    character_id = agent_state.get('characterid')
    if not character_id:
        return None
    return select_mapid_by_characterid(character_id)


def get_events_from_mapid(map_id):
    events = select_eventinfo_by_mapid(map_id)
    # events 是 fetchall 返回的元组列表 (eventInfo, rate, result)
    return events if events else []


def weighted_random_event(events):
    if not events:
        return None
    total = sum(event[1] for event in events)  # event[1] 是 rate
    r = random.uniform(0, total)
    upto = 0
    for event in events:
        upto += event[1]
        if upto >= r:
            return event
    return events[-1]  # 兜底


def get_random_event_result(agent_state):
    map_id = get_mapid_from_agentstate(agent_state)
    if not map_id:
        return "未找到角色对应的地图ID"
    events = get_events_from_mapid(map_id)
    if not events:
        return "未找到对应地图的事件"
    selected_event = weighted_random_event(events)
    if not selected_event:
        return "未能随机选出事件"
    return selected_event[2] if selected_event[2] else "事件无结果字段"  # event[2] 是 result
