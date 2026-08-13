import streamlit as st
import requests
import json
import random
import re
import time
import base64
from difflib import SequenceMatcher


# =========================================================
# V3.5
# 三界奇譚：小薯逆襲記
# =========================================================

st.set_page_config(
    page_title="三界奇譚：小薯逆襲記",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# 1. OpenRouter
# =========================================================

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "nvidia/nemotron-3-ultra-550b-a55b:free"

MAX_API_RETRIES = 3
API_TIMEOUT = 120


def get_api_key():
    key = st.secrets.get("OPENROUTER_API_KEY", "")

    if key is None:
        return ""

    key = str(key).strip()
    key = key.replace("\r", "").replace("\n", "")
    key = key.replace("\ufeff", "")

    key = key.strip("\"'")
    key = key.strip("「」")
    key = key.strip("“”")

    if key.startswith("OPENROUTER_API_KEY="):
        key = key.split("=", 1)[1].strip()

    return key


OPENROUTER_API_KEY = get_api_key()

if not OPENROUTER_API_KEY:
    st.error(
        "⚠️ 找不到 OPENROUTER_API_KEY。\n\n"
        "請到 Streamlit Cloud → Settings → Secrets 設定：\n\n"
        'OPENROUTER_API_KEY = "你的 API Key"'
    )
    st.stop()


def clean_api_key(key):
    if key is None:
        return ""

    key = str(key).strip()
    key = key.replace("\r", "").replace("\n", "")
    key = key.replace("\ufeff", "")

    key = key.strip("\"'")
    key = key.strip("「」")
    key = key.strip("“”")

    if key.startswith("OPENROUTER_API_KEY="):
        key = key.split("=", 1)[1].strip()

    # API Key 正常應該只包含 ASCII。
    # 唔再將 Unicode 直接塞入 HTTP Header。
    try:
        key.encode("ascii")
    except UnicodeEncodeError:
        raise RuntimeError(
            "OPENROUTER_API_KEY 含有非 ASCII 字元。\n\n"
            "請檢查 Streamlit Secrets，確保只放真正 API Key，"
            "不要包含中文引號、空格、換行或其他文字。"
        )

    return key


# =========================================================
# 2. API 呼叫
# =========================================================

def call_nemotron(messages):
    api_key = clean_api_key(OPENROUTER_API_KEY)

    if not api_key:
        raise RuntimeError("OpenRouter API Key 是空白的。")

    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "HTTP-Referer": "https://openrouter.ai",
        "X-Title": "Three Realms RPG",
    }

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.8,
        "max_tokens": 2500,
    }

    last_error = None

    for attempt in range(MAX_API_RETRIES):
        try:
            response = requests.post(
                OPENROUTER_URL,
                headers=headers,
                json=payload,
                timeout=API_TIMEOUT,
            )

        except requests.exceptions.Timeout as error:
            last_error = (
                "OpenRouter 回應逾時。"
            )

            if attempt < MAX_API_RETRIES - 1:
                time.sleep(2 * (attempt + 1))
                continue

            raise RuntimeError(
                last_error
                + "\n\n已重試 "
                + str(MAX_API_RETRIES)
                + " 次。"
            )

        except requests.exceptions.RequestException as error:
            last_error = (
                "連接 OpenRouter 失敗："
                + str(error)
            )

            if attempt < MAX_API_RETRIES - 1:
                time.sleep(2 * (attempt + 1))
                continue

            raise RuntimeError(last_error)

        # -------------------------------------------------
        # 429
        # -------------------------------------------------

        if response.status_code == 429:
            retry_after = response.headers.get(
                "Retry-After",
                ""
            )

            wait_seconds = 2 * (attempt + 1)

            try:
                if retry_after:
                    wait_seconds = max(
                        wait_seconds,
                        min(int(retry_after), 15)
                    )
            except Exception:
                pass

            if attempt < MAX_API_RETRIES - 1:
                time.sleep(wait_seconds)
                continue

            try:
                error_data = response.json()
                detail = json.dumps(
                    error_data,
                    ensure_ascii=False
                )
            except Exception:
                detail = response.text[:1000]

            raise RuntimeError(
                "OpenRouter 回覆 429。\n\n"
                "即係目前受到 Rate Limit / 免費模型額度限制，"
                "或者模型暫時繁忙。\n\n"
                "程式已自動重試 "
                + str(MAX_API_RETRIES)
                + " 次，但仍然未成功。\n\n"
                + detail
            )

        # -------------------------------------------------
        # 5xx
        # -------------------------------------------------

        if 500 <= response.status_code <= 599:
            last_error = (
                "OpenRouter 伺服器暫時錯誤："
                + str(response.status_code)
            )

            if attempt < MAX_API_RETRIES - 1:
                time.sleep(2 * (attempt + 1))
                continue

            raise RuntimeError(last_error)

        # -------------------------------------------------
        # 其他錯誤
        # -------------------------------------------------

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_text = json.dumps(
                    error_data,
                    ensure_ascii=False
                )
            except Exception:
                error_text = response.text[:1500]

            if response.status_code == 401:
                raise RuntimeError(
                    "OpenRouter API Key 無效或未授權。\n\n"
                    "請檢查 Streamlit Secrets。"
                )

            if response.status_code == 403:
                raise RuntimeError(
                    "OpenRouter 拒絕請求。\n\n"
                    "可能係模型權限、帳戶或 API Key 問題。\n\n"
                    + error_text
                )

            raise RuntimeError(
                "OpenRouter API 錯誤 "
                + str(response.status_code)
                + "\n\n"
                + error_text
            )

        # -------------------------------------------------
        # 解析 JSON
        # -------------------------------------------------

        try:
            result = response.json()
        except Exception:
            raise RuntimeError(
                "OpenRouter 返回的內容不是有效 JSON。"
            )

        if "error" in result:
            raise RuntimeError(
                "模型 API 發生錯誤：\n"
                + json.dumps(
                    result["error"],
                    ensure_ascii=False
                )
            )

        choices = result.get("choices", [])

        if not choices:
            raise RuntimeError(
                "模型沒有返回有效結果。"
            )

        message = choices[0].get(
            "message",
            {}
        )

        content = message.get(
            "content",
            ""
        )

        if isinstance(content, list):
            parts = []

            for part in content:
                if isinstance(part, dict):
                    if "text" in part:
                        parts.append(
                            str(part["text"])
                        )

            content = "".join(parts)

        if not content:
            raise RuntimeError(
                "Nemotron 返回空白內容。"
            )

        return str(content)

    raise RuntimeError(
        "OpenRouter 呼叫失敗。"
    )


# =========================================================
# 3. 世界資料
# =========================================================

LOCATIONS = [
    {
        "loc": "凡間·青石鎮",
        "identity": "街頭討生活的落魄孤兒",
        "bg": (
            "你無父無母，只能靠替人跑腿、搬貨與偶爾乞討維生。"
        ),
    },
    {
        "loc": "仙界·凌霄外園",
        "identity": "九霄雲宮最底層雜役",
        "bg": (
            "你每日清掃落花、挑水與處理雜務，"
            "在仙界眾生眼中幾乎毫無地位。"
        ),
    },
    {
        "loc": "妖界·萬妖山脈",
        "identity": "被遺棄在山脈外圍的半妖",
        "bg": (
            "你的血統混雜，因此受到妖族排斥，"
            "只能在危險山林邊緣求生。"
        ),
    },
    {
        "loc": "魔界·黑焰礦區",
        "identity": "最低階的魔鐵礦奴",
        "bg": (
            "你每日挖掘魔鐵，承受魔氣侵蝕與監工驅使，"
            "只求活過今天。"
        ),
    },
    {
        "loc": "靈界·散修坊市",
        "identity": "擺地攤維生的落魄散修",
        "bg": (
            "你的靈根普通，功法殘缺，"
            "平日靠替人尋物與販賣雜物勉強維生。"
        ),
    },
]

BLOODLINES = [
    "鳳凰涅槃血脈",
    "鴻蒙神魔同體印",
    "太古星辰帝君遺脈",
    "九幽妖皇真靈",
    "混沌天脈",
    "太初劍骨",
]

STARTING_ITEMS = [
    {
        "name": "粗布麻衣",
        "count": 1,
        "desc": "洗得發白的粗布衣物，勉強可以遮身。",
    },
    {
        "name": "乾糧",
        "count": 2,
        "desc": "粗糙乾糧，可以暫時填飽肚子。",
    },
    {
        "name": "清水",
        "count": 1,
        "desc": "一小壺普通清水。",
    },
]

DEFAULT_OPTIONS = [
    "仔細觀察附近環境，尋找新的線索。",
    "主動與附近的人交談，試探對方的目的。",
    "暫時避開人群，找一個安全地方思考下一步。",
    "冒險靠近剛才發現的異常之處。",
]


# =========================================================
# 4. 初始化
# =========================================================

def init_game(player_name):
    location = random.choice(LOCATIONS)

    player_name = str(
        player_name
    ).strip() or "詩柔"

    state = {
        "version": "V3.5",
        "turn": 0,
        "processing": False,

        "player": {
            "name": player_name,
            "identity": (
                location["loc"]
                + "·"
                + location["identity"]
            ),
            "secret_bloodline": random.choice(
                BLOODLINES
            ),
            "bloodline_awakened": False,
            "hp": 100,
            "max_hp": 100,
            "mp": 30,
            "max_mp": 30,
            "fullness": 90,
            "money": 5,
            "realm": "凡俗之軀",
            "location": location["loc"],
            "status": "健康",
            "comprehension": random.randint(8, 12),
            "fortune": random.randint(8, 12),
            "charm": random.randint(8, 12),
            "righteousness": 0,
            "evil_aura": 0,
            "fame": 0,
        },

        "inventory": [
            dict(item)
            for item in STARTING_ITEMS
        ],

        "npcs": {},

        "story_summary": (
            "你從一無所有開始，身處"
            + location["loc"]
            + "，身上只有五文錢，尚未踏入真正的修仙之路。"
        ),

        "story_history": [],
        "current_options": [],
        "last_action": "",
        "last_story": "",
    }

    opening_story = (
        f"你睜開眼睛。\n\n"
        f"晨霧尚未散去，冰冷的空氣貼著你的臉頰。"
        f"你躺在{location['loc']}一處不起眼的角落，"
        f"身上的粗布麻衣沾滿塵土。\n\n"
        f"你是【{player_name}】。\n\n"
        f"如今的你，只是{location['identity']}。"
        f"{location['bg']}\n\n"
        f"你摸遍全身，只找到五文錢。\n\n"
        f"五文錢，在這個弱肉強食的世界裡，"
        f"甚至不足以換來一頓像樣的飯。\n\n"
        f"遠處傳來鐘聲。"
        f"街道上的人開始活動，新的日子又一次開始。\n\n"
        f"然而你不知道的是——"
        f"就在你醒來之前，命運已經悄然替你推開了一扇門。\n\n"
        f"只是那扇門後面究竟是機緣，還是死路，"
        f"尚無人知曉。"
    )

    state["story_history"].append(
        opening_story
    )

    state["current_options"] = [
        "仔細觀察四周，先弄清楚自己身處何地。",
        "檢查身上的物品，看看是否有遺漏的東西。",
        "觀察附近的人群，尋找可以賺錢或獲得食物的機會。",
        "找一個偏僻角落，暗中觀察附近是否藏有異常。",
        "查看狀態",
    ]

    st.session_state.game_state = state
    st.session_state.game_started = True


# =========================================================
# 5. 數值
# =========================================================

def clamp(value, minimum, maximum):
    try:
        value = int(value)
    except Exception:
        value = minimum

    return max(
        minimum,
        min(maximum, value)
    )


def get_status_text(player):
    hp = player.get("hp", 100)
    fullness = player.get("fullness", 90)

    if hp <= 0:
        return "瀕死"

    if hp < 15:
        return "重傷，生命垂危"

    if fullness < 15:
        return "極度飢餓"

    if fullness < 30:
        return "飢餓"

    return "健康"


def normalise_player(player):
    player["max_hp"] = max(
        1,
        int(player.get("max_hp", 100))
    )

    player["max_mp"] = max(
        0,
        int(player.get("max_mp", 30))
    )

    player["hp"] = clamp(
        player.get("hp", 100),
        0,
        player["max_hp"]
    )

    player["mp"] = clamp(
        player.get("mp", 30),
        0,
        player["max_mp"]
    )

    player["fullness"] = clamp(
        player.get("fullness", 90),
        0,
        100
    )

    try:
        player["money"] = max(
            0,
            int(player.get("money", 0))
        )
    except Exception:
        player["money"] = 0

    for key in [
        "comprehension",
        "fortune",
        "charm",
        "righteousness",
        "evil_aura",
        "fame",
    ]:
        try:
            player[key] = int(
                player.get(key, 0)
            )
        except Exception:
            player[key] = 0

    player["status"] = get_status_text(player)


# =========================================================
# 6. AI System Prompt
# =========================================================

SYSTEM_PROMPT = """
你是《三界奇譚》的專業修仙 RPG 遊戲主持人。

你負責根據玩家的行動推進劇情。

【語言】
全程使用繁體中文。
劇情、人物對話、選項全部使用繁體中文。
不要使用英文。
不要輸出 Markdown。

【敘事】
使用第二人稱「你」。
採用古典修仙小說風格。
故事必須有畫面感。
人物必須有自己的性格、目的、秘密與利益。

【世界】
這是一個危險的修仙世界。
凡人、修士、妖族、魔族、仙人都可能互相利用。
不要把所有人物寫成善良。
不要讓所有事件都變成機緣。
機緣可以是陷阱。
幫助可以帶有代價。
NPC 可以說謊。

【玩家】
玩家不是天生無敵。
開局非常弱。
玩家的隱藏血脈絕對不能在沒有合理劇情觸發之前直接說出。

【劇情】
每次行動必須推進新的劇情。
不要重複上一段。
不要把玩家上一個選項原封不動再寫一次。
不要一直停留在觀察。
事件必須真正發生。

如果玩家觀察：
必須得到新的資訊。

如果玩家交涉：
NPC 必須回應。

如果玩家探索：
必須得到結果。

如果玩家冒險：
必須承擔合理風險。

如果玩家戰鬥：
必須根據雙方實力判定結果。

【回合】
每次只推進一個回合。
不要自行增加回合數。
不要輸出第幾回合。

【選項】
每次提供四個新的行動選項。
第五個由遊戲程式固定加入查看狀態。

四個選項應該盡量具有不同策略：
探索、交涉、冒險、戰鬥、利益交換、逃避、觀察等。

【數值】
只可以提出變化。
不要重新建立完整玩家狀態。
不要修改玩家姓名。
不要修改隱藏血脈。
不要自行增加不存在的屬性。

【重要】
所有數值變化必須合理。
不要每次都給玩家巨大機緣。
不要無故令玩家死亡。

【輸出】
只可以輸出合法 JSON。
不要輸出 Markdown。
不要輸出程式碼。
不要輸出三個反引號。
不要輸出 JSON 以外的說明。

格式：

{
    "story": "新的劇情",
    "story_summary_update": "簡短摘要",
    "options": [
        "行動一",
        "行動二",
        "行動三",
        "行動四"
    ],
    "player_update": {
        "hp_change": 0,
        "mp_change": 0,
        "fullness_change": 0,
        "money_change": 0,
        "realm": "維持不變",
        "location": "維持不變",
        "status": "健康"
    },
    "inventory_changes": [],
    "npc_updates": []
}
"""


# =========================================================
# 7. AI 輸出清理
# =========================================================

def clean_model_text(text):
    if not text:
        return ""

    text = str(text).strip()

    text = re.sub(
        r"^```(?:json|JSON)?",
        "",
        text
    )

    text = text.replace(
        "```",
        ""
    ).strip()

    first = text.find("{")

    if first > 0:
        text = text[first:]

    last = text.rfind("}")

    if last >= 0:
        text = text[:last + 1]

    return text.strip()


def parse_json_response(text):
    cleaned = clean_model_text(text)

    if not cleaned:
        return None

    try:
        data = json.loads(cleaned)

        if isinstance(data, dict):
            return data

    except Exception:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start >= 0 and end > start:
        try:
            data = json.loads(
                cleaned[start:end + 1]
            )

            if isinstance(data, dict):
                return data

        except Exception:
            pass

    return None


# =========================================================
# 8. 建立 Prompt
# =========================================================

def build_game_prompt(action):
    game = st.session_state.game_state
    player = game["player"]

    recent_history = game.get(
        "story_history",
        []
    )[-10:]

    recent_text = "\n\n".join(
        str(x)
        for x in recent_history
    )

    npc_text = json.dumps(
        game.get("npcs", {}),
        ensure_ascii=False
    )

    inventory_text = json.dumps(
        game.get("inventory", []),
        ensure_ascii=False
    )

    player_text = json.dumps(
        player,
        ensure_ascii=False
    )

    return f"""
【遊戲目前資料】

【劇情摘要】
{game.get("story_summary", "")}

【最近劇情】
{recent_text}

【玩家資料】
{player_text}

【背包】
{inventory_text}

【人物關係】
{npc_text}

【上一個玩家行動】
{action}

【重要】
上一個玩家行動已經發生。

現在必須讓故事繼續向前發展。

不要重新描述相同事件。

如果玩家只是觀察，
必須得到新的資訊。

如果玩家交涉，
讓 NPC 回應。

如果玩家探索，
讓探索得到結果。

如果玩家冒險，
讓冒險產生合理風險。

如果玩家做出明顯危險行動，
可以讓玩家受傷、失去物品或金錢。

如果玩家成功，
也不應該每次都直接得到巨大機緣。

請按照系統指定 JSON 格式輸出。
"""


# =========================================================
# 9. 套用玩家變化
# =========================================================

def apply_player_changes(data):
    game = st.session_state.game_state
    player = game["player"]

    update = data.get(
        "player_update",
        {}
    )

    if not isinstance(update, dict):
        return

    def to_int(value):
        try:
            return int(value)
        except Exception:
            return 0

    player["hp"] += to_int(
        update.get("hp_change", 0)
    )

    player["mp"] += to_int(
        update.get("mp_change", 0)
    )

    player["fullness"] += to_int(
        update.get("fullness_change", 0)
    )

    player["money"] += to_int(
        update.get("money_change", 0)
    )

    realm = str(
        update.get("realm", "")
    ).strip()

    if realm and realm != "維持不變":
        player["realm"] = realm

    location = str(
        update.get("location", "")
    ).strip()

    if location and location != "維持不變":
        player["location"] = location

    normalise_player(player)


# =========================================================
# 10. 背包
# =========================================================

def apply_inventory_changes(data):
    game = st.session_state.game_state

    changes = data.get(
        "inventory_changes",
        []
    )

    if not isinstance(changes, list):
        return

    inventory = game["inventory"]

    for change in changes:
        if not isinstance(change, dict):
            continue

        name = str(
            change.get("name", "")
        ).strip()

        if not name:
            continue

        try:
            amount = int(
                change.get(
                    "count_change",
                    0
                )
            )
        except Exception:
            amount = 0

        if amount == 0:
            continue

        found = next(
            (
                item for item in inventory
                if item.get("name") == name
            ),
            None
        )

        if found:
            found["count"] = (
                int(found.get("count", 0))
                + amount
            )

            if found["count"] <= 0:
                inventory.remove(found)

        elif amount > 0:
            inventory.append(
                {
                    "name": name,
                    "count": amount,
                    "desc": str(
                        change.get(
                            "desc",
                            "未知物品"
                        )
                    ),
                }
            )


# =========================================================
# 11. NPC
# =========================================================

def apply_npc_updates(data):
    game = st.session_state.game_state

    updates = data.get(
        "npc_updates",
        []
    )

    if not isinstance(updates, list):
        return

    for npc in updates:
        if not isinstance(npc, dict):
            continue

        name = str(
            npc.get("name", "")
        ).strip()

        if not name:
            continue

        old = game["npcs"].get(
            name,
            {}
        )

        try:
            affinity = int(
                npc.get(
                    "affinity",
                    old.get("affinity", 0)
                )
            )
        except Exception:
            affinity = int(
                old.get("affinity", 0)
            )

        game["npcs"][name] = {
            "name": name,
            "identity": npc.get(
                "identity",
                old.get("identity", "未知")
            ),
            "relationship": npc.get(
                "relationship",
                old.get("relationship", "陌生")
            ),
            "affinity": affinity,
            "key_memory": npc.get(
                "key_memory",
                old.get("key_memory", "")
            ),
        }


# =========================================================
# 12. 防重複劇情
# =========================================================

def is_duplicate_story(new_story):
    game = st.session_state.game_state

    if not new_story:
        return True

    old_story = game.get(
        "last_story",
        ""
    )

    if not old_story:
        return False

    a = re.sub(
        r"\s+",
        "",
        str(new_story)
    )

    b = re.sub(
        r"\s+",
        "",
        str(old_story)
    )

    if a == b:
        return True

    if len(a) < 80 or len(b) < 80:
        return False

    return SequenceMatcher(
        None,
        a,
        b
    ).ratio() > 0.82


# =========================================================
# 13. JSON 修復
# =========================================================

def repair_ai_json(messages, raw):
    repair_prompt = """
你上一個回答不是合法 JSON。

請立即重新輸出完整合法 JSON。

不要輸出 Markdown。
不要輸出三個反引號。
不要輸出說明。
不要輸出英文。

必須包含：

{
    "story": "劇情",
    "story_summary_update": "摘要",
    "options": [
        "選項一",
        "選項二",
        "選項三",
        "選項四"
    ],
    "player_update": {
        "hp_change": 0,
        "mp_change": 0,
        "fullness_change": 0,
        "money_change": 0,
        "realm": "維持不變",
        "location": "維持不變",
        "status": "健康"
    },
    "inventory_changes": [],
    "npc_updates": []
}
"""

    repair_messages = list(messages)

    repair_messages.append(
        {
            "role": "assistant",
            "content": str(raw)[:7000],
        }
    )

    repair_messages.append(
        {
            "role": "user",
            "content": repair_prompt,
        }
    )

    repaired = call_nemotron(
        repair_messages
    )

    return parse_json_response(
        repaired
    )


# =========================================================
# 14. 取得 AI 劇情
# =========================================================

def generate_turn(action):
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": build_game_prompt(action),
        },
    ]

    raw = call_nemotron(messages)

    data = parse_json_response(raw)

    if data is not None:
        return data

    # JSON 修復
    data = repair_ai_json(
        messages,
        raw
    )

    if data is None:
        raise RuntimeError(
            "模型連續兩次沒有回傳有效 JSON。"
        )

    return data


# =========================================================
# 15. 取得選項
# =========================================================

def normalise_options(options):
    valid = []

    if isinstance(options, list):
        for option in options:
            option = str(option).strip()

            if option and option not in valid:
                valid.append(option)

    while len(valid) < 4:
        fallback = DEFAULT_OPTIONS[
            len(valid) % len(DEFAULT_OPTIONS)
        ]

        if fallback not in valid:
            valid.append(fallback)
        else:
            valid.append(
                "繼續尋找下一步的機會。"
            )

    return valid[:4] + ["查看狀態"]


# =========================================================
# 16. 處理回合
# =========================================================

def process_turn(action):
    game = st.session_state.game_state

    if game.get("processing", False):
        return False

    action = str(action).strip()

    if not action:
        return False

    # -----------------------------------------------------
    # 查看狀態不需要 AI
    # -----------------------------------------------------

    if action.startswith("查看狀態"):
        player = game["player"]

        status_story = (
            "你暫時停下腳步。\n\n"
            "你仔細整理自己的狀態。\n\n"
            f"目前生命狀態為【"
            f"{player['hp']}/{player['max_hp']}】。\n"
            f"體內靈力為【"
            f"{player['mp']}/{player['max_mp']}】。\n"
            f"飽腹程度為【"
            f"{player['fullness']}/100】。\n"
            f"身上共有【"
            f"{player['money']}文錢】。\n\n"
            f"目前境界：{player['realm']}。\n"
            f"目前位置：{player['location']}。\n"
            f"目前狀態：{player['status']}。"
        )

        game["story_history"].append(
            status_story
        )

        game["last_action"] = action

        return True

    # -----------------------------------------------------
    # 開始 AI processing
    # -----------------------------------------------------

    game["processing"] = True

    old_turn = game.get("turn", 0)

    try:
        with st.spinner(
            "🔮 命運正在推演……"
        ):
            data = generate_turn(action)

        story = str(
            data.get(
                "story",
                ""
            )
        ).strip()

        if not story:
            raise RuntimeError(
                "模型返回了空白劇情。"
            )

        # -------------------------------------------------
        # 如果重複，重新生成一次
        # -------------------------------------------------

        if is_duplicate_story(story):
            retry_messages = [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": (
                        build_game_prompt(action)
                        + """

上一個生成結果與上一回合過於相似。

這一次必須發生新的事件。

不要重複相同描述。
不要重新描述玩家剛才做過的事情。
必須讓劇情真正向前發展。

只輸出指定 JSON。
"""
                    ),
                },
            ]

            try:
                retry_raw = call_nemotron(
                    retry_messages
                )

                retry_data = parse_json_response(
                    retry_raw
                )

                if retry_data:
                    retry_story = str(
                        retry_data.get(
                            "story",
                            ""
                        )
                    ).strip()

                    if retry_story:
                        data = retry_data
                        story = retry_story

            except Exception:
                # 重試失敗就保留原本有效結果
                pass

        # -------------------------------------------------
        # 只有 AI 成功後先正式增加回合
        # -------------------------------------------------

        game["turn"] = old_turn + 1

        apply_player_changes(data)
        apply_inventory_changes(data)
        apply_npc_updates(data)

        player = game["player"]

        # 飢餓
        if player["fullness"] < 15:
            player["hp"] = max(
                0,
                player["hp"] - 5
            )

            story += (
                "\n\n【生存危機】\n"
                "你的腹中空空如也，"
                "飢餓感開始侵蝕體力。"
                "本次行動額外損失五點生命。"
            )

        normalise_player(player)

        # -------------------------------------------------
        # 摘要
        # -------------------------------------------------

        summary = str(
            data.get(
                "story_summary_update",
                ""
            )
        ).strip()

        if summary:
            game["story_summary"] = summary[:800]

        # -------------------------------------------------
        # 記錄
        # -------------------------------------------------

        game["story_history"].append(
            f"【第 {game['turn']} 回合】\n"
            f"你選擇：{action}"
        )

        game["story_history"].append(
            story
        )

        game["last_action"] = action
        game["last_story"] = story

        # -------------------------------------------------
        # 歷史限制
        # -------------------------------------------------

        if len(game["story_history"]) > 50:
            game["story_history"] = (
                game["story_history"][-50:]
            )

        # -------------------------------------------------
        # 選項
        # -------------------------------------------------

        game["current_options"] = normalise_options(
            data.get("options", [])
        )

        return True

    except Exception as error:
        # -------------------------------------------------
        # AI 失敗
        # -------------------------------------------------

        game["turn"] = old_turn

        st.error(
            "⚠️ 命運推演失敗\n\n"
            + str(error)
        )

        st.info(
            "你的回合沒有被消耗。"
            "可以稍後再試一次。"
        )

        return False

    finally:
        game["processing"] = False


# =========================================================
# 17. 短存檔
# =========================================================

def create_save():
    game = st.session_state.game_state

    save_data = {
        "v": "3.5",
        "t": game.get("turn", 0),
        "p": game.get("player", {}),
        "i": game.get("inventory", []),
        "n": game.get("npcs", {}),
        "s": game.get("story_summary", ""),
        "h": game.get("story_history", []),
        "o": game.get("current_options", []),
        "a": game.get("last_action", ""),
        "l": game.get("last_story", ""),
    }

    raw = json.dumps(
        save_data,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return base64.b64encode(
        raw.encode("utf-8")
    ).decode("ascii")


# =========================================================
# 18. 讀檔
# =========================================================

def load_save(save_string):
    save_string = str(
        save_string
    ).strip()

    if not save_string:
        raise ValueError(
            "存檔內容是空白的。"
        )

    data = None

    # Base64
    try:
        decoded = base64.b64decode(
            save_string,
            validate=True
        ).decode("utf-8")

        data = json.loads(decoded)

    except Exception:
        pass

    # 舊 JSON
    if data is None:
        try:
            data = json.loads(
                save_string
            )
        except Exception as error:
            raise ValueError(
                "無法讀取存檔格式："
                + str(error)
            )

    # -----------------------------------------------------
    # 短格式
    # -----------------------------------------------------

    if isinstance(data, dict) and "p" in data:
        game_state = {
            "version": data.get(
                "v",
                "3.5"
            ),
            "turn": data.get(
                "t",
                0
            ),
            "processing": False,
            "player": data.get(
                "p",
                {}
            ),
            "inventory": data.get(
                "i",
                []
            ),
            "npcs": data.get(
                "n",
                {}
            ),
            "story_summary": data.get(
                "s",
                ""
            ),
            "story_history": data.get(
                "h",
                []
            ),
            "current_options": data.get(
                "o",
                []
            ),
            "last_action": data.get(
                "a",
                ""
            ),
            "last_story": data.get(
                "l",
                ""
            ),
        }

    else:
        # 舊 V3.3 / V3.4
        game_state = (
            data.get("game_state")
            if isinstance(data, dict)
            else None
        )

        if not isinstance(
            game_state,
            dict
        ):
            raise ValueError(
                "找不到有效遊戲資料。"
            )

    # -----------------------------------------------------
    # 補資料
    # -----------------------------------------------------

    game_state.setdefault(
        "version",
        "3.5"
    )

    game_state.setdefault(
        "turn",
        0
    )

    game_state.setdefault(
        "processing",
        False
    )

    game_state.setdefault(
        "story_history",
        []
    )

    game_state.setdefault(
        "npcs",
        {}
    )

    game_state.setdefault(
        "inventory",
        []
    )

    game_state.setdefault(
        "story_summary",
        ""
    )

    game_state.setdefault(
        "current_options",
        []
    )

    game_state.setdefault(
        "last_action",
        ""
    )

    game_state.setdefault(
        "last_story",
        ""
    )

    player = game_state.setdefault(
        "player",
        {}
    )

    defaults = {
        "name": "詩柔",
        "identity": "凡間·落魄孤兒",
        "secret_bloodline": random.choice(
            BLOODLINES
        ),
        "bloodline_awakened": False,
        "max_hp": 100,
        "max_mp": 30,
        "hp": 100,
        "mp": 30,
        "fullness": 90,
        "money": 5,
        "realm": "凡俗之軀",
        "location": "凡間·青石鎮",
        "status": "健康",
        "comprehension": 10,
        "fortune": 10,
        "charm": 10,
        "righteousness": 0,
        "evil_aura": 0,
        "fame": 0,
    }

    for key, value in defaults.items():
        player.setdefault(
            key,
            value
        )

    normalise_player(player)

    game_state["processing"] = False

    if not game_state["current_options"]:
        game_state["current_options"] = (
            DEFAULT_OPTIONS
            + ["查看狀態"]
        )

    st.session_state.game_state = (
        game_state
    )

    st.session_state.game_started = True


# =========================================================
# 19. Session
# =========================================================

if "game_started" not in st.session_state:
    st.session_state.game_started = False

if "game_state" not in st.session_state:
    st.session_state.game_state = None


# =========================================================
# 20. 開始畫面
# =========================================================

st.title(
    "🌸 三界奇譚：小薯逆襲記"
)

st.caption(
    "V3.5 · Nemotron Free · 修仙文字 RPG"
)


if not st.session_state.game_started:

    st.subheader(
        "🎲 踏入命途"
    )

    st.write(
        "你將從五文錢開始，在三界之中一步一步尋找自己的道路。"
    )

    with st.form(
        "start_game_form"
    ):
        player_name = st.text_input(
            "請輸入你的名字",
            value="詩柔"
        )

        start_button = st.form_submit_button(
            "🌸 開始新人生",
            use_container_width=True
        )

        if start_button:
            init_game(player_name)
            st.rerun()

    st.markdown("---")

    st.subheader(
        "💾 讀取舊存檔"
    )

    load_code = st.text_area(
        "貼上之前保存的存檔代碼",
        height=120
    )

    if st.button(
        "📂 載入存檔",
        use_container_width=True
    ):
        if load_code.strip():
            try:
                load_save(
                    load_code.strip()
                )

                st.success(
                    "存檔載入成功！"
                )

                st.rerun()

            except Exception as error:
                st.error(
                    "存檔無效："
                    + str(error)
                )

    st.stop()


# =========================================================
# 21. Game
# =========================================================

game = st.session_state.game_state
player = game["player"]

normalise_player(player)


# =========================================================
# 22. Sidebar
# =========================================================

with st.sidebar:

    st.header(
        "📌 逆襲狀態"
    )

    st.write(
        "👤 " + str(player["name"])
    )

    st.write(
        "🏷️ " + str(player["realm"])
    )

    st.write(
        "📍 " + str(player["location"])
    )

    st.write(
        "📖 第 "
        + str(game["turn"])
        + " 回合"
    )

    st.markdown("---")

    col1, col2 = st.columns(2)

    col1.metric(
        "❤️ 生命",
        f"{player['hp']}/{player['max_hp']}"
    )

    col2.metric(
        "💙 靈力",
        f"{player['mp']}/{player['max_mp']}"
    )

    col3, col4 = st.columns(2)

    col3.metric(
        "🍚 飽腹",
        f"{player['fullness']}/100"
    )

    col4.metric(
        "💰 金錢",
        f"{player['money']} 文"
    )

    st.markdown("---")

    with st.expander(
        "📊 詳細屬性",
        expanded=True
    ):
        st.write(
            "🧠 悟性："
            + str(player["comprehension"])
        )

        st.write(
            "🎲 福緣："
            + str(player["fortune"])
        )

        st.write(
            "✨ 魅力："
            + str(player["charm"])
        )

        st.write(
            "⚖️ 正氣："
            + str(player["righteousness"])
        )

        st.write(
            "🩸 煞氣："
            + str(player["evil_aura"])
        )

        st.write(
            "👑 威名："
            + str(player["fame"])
        )

    if player.get(
        "bloodline_awakened",
        False
    ):
        st.success(
            "🔥 隱藏血脈已覺醒："
            + str(
                player.get(
                    "secret_bloodline",
                    "未知"
                )
            )
        )
    else:
        st.info(
            "🔒 身世之謎尚未揭開"
        )

    st.markdown("---")

    page = st.radio(
        "🗂️ 遊戲功能",
        [
            "📖 主線劇情",
            "🎒 背包",
            "👥 人物關係",
            "💾 存檔／讀檔",
        ],
    )

    st.markdown("---")

    if st.button(
        "🔄 重開新局",
        use_container_width=True
    ):
        st.session_state.game_started = False
        st.session_state.game_state = None
        st.rerun()


# =========================================================
# 23. 主線劇情
# =========================================================

if page == "📖 主線劇情":

    st.subheader(
        "📖 主線劇情"
    )

    # -----------------------------------------------------
    # 固定右下角按鈕
    # -----------------------------------------------------

    st.markdown(
        """
        <style>

        .rpg-bottom-link {
            position: fixed !important;
            right: 24px !important;
            bottom: 24px !important;
            z-index: 999999 !important;

            display: inline-block !important;

            padding: 10px 16px !important;

            border-radius: 24px !important;

            background: white !important;

            border: 1px solid #cccccc !important;

            box-shadow:
                0 3px 12px rgba(0,0,0,0.22) !important;

            color: #333333 !important;

            text-decoration: none !important;

            font-size: 14px !important;

            font-weight: 600 !important;

            cursor: pointer !important;
        }

        .rpg-bottom-link:hover {
            background: #f5f5f5 !important;
            transform: translateY(-2px);
        }

        </style>

        <a
            class="rpg-bottom-link"
            href="#rpg-story-bottom"
        >
            ⬇️ 到最底
        </a>
        """,
        unsafe_allow_html=True
    )

    # -----------------------------------------------------
    # 劇情
    # -----------------------------------------------------

    for text in game.get(
        "story_history",
        []
    ):

        if str(text).startswith(
            "【第 "
        ):
            st.info(text)
        else:
            st.write(text)

    # -----------------------------------------------------
    # 真正底部 anchor
    # -----------------------------------------------------

    st.markdown(
        '<div id="rpg-story-bottom"></div>',
        unsafe_allow_html=True
    )

    st.markdown("---")

    st.write(
        "✨ **你打算怎麼做？**"
    )

    options = game.get(
        "current_options",
        []
    )

    if not options:
        options = (
            DEFAULT_OPTIONS
            + ["查看狀態"]
        )

        game["current_options"] = options

    # -----------------------------------------------------
    # 選項
    # -----------------------------------------------------

    for idx, option in enumerate(options):

        button_key = (
            "v35_turn_"
            + str(game["turn"])
            + "_option_"
            + str(idx)
        )

        if st.button(
            option,
            key=button_key,
            use_container_width=True,
            disabled=game.get(
                "processing",
                False
            ),
        ):
            success = process_turn(
                option
            )

            if success:
                st.rerun()

    st.markdown("---")

    # -----------------------------------------------------
    # 自由行動
    # -----------------------------------------------------

    st.write(
        "💬 **自由行動**"
    )

    custom_action = st.text_input(
        "你可以輸入任何想做的事情",
        key="custom_action_input",
        disabled=game.get(
            "processing",
            False
        )
    )

    if st.button(
        "✍️ 執行自由行動",
        use_container_width=True,
        disabled=game.get(
            "processing",
            False
        ),
    ):

        if custom_action.strip():

            success = process_turn(
                custom_action.strip()
            )

            if success:
                st.rerun()

        else:
            st.warning(
                "請先輸入你想做的事情。"
            )


# =========================================================
# 24. 背包
# =========================================================

elif page == "🎒 背包":

    st.subheader(
        "🎒 我的背包"
    )

    inventory = game.get(
        "inventory",
        []
    )

    if not inventory:
        st.info(
            "你的背包空空如也。"
        )

    else:
        for item in inventory:

            name = item.get(
                "name",
                "未知物品"
            )

            count = item.get(
                "count",
                0
            )

            desc = item.get(
                "desc",
                ""
            )

            with st.container(
                border=True
            ):
                st.write(
                    f"### {name} × {count}"
                )

                st.write(
                    str(desc)
                )


# =========================================================
# 25. NPC
# =========================================================

elif page == "👥 人物關係":

    st.subheader(
        "👥 三界人物關係"
    )

    npcs = game.get(
        "npcs",
        {}
    )

    if not npcs:
        st.info(
            "目前尚未正式結識任何重要人物。"
        )

    else:
        for name, npc in npcs.items():

            affinity = npc.get(
                "affinity",
                0
            )

            with st.expander(
                "🌸 "
                + str(name)
                + "｜好感："
                + str(affinity)
            ):

                st.write(
                    "身份："
                    + str(
                        npc.get(
                            "identity",
                            "未知"
                        )
                    )
                )

                st.write(
                    "關係："
                    + str(
                        npc.get(
                            "relationship",
                            "未知"
                        )
                    )
                )

                st.write(
                    "記憶："
                    + str(
                        npc.get(
                            "key_memory",
                            "暫無"
                        )
                    )
                )


# =========================================================
# 26. 存檔／讀檔
# =========================================================

elif page == "💾 存檔／讀檔":

    st.subheader(
        "💾 存檔／讀檔"
    )

    st.write(
        "新版存檔使用較短的 Base64 格式，"
        "直接完整複製即可。"
    )

    save_string = create_save()

    st.text_area(
        "📋 當前存檔",
        value=save_string,
        height=150
    )

    st.caption(
        "請完整複製以上代碼，不要修改內容。"
    )

    st.markdown("---")

    st.write(
        "📥 載入之前的存檔"
    )

    load_string = st.text_area(
        "貼上存檔",
        height=150,
        key="load_save_area"
    )

    if st.button(
        "🔄 確認載入",
        use_container_width=True
    ):

        if load_string.strip():

            try:
                load_save(
                    load_string.strip()
                )

                st.success(
                    "載入成功！"
                )

                time.sleep(0.3)

                st.rerun()

            except Exception as error:

                st.error(
                    "載入失敗："
                    + str(error)
                )

        else:

            st.warning(
                "請先貼上存檔內容。"
            )


# =========================================================
# 27. Footer
# =========================================================

st.markdown("---")

st.caption(
    "三界奇譚 V3.5 · Nemotron Free · 修仙文字 RPG"
)
