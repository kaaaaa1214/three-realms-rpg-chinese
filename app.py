import streamlit as st
import requests
import json
import random
import re
import time
import html


# =========================================================
# V3.4
# 三界奇譚：小薯逆襲記
# =========================================================


# =========================================================
# 1. Streamlit 頁面設定
# =========================================================

st.set_page_config(
    page_title="三界奇譚：小薯逆襲記",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# 2. OpenRouter 設定
# =========================================================

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MODEL_NAME = "nvidia/nemotron-3-ultra-550b-a55b:free"

OPENROUTER_API_KEY = st.secrets.get(
    "OPENROUTER_API_KEY",
    ""
)

if not OPENROUTER_API_KEY:
    st.error(
        "⚠️ 找不到 OPENROUTER_API_KEY。\n\n"
        "請到 Streamlit Cloud → Settings → Secrets 設定。"
    )
    st.stop()


# =========================================================
# 3. 遊戲世界資料
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


# =========================================================
# 4. 初始化遊戲
# =========================================================

def init_game(player_name):

    location = random.choice(LOCATIONS)

    player_name = str(player_name).strip()

    if not player_name:
        player_name = "詩柔"

    comprehension = random.randint(8, 12)
    fortune = random.randint(8, 12)
    charm = random.randint(8, 12)

    state = {
        "version": "V3.4",

        "turn": 0,

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

            "comprehension": comprehension,
            "fortune": fortune,
            "charm": charm,

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
            + "，身上只有五文錢，"
            "尚未踏入真正的修仙之路。"
        ),

        "story_history": [],

        "current_options": [],

        "last_action": "",

        "last_story": "",

        "processing": False,

        # 用來控制返回主線後自動捲到底
        "scroll_to_bottom": True,
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
        f"遠處傳來鐘聲。\n"
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
# 5. 安全數值處理
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
        player["money"] = int(
            player.get("money", 0)
        )
    except Exception:
        player["money"] = 0

    player["money"] = max(
        0,
        player["money"]
    )


# =========================================================
# 6. 狀態文字
# =========================================================

def get_status_text(player):

    hp = player["hp"]
    fullness = player["fullness"]

    if hp <= 0:
        return "瀕死"

    if hp < 15:
        return "重傷，生命垂危"

    if fullness < 15:
        return "極度飢餓"

    if fullness < 30:
        return "飢餓"

    return "健康"


# =========================================================
# 7. 遊戲規則
# =========================================================

SYSTEM_PROMPT = """
你是《三界奇譚》的專業修仙 RPG 遊戲主持人。

你負責根據玩家的行動推進劇情。

【最重要規則】

一、語言

全程使用繁體中文。

劇情、人物對話、選項全部使用繁體中文。

不要使用英文單字。

不要使用英文字母。

不要使用外語。

JSON 的欄位名稱可以按照指定格式使用英文。

二、敘事

使用第二人稱「你」。

採用古典修仙小說風格。

故事必須有畫面感。

人物必須有自己的性格、目的、秘密與利益。

三、世界

這是一個危險的修仙世界。

凡人、修士、妖族、魔族、仙人都可能互相利用。

不要把所有人物寫成善良。

不要讓所有事件都變成機緣。

機緣可以是陷阱。

幫助可以帶有代價。

NPC 可以說謊。

四、玩家

玩家不是天生無敵。

開局非常弱。

玩家的隱藏血脈絕對不能在沒有合理劇情觸發之前直接說出。

五、劇情

每次行動推進一段新的劇情。

不要重複上一段。

不要把玩家上一個選項原封不動再寫一次。

不要一直停留在「你觀察四周」。

事件必須真正發生。

六、回合

每次只推進一個回合。

不要自行增加回合數。

不要輸出第幾回合。

回合數由遊戲程式處理。

七、選項

每次提供四個新的行動選項。

第五個固定是查看狀態。

選項必須有不同策略：

探索、交涉、冒險、戰鬥、利益交換、逃避、觀察等。

八、禁止

不要輸出 Markdown。

不要輸出程式碼。

不要輸出 JSON 以外的內容。

不要輸出程式碼框。

不要輸出 null。

不要輸出 None。

九、輸出

只可以輸出合法 JSON。

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

十、重要

你只負責提出變化。

不要重新建立完整玩家狀態。

不要修改姓名。

不要修改隱藏血脈。

不要自行增加不存在的屬性。
"""


# =========================================================
# 8. 清理模型輸出
# =========================================================

def clean_model_text(text):

    if not text:
        return ""

    text = str(text).strip()

    text = text.replace(
        "```json",
        ""
    )

    text = text.replace(
        "```JSON",
        ""
    )

    text = text.replace(
        "```",
        ""
    )

    text = text.strip()

    first_brace = text.find("{")

    if first_brace > 0:
        text = text[first_brace:]

    last_brace = text.rfind("}")

    if last_brace >= 0:
        text = text[:last_brace + 1]

    return text.strip()


# =========================================================
# 9. 解析 JSON
# =========================================================

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

        candidate = cleaned[
            start:end + 1
        ]

        try:
            data = json.loads(candidate)

            if isinstance(data, dict):
                return data

        except Exception:
            pass

    return None


# =========================================================
# 10. API 錯誤處理
# =========================================================

def get_api_error_message(response):

    status_code = response.status_code

    try:
        data = response.json()

        error_data = data.get(
            "error",
            {}
        )

        if isinstance(
            error_data,
            dict
        ):
            message = error_data.get(
                "message",
                ""
            )

            if message:
                return str(message)

        return str(data)

    except Exception:

        try:
            return response.text[:1000]
        except Exception:
            return "未知 API 錯誤"


# =========================================================
# 11. 呼叫 Nemotron
# =========================================================

def call_nemotron(messages):

    headers = {
        "Authorization": (
            "Bearer "
            + str(OPENROUTER_API_KEY).strip()
        ),
        "Content-Type": "application/json",
        "Accept": "application/json",

        # OpenRouter 官方建議的額外 header
        "HTTP-Referer": (
            "https://three-realms-rpg-chinese.streamlit.app"
        ),

        "X-Title": "三界奇譚：小薯逆襲記",
    }

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.8,
        "max_tokens": 2500,
    }

    try:

        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=120,
        )

    except UnicodeEncodeError:

        raise RuntimeError(
            "API 請求編碼失敗。\n\n"
            "通常是 HTTP Header 含有非英文字符。\n"
            "V3.4 已將 API Header 全部固定為純英文，"
            "請重新部署後再試。"
        )

    except requests.exceptions.Timeout:

        raise RuntimeError(
            "Nemotron 回應逾時。\n\n"
            "免費模型可能需要較長時間，"
            "請稍後再試。"
        )

    except requests.exceptions.ConnectionError:

        raise RuntimeError(
            "無法連接 OpenRouter。\n\n"
            "請檢查 Streamlit Cloud 網絡或稍後再試。"
        )

    except requests.exceptions.RequestException as error:

        raise RuntimeError(
            "連接 OpenRouter 失敗："
            + str(error)
        )

    # -----------------------------------------------------
    # HTTP 狀態處理
    # -----------------------------------------------------

    if response.status_code == 401:

        raise RuntimeError(
            "OpenRouter API Key 無效或已失效。\n\n"
            "請到 Streamlit Secrets 檢查 "
            "OPENROUTER_API_KEY。"
        )

    if response.status_code == 403:

        raise RuntimeError(
            "OpenRouter 拒絕這次請求。\n\n"
            "可能是 API Key 權限或模型權限問題。"
        )

    if response.status_code == 429:

        raise RuntimeError(
            "⚠️ API 暫時達到使用限制。\n\n"
            "可能是免費模型目前達到速率限制，"
            "並不代表你的遊戲存檔壞了。\n\n"
            "請等一陣子再試。"
        )

    if response.status_code >= 500:

        raise RuntimeError(
            "OpenRouter / 模型服務暫時發生問題。\n\n"
            f"服務回應代碼：{response.status_code}\n\n"
            "請稍後再試。"
        )

    if response.status_code != 200:

        error_message = get_api_error_message(
            response
        )

        raise RuntimeError(
            "OpenRouter API 錯誤 "
            + str(response.status_code)
            + "\n\n"
            + error_message
        )

    # -----------------------------------------------------
    # 解析 API 回應
    # -----------------------------------------------------

    try:

        result = response.json()

    except Exception:

        raise RuntimeError(
            "OpenRouter 回傳的內容不是有效 JSON。"
        )

    choices = result.get(
        "choices"
    )

    if not choices:

        raise RuntimeError(
            "模型沒有返回有效結果。\n\n"
            + str(result)[:1000]
        )

    message = choices[0].get(
        "message",
        {}
    )

    content = message.get(
        "content",
        ""
    )

    if isinstance(
        content,
        list
    ):

        parts = []

        for item in content:

            if isinstance(
                item,
                dict
            ):

                if item.get("type") == "text":

                    parts.append(
                        str(
                            item.get(
                                "text",
                                ""
                            )
                        )
                    )

        content = "".join(parts)

    if not content:

        raise RuntimeError(
            "Nemotron 返回空白內容。"
        )

    return str(content)


# =========================================================
# 12. 建立遊戲 Prompt
# =========================================================

def build_game_prompt(action):

    game = st.session_state.game_state

    player = game["player"]

    recent_history = game[
        "story_history"
    ][-8:]

    recent_text = "\n\n".join(
        str(item)
        for item in recent_history
    )

    npc_text = json.dumps(
        game.get(
            "npcs",
            {}
        ),
        ensure_ascii=False,
    )

    inventory_text = json.dumps(
        game.get(
            "inventory",
            []
        ),
        ensure_ascii=False,
    )

    prompt = f"""
【遊戲目前資料】

【劇情摘要】

{game.get("story_summary", "")}

【最近劇情】

{recent_text}

【玩家資料】

{json.dumps(player, ensure_ascii=False)}

【背包】

{inventory_text}

【人物關係】

{npc_text}

【上一個玩家行動】

{action}

【重要】

上一個玩家行動已經發生。

你現在必須讓故事繼續向前發展。

不要重新描述相同事件。

如果玩家只是觀察，就必須讓觀察得到新的資訊。

如果玩家交涉，就讓 NPC 回應。

如果玩家探索，就讓探索得到結果。

如果玩家冒險，就必須承擔合理風險。

請按照指定 JSON 格式輸出。

只輸出 JSON。
"""

    return prompt


# =========================================================
# 13. 套用玩家數值
# =========================================================

def apply_player_changes(data):

    game = st.session_state.game_state

    player = game["player"]

    update = data.get(
        "player_update",
        {}
    )

    if not isinstance(
        update,
        dict
    ):
        update = {}

    try:
        hp_change = int(
            update.get(
                "hp_change",
                0
            )
        )
    except Exception:
        hp_change = 0

    try:
        mp_change = int(
            update.get(
                "mp_change",
                0
            )
        )
    except Exception:
        mp_change = 0

    try:
        fullness_change = int(
            update.get(
                "fullness_change",
                0
            )
        )
    except Exception:
        fullness_change = 0

    try:
        money_change = int(
            update.get(
                "money_change",
                0
            )
        )
    except Exception:
        money_change = 0

    player["hp"] += hp_change

    player["mp"] += mp_change

    player["fullness"] += fullness_change

    player["money"] += money_change

    realm = update.get(
        "realm"
    )

    if realm:

        realm = str(
            realm
        ).strip()

        if realm != "維持不變":

            player["realm"] = realm

    location = update.get(
        "location"
    )

    if location:

        location = str(
            location
        ).strip()

        if location != "維持不變":

            player["location"] = location

    normalise_player(
        player
    )

    player["status"] = get_status_text(
        player
    )


# =========================================================
# 14. 處理背包
# =========================================================

def apply_inventory_changes(data):

    game = st.session_state.game_state

    changes = data.get(
        "inventory_changes",
        []
    )

    if not isinstance(
        changes,
        list
    ):
        return

    inventory = game.setdefault(
        "inventory",
        []
    )

    for change in changes:

        if not isinstance(
            change,
            dict
        ):
            continue

        name = str(
            change.get(
                "name",
                ""
            )
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

        found = None

        for item in inventory:

            if item.get(
                "name"
            ) == name:

                found = item
                break

        if found:

            try:
                found["count"] = int(
                    found.get(
                        "count",
                        0
                    )
                )
            except Exception:
                found["count"] = 0

            found["count"] += amount

            if found["count"] <= 0:

                inventory.remove(
                    found
                )

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
# 15. 處理 NPC
# =========================================================

def apply_npc_updates(data):

    game = st.session_state.game_state

    updates = data.get(
        "npc_updates",
        []
    )

    if not isinstance(
        updates,
        list
    ):
        return

    npcs = game.setdefault(
        "npcs",
        {}
    )

    for npc in updates:

        if not isinstance(
            npc,
            dict
        ):
            continue

        name = str(
            npc.get(
                "name",
                ""
            )
        ).strip()

        if not name:
            continue

        old = npcs.get(
            name,
            {}
        )

        try:
            affinity = int(
                npc.get(
                    "affinity",
                    old.get(
                        "affinity",
                        0
                    )
                )
            )
        except Exception:

            affinity = old.get(
                "affinity",
                0
            )

        merged = {
            "name": name,

            "identity": npc.get(
                "identity",
                old.get(
                    "identity",
                    "未知"
                )
            ),

            "relationship": npc.get(
                "relationship",
                old.get(
                    "relationship",
                    "陌生"
                )
            ),

            "affinity": affinity,

            "key_memory": npc.get(
                "key_memory",
                old.get(
                    "key_memory",
                    ""
                )
            ),
        }

        npcs[name] = merged


# =========================================================
# 16. 防止重複劇情
# =========================================================

def is_duplicate_story(new_story):

    game = st.session_state.game_state

    if not new_story:
        return True

    last_story = game.get(
        "last_story",
        ""
    )

    if not last_story:
        return False

    clean_a = re.sub(
        r"\s+",
        "",
        str(new_story)
    )

    clean_b = re.sub(
        r"\s+",
        "",
        str(last_story)
    )

    if clean_a == clean_b:
        return True

    if (
        len(clean_a) > 80
        and len(clean_b) > 80
    ):

        check_length = min(
            len(clean_a),
            len(clean_b),
            300
        )

        same_chars = 0

        for i in range(
            check_length
        ):

            if clean_a[i] == clean_b[i]:
                same_chars += 1

        ratio = (
            same_chars
            / max(
                1,
                check_length
            )
        )

        if ratio > 0.85:
            return True

    return False


# =========================================================
# 17. 安全取得選項
# =========================================================

def make_valid_options(
    model_options
):

    valid_options = []

    if isinstance(
        model_options,
        list
    ):

        for option in model_options:

            option = str(
                option
            ).strip()

            if option:

                valid_options.append(
                    option
                )

    default_options = [
        "仔細觀察附近環境，尋找新的線索。",
        "主動與附近的人交談，試探對方的目的。",
        "暫時避開人群，找一個安全地方思考下一步。",
        "冒險靠近剛才發現的異常之處。",
    ]

    while len(valid_options) < 4:

        candidate = default_options[
            len(valid_options)
        ]

        if candidate not in valid_options:

            valid_options.append(
                candidate
            )

        else:

            valid_options.append(
                "暫時保持觀察，尋找新的機會。"
            )

    return valid_options[:4] + [
        "查看狀態"
    ]


# =========================================================
# 18. API JSON 修復
# =========================================================

def repair_json_response(
    messages,
    raw
):

    repair_prompt = """
你上一個回答不是合法 JSON。

請重新輸出。

只可以輸出合法 JSON。

不可輸出 Markdown。

不可輸出程式碼框。

不可輸出說明文字。

劇情內容必須使用繁體中文。

格式：

{
"story":"劇情",
"story_summary_update":"摘要",
"options":["選項一","選項二","選項三","選項四"],
"player_update":{
"hp_change":0,
"mp_change":0,
"fullness_change":0,
"money_change":0,
"realm":"維持不變",
"location":"維持不變",
"status":"健康"
},
"inventory_changes":[],
"npc_updates":[]
}
"""

    repair_messages = list(
        messages
    )

    repair_messages.append(
        {
            "role": "assistant",
            "content": str(raw)[:8000],
        }
    )

    repair_messages.append(
        {
            "role": "user",
            "content": repair_prompt,
        }
    )

    repaired_raw = call_nemotron(
        repair_messages
    )

    return parse_json_response(
        repaired_raw
    )


# =========================================================
# 19. 處理一個玩家回合
# =========================================================

def process_turn(action):

    game = st.session_state.game_state

    if game.get(
        "processing",
        False
    ):
        return

    action = str(
        action
    ).strip()

    if not action:
        return

    # -----------------------------------------------------
    # 查看狀態
    # -----------------------------------------------------

    if action.startswith(
        "查看狀態"
    ):

        player = game["player"]

        status_story = (
            "你暫時停下腳步。\n\n"
            "你仔細整理自己的狀態。\n\n"
            f"目前生命狀態為【"
            f"{player['hp']}/"
            f"{player['max_hp']}】。\n"
            f"體內靈力為【"
            f"{player['mp']}/"
            f"{player['max_mp']}】。\n"
            f"飽腹程度為【"
            f"{player['fullness']}/100】。\n"
            f"身上共有【"
            f"{player['money']}文錢】。\n\n"
            f"目前境界："
            f"{player['realm']}。\n"
            f"目前位置："
            f"{player['location']}。\n"
            f"目前狀態："
            f"{player['status']}。"
        )

        game["story_history"].append(
            status_story
        )

        game["last_action"] = action

        game["scroll_to_bottom"] = True

        return

    # -----------------------------------------------------
    # 防止重複處理
    # -----------------------------------------------------

    game["processing"] = True

    try:

        game["turn"] += 1

        game["scroll_to_bottom"] = True

        prompt = build_game_prompt(
            action
        )

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]

        # -------------------------------------------------
        # 第一次 API
        # -------------------------------------------------

        with st.spinner(
            "🔮 命運正在推演……"
        ):

            raw = call_nemotron(
                messages
            )

        data = parse_json_response(
            raw
        )

        # -------------------------------------------------
        # JSON 修復
        # -------------------------------------------------

        if data is None:

            with st.spinner(
                "📜 正在整理命運卷軸……"
            ):

                data = repair_json_response(
                    messages,
                    raw
                )

        if data is None:

            raise RuntimeError(
                "模型連續兩次沒有回傳有效 JSON。\n\n"
                "請稍後再試。"
            )

        # -------------------------------------------------
        # 取得劇情
        # -------------------------------------------------

        story = str(
            data.get(
                "story",
                ""
            )
        ).strip()

        if not story:

            story = (
                "你停下腳步。\n\n"
                "周圍的氣氛似乎比剛才更加微妙。"
                "你沒有貿然行動，"
                "而是重新思考下一步。"
            )

        # -------------------------------------------------
        # 防止重複
        # -------------------------------------------------

        if is_duplicate_story(
            story
        ):

            retry_prompt = (
                build_game_prompt(
                    action
                )
                + """

上一個生成結果與上一回合過於相似。

這一次必須發生新的事件。

不要重複相同描述。

必須讓劇情真正前進。

只輸出指定 JSON。
"""
            )

            retry_messages = [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": retry_prompt,
                },
            ]

            with st.spinner(
                "🔮 命運正在重新推演……"
            ):

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

        # -------------------------------------------------
        # 套用玩家變化
        # -------------------------------------------------

        apply_player_changes(
            data
        )

        apply_inventory_changes(
            data
        )

        apply_npc_updates(
            data
        )

        # -------------------------------------------------
        # 飢餓機制
        # -------------------------------------------------

        player = game["player"]

        if player["fullness"] < 15:

            player["hp"] = max(
                0,
                player["hp"] - 5
            )

            player["status"] = (
                "極度飢餓，持續損耗生命"
            )

            story += (
                "\n\n【生存危機】\n"
                "你的腹中空空如也，"
                "飢餓感開始侵蝕體力。"
                "本次行動額外損失五點生命。"
            )

        normalise_player(
            player
        )

        # -------------------------------------------------
        # 故事摘要
        # -------------------------------------------------

        summary = str(
            data.get(
                "story_summary_update",
                game.get(
                    "story_summary",
                    ""
                )
            )
        ).strip()

        if summary:

            game["story_summary"] = (
                summary[:800]
            )

        # -------------------------------------------------
        # 記錄玩家行動
        # -------------------------------------------------

        game["story_history"].append(
            "【第 "
            + str(game["turn"])
            + " 回合】\n"
            + "你選擇："
            + action
        )

        # -------------------------------------------------
        # 記錄劇情
        # -------------------------------------------------

        game["story_history"].append(
            story
        )

        game["last_action"] = action

        game["last_story"] = story

        # -------------------------------------------------
        # 保留最近 40 段
        # -------------------------------------------------

        if len(
            game["story_history"]
        ) > 40:

            game["story_history"] = (
                game["story_history"][-40:]
            )

        # -------------------------------------------------
        # 選項
        # -------------------------------------------------

        game["current_options"] = (
            make_valid_options(
                data.get(
                    "options",
                    []
                )
            )
        )

        game["scroll_to_bottom"] = True

    except Exception as error:

        # 如果 API 失敗，回合數回退
        game["turn"] = max(
            0,
            game["turn"] - 1
        )

        # 將錯誤交給頁面顯示
        st.session_state.last_error = (
            str(error)
        )

    finally:

        game["processing"] = False


# =========================================================
# 20. 存檔
# =========================================================

def create_save():

    game = st.session_state.game_state

    save_data = {
        "version": "V3.4",
        "game_state": game,
        "current_options": (
            game.get(
                "current_options",
                []
            )
        ),
    }

    return json.dumps(
        save_data,
        ensure_ascii=False,
        separators=(
            ",",
            ":"
        ),
    )


# =========================================================
# 21. 讀檔
# =========================================================

def load_save(
    save_string
):

    data = json.loads(
        save_string
    )

    game_state = data.get(
        "game_state"
    )

    if not isinstance(
        game_state,
        dict
    ):

        raise ValueError(
            "找不到有效遊戲資料。"
        )

    # -----------------------------------------------------
    # 補上舊版本資料
    # -----------------------------------------------------

    game_state.setdefault(
        "version",
        "V3.4"
    )

    game_state.setdefault(
        "turn",
        0
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

    game_state.setdefault(
        "processing",
        False
    )

    game_state.setdefault(
        "scroll_to_bottom",
        True
    )

    player = game_state.setdefault(
        "player",
        {}
    )

    # -----------------------------------------------------
    # 補玩家舊資料
    # -----------------------------------------------------

    player.setdefault(
        "name",
        "詩柔"
    )

    player.setdefault(
        "identity",
        "未知"
    )

    player.setdefault(
        "secret_bloodline",
        random.choice(
            BLOODLINES
        )
    )

    player.setdefault(
        "bloodline_awakened",
        False
    )

    player.setdefault(
        "max_hp",
        100
    )

    player.setdefault(
        "max_mp",
        30
    )

    player.setdefault(
        "hp",
        100
    )

    player.setdefault(
        "mp",
        30
    )

    player.setdefault(
        "fullness",
        90
    )

    player.setdefault(
        "money",
        5
    )

    player.setdefault(
        "realm",
        "凡俗之軀"
    )

    player.setdefault(
        "location",
        "未知"
    )

    player.setdefault(
        "status",
        "健康"
    )

    player.setdefault(
        "comprehension",
        10
    )

    player.setdefault(
        "fortune",
        10
    )

    player.setdefault(
        "charm",
        10
    )

    player.setdefault(
        "righteousness",
        0
    )

    player.setdefault(
        "evil_aura",
        0
    )

    player.setdefault(
        "fame",
        0
    )

    normalise_player(
        player
    )

    player["status"] = get_status_text(
        player
    )

    # -----------------------------------------------------
    # 確保背包格式正常
    # -----------------------------------------------------

    if not isinstance(
        game_state["inventory"],
        list
    ):

        game_state["inventory"] = []

    if not isinstance(
        game_state["npcs"],
        dict
    ):

        game_state["npcs"] = {}

    st.session_state.game_state = (
        game_state
    )

    st.session_state.game_started = True

    st.session_state.last_error = ""

    game_state["scroll_to_bottom"] = True


# =========================================================
# 22. 自動捲到底
# =========================================================

def scroll_to_bottom():

    st.markdown(
        """
        <div id="story-bottom"></div>

        <script>
        setTimeout(function() {

            try {

                const parentDocument =
                    window.parent.document;

                const bottom =
                    parentDocument.getElementById(
                        "story-bottom"
                    );

                if (bottom) {

                    bottom.scrollIntoView({
                        behavior: "instant",
                        block: "end"
                    });

                } else {

                    window.parent.scrollTo(
                        0,
                        parentDocument.body.scrollHeight
                    );
                }

            } catch (error) {

                window.scrollTo(
                    0,
                    document.body.scrollHeight
                );
            }

        }, 250);
        </script>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# 23. 初始化 Session
# =========================================================

if "game_started" not in st.session_state:

    st.session_state.game_started = False


if "game_state" not in st.session_state:

    st.session_state.game_state = None


if "last_error" not in st.session_state:

    st.session_state.last_error = ""


# =========================================================
# 24. 頁面標題
# =========================================================

st.title(
    "🌸 三界奇譚：小薯逆襲記"
)

st.caption(
    "V3.4 · Nemotron Free 穩定版"
)


# =========================================================
# 25. 未開始遊戲
# =========================================================

if not st.session_state.game_started:

    st.subheader(
        "🎲 踏入命途"
    )

    st.write(
        "你將從五文錢開始，"
        "在三界之中一步一步尋找自己的道路。"
    )

    with st.form(
        "start_game_form"
    ):

        player_name = st.text_input(
            "請輸入你的名字",
            value="詩柔"
        )

        start_button = (
            st.form_submit_button(
                "🌸 開始新人生",
                use_container_width=True
            )
        )

        if start_button:

            init_game(
                player_name
            )

            st.rerun()

    st.markdown("---")

    st.subheader(
        "💾 讀取舊存檔"
    )

    load_code = st.text_area(
        "貼上之前保存的存檔代碼",
        height=180
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
# 26. 取得遊戲狀態
# =========================================================

game = st.session_state.game_state

player = game["player"]


# =========================================================
# 27. 顯示 API 錯誤
# =========================================================

if st.session_state.last_error:

    st.error(
        "⚠️ 本次行動未完成\n\n"
        + st.session_state.last_error
    )

    if st.button(
        "✖ 關閉錯誤訊息"
    ):

        st.session_state.last_error = ""

        st.rerun()


# =========================================================
# 28. Sidebar
# =========================================================

with st.sidebar:

    st.header(
        "📌 逆襲狀態"
    )

    st.write(
        "👤 "
        + str(
            player["name"]
        )
    )

    st.write(
        "🏷️ "
        + str(
            player["realm"]
        )
    )

    st.write(
        "📍 "
        + str(
            player["location"]
        )
    )

    st.write(
        "📖 第 "
        + str(
            game["turn"]
        )
        + " 回合"
    )

    st.markdown("---")

    col1, col2 = st.columns(2)

    col1.metric(
        "❤️ 生命",
        str(
            player["hp"]
        )
        + "/"
        + str(
            player["max_hp"]
        )
    )

    col2.metric(
        "💙 靈力",
        str(
            player["mp"]
        )
        + "/"
        + str(
            player["max_mp"]
        )
    )

    col3, col4 = st.columns(2)

    col3.metric(
        "🍚 飽腹",
        str(
            player["fullness"]
        )
        + "/100"
    )

    col4.metric(
        "💰 金錢",
        str(
            player["money"]
        )
        + " 文"
    )

    st.markdown("---")

    with st.expander(
        "📊 詳細屬性",
        expanded=True
    ):

        st.write(
            "🧠 悟性："
            + str(
                player["comprehension"]
            )
        )

        st.write(
            "🎲 福緣："
            + str(
                player["fortune"]
            )
        )

        st.write(
            "✨ 魅力："
            + str(
                player["charm"]
            )
        )

        st.write(
            "⚖️ 正氣："
            + str(
                player["righteousness"]
            )
        )

        st.write(
            "🩸 煞氣："
            + str(
                player["evil_aura"]
            )
        )

        st.write(
            "👑 威名："
            + str(
                player["fame"]
            )
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
        key="game_page",
    )

    st.markdown("---")

    if st.button(
        "🔄 重開新局",
        use_container_width=True
    ):

        st.session_state.game_started = False

        st.session_state.game_state = None

        st.session_state.last_error = ""

        st.rerun()


# =========================================================
# 29. 主線劇情
# =========================================================

if page == "📖 主線劇情":

    st.subheader(
        "📖 主線劇情"
    )

    # -----------------------------------------------------
    # 顯示故事
    # -----------------------------------------------------

    for index, text in enumerate(
        game["story_history"]
    ):

        if str(text).startswith(
            "【第 "
        ):

            st.info(
                text
            )

        else:

            st.write(
                text
            )

    # -----------------------------------------------------
    # 故事最底部錨點
    # -----------------------------------------------------

    scroll_required = game.get(
        "scroll_to_bottom",
        False
    )

    st.markdown(
        '<div id="story-bottom"></div>',
        unsafe_allow_html=True
    )

    if scroll_required:

        scroll_to_bottom()

        game["scroll_to_bottom"] = False

    st.markdown("---")

    st.write(
        "✨ **你打算怎麼做？**"
    )

    options = game.get(
        "current_options",
        []
    )

    if not options:

        options = [
            "仔細觀察四周。",
            "檢查身上物品。",
            "與附近人物交談。",
            "尋找安全地方。",
            "查看狀態",
        ]

        game["current_options"] = options

    # -----------------------------------------------------
    # 選項按鈕
    # -----------------------------------------------------

    for idx, option in enumerate(
        options
    ):

        button_key = (
            "turn_"
            + str(
                game["turn"]
            )
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

            process_turn(
                option
            )

            st.rerun()

    st.markdown("---")

    st.write(
        "💬 **自由行動**"
    )

    custom_action = st.text_input(
        "你可以輸入任何想做的事情",
        key="custom_action_input"
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

            process_turn(
                custom_action.strip()
            )

            st.rerun()


# =========================================================
# 30. 背包
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
                    "### "
                    + str(name)
                    + " × "
                    + str(count)
                )

                st.write(
                    str(desc)
                )


# =========================================================
# 31. NPC
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
# 32. 存檔／讀檔
# =========================================================

elif page == "💾 存檔／讀檔":

    st.subheader(
        "💾 存檔／讀檔"
    )

    st.write(
        "你可以把下面整段文字複製保存。"
    )

    save_string = create_save()

    st.text_area(
        "📋 當前存檔",
        value=save_string,
        height=300,
    )

    st.markdown("---")

    st.write(
        "📥 載入之前的存檔"
    )

    load_string = st.text_area(
        "貼上存檔",
        height=220,
        key="load_save_area",
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

                time.sleep(
                    0.5
                )

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
# 33. Footer
# =========================================================

st.markdown("---")

st.caption(
    "三界奇譚 V3.4 · Nemotron Free · 修仙文字 RPG"
)
