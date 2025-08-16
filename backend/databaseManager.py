import sqlite3

conn = sqlite3.connect('../database.db')
cursor = conn.cursor()

def select_mapid_by_characterid(character_id):
    cursor.execute("SELECT mapId FROM characters WHERE id = ?", (character_id,))
    result = cursor.fetchone()
    return result[0] if result else None

def select_eventinfo_by_mapid(map_id):
    cursor.execute("SELECT eventInfo, rate, result FROM maps WHERE map_ids = ?", (map_id,))
    result = cursor.fetchall()
    return result if result else None