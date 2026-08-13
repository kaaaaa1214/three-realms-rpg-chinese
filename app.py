import streamlit as st
import requests
import json
import random
import re


# =========================================================
# 0. Streamlit Page Config
# =========================================================

st.set_page_config(
    page_title="三界奇譚：小薯逆襲記",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================================================
# 1. OpenRouter 設定
# =========================================================

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MODEL_NAME = "nvidia/nemotron-3-ultra-550b-a55b:free"

OPENROUTER_API_KEY = str(
    st.secrets.get(
        "OPENROUTER_API_KEY",
        ""
    )
).strip()

if not OPENROUTER_API_KEY:
    st.error(
        "⚠️ 找不到 OPENROUTER_API_KEY。\n\n"
        "請到 Streamlit Cloud → Settings → Secrets 設定：\n\n"
        'OPENROUTER_API_KEY = "你的 API Key"'
    )
    st.stop()


# =========================================================
# 2. API 時間設定
# =========================================================
#
# 原本 timeout = 120
#
# Free Model 如果排隊，會令你以為個 App 死咗。
#
# 而家：
# Connect 最多 10 秒
# Read 最多 45 秒
#
# 如果 45 秒模型都未回覆，就直接報錯。
# =========================================================

API_CONNECT_TIMEOUT = 10
API_READ_TIMEOUT = 45


# =========================================================
# 3. 遊戲世界資料
# =========================================================

LOCATIONS = [
    {
        "loc": "凡間·青石鎮",
        "identity": "街頭討生活的落魄孤兒",
        "bg": "你無父無母，只能靠替人跑腿、搬貨與偶爾乞討維生。"
    },
    {
        "loc": "仙界·凌霄外園",
        "identity": "九霄雲宮最底層雜役",
        "bg": "你每日清掃落花、挑水與處理雜務，在仙界眾生眼中幾乎毫無地位。"
    },
    {
        "loc": "妖界·萬妖山脈",
        "identity": "被遺棄在山脈外圍的半妖",
        "bg": "你的血統混雜，因此受到妖族排斥，只能在危險山林邊緣求生。"
    },
    {
        "loc": "魔界·黑焰礦區",
        "identity": "最低階的魔鐵礦奴",
        "bg": "你每日挖掘魔鐵，承受魔氣侵蝕與監工驅使，只求活過今天。"
    },
    {
        "loc": "靈界·散修坊市",
        "identity": "擺地攤維生的落魄散修",
        "bg": "你的靈根普通，功法殘缺，平日靠替人尋物與販賣雜物勉強維生。"
    }
]


BLOODLINES = [
    "鳳凰涅槃血脈",
    "鴻蒙神魔同體印",
    "太古星辰帝君遺脈",
    "九幽妖皇真靈",
    "混沌天脈",
    "太初劍骨"
]


STARTING_ITEMS = [
    {
        "name": "粗布麻衣",
        "count": 1,
        "desc": "洗得發白的粗布衣物，勉強可以遮身。"
    },
    {
        "name": "乾糧",
        "count": 2,
        "desc": "粗糙乾糧，可以暫時填飽肚子。"
    },
    {
        "name": "清水",
        "count": 1,
        "desc": "一小壺普通清水。"
    }
]


DEFAULT_OPTIONS = [
    "仔細觀察附近環境，尋找新的線索。",
    "主動與附近的人交談，試探對方的目的。",
    "暫時避開人群，找一個安全地方思考下一步。",
    "冒險靠近剛才發現的異常之處。"
]


# =========================================================
# 4. System Prompt
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

每次行動必須推進新的劇情。

不要重複上一段。

不要把玩家上一個選項原封不動再寫一次。

不要一直停留在觀察四周。

事件必須真正發生。

六、回合

每次只推進一個回合。

不要自行增加回合數。

回合數由遊戲程式處理。

七、選項

每次提供四個新的行動選項。

選項必須有不同策略，例如：

探索、交涉、冒險、戰鬥、利益交換、逃避、觀察等。

八、禁止

不要輸出 Markdown。

不要輸出程式碼。

不要輸出 JSON 以外的任何內容。

不要輸出程式碼區塊。

不要輸出英文。

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
# 5. Session State 初始化
# =========================================================

if "game_started" not in st.session_state:
    st.session_state.game_started = False

if "game_state" not in st.session_state:
    st.session_state.game_state = None

if "game_page" not in st.session_state:
    st.session_state.game_page = "📖 主線劇情"

if "page_selector" not in st.session_state:
    st.session_state.page_selector = "📖 主線劇情"

if "pending_game_page" not in st.session_state:
    st.session_state.pending_game_page = None

if "scroll_to_bottom" not in st.session_state:
    st.session_state.scroll_to_bottom = False


# =========================================================
# 6. Page Constants
# =========================================================

PAGES = [
    "📖 主線劇情",
    "🎒 背包",
    "👥 人物關係",
    "💾 存檔／讀檔"
]


# =========================================================
# 7. 建立初始背包
# =========================================================

def create_starting_inventory():

    return [
        {
            "name": item["name"],
            "count": item["count"],
            "desc": item["desc"]
        }
        for item in STARTING_ITEMS
    ]


# =========================================================
# 8. 初始化遊戲
# =========================================================

def init_game(player_name):

    location = random.choice(
        LOCATIONS
    )

    player_name = str(
        player_name
    ).strip()

    if not player_name:
        player_name = "詩柔"

    comprehension = random.randint(
        8,
        12
    )

    fortune = random.randint(
        8,
        12
    )

    charm = random.randint(
        8,
        12
    )

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

            "comprehension": comprehension,

            "fortune": fortune,

            "charm": charm,

            "righteousness": 0,

            "evil_aura": 0,

            "fame": 0
        },

        "inventory": create_starting_inventory(),

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

        "last_story": ""
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
        "查看狀態"
    ]

    st.session_state.game_state = state
    st.session_state.game_started = True

    st.session_state.game_page = "📖 主線劇情"
    st.session_state.page_selector = "📖 主線劇情"
    st.session_state.pending_game_page = None

    st.session_state.scroll_to_bottom = True


# =========================================================
# 9. 數值處理
# =========================================================

def clamp(
    value,
    minimum,
    maximum
):

    try:
        value = int(value)
    except Exception:
        value = minimum

    return max(
        minimum,
        min(
            maximum,
            value
        )
    )


def normalise_player(player):

    player["max_hp"] = max(
        1,
        int(
            player.get(
                "max_hp",
                100
            )
        )
    )

    player["max_mp"] = max(
        0,
        int(
            player.get(
                "max_mp",
                30
            )
        )
    )

    player["hp"] = clamp(
        player.get(
            "hp",
            100
        ),
        0,
        player["max_hp"]
    )

    player["mp"] = clamp(
        player.get(
            "mp",
            30
        ),
        0,
        player["max_mp"]
    )

    player["fullness"] = clamp(
        player.get(
            "fullness",
            90
        ),
        0,
        100
    )

    try:

        player["money"] = max(
            0,
            int(
                player.get(
                    "money",
                    0
                )
            )
        )

    except Exception:

        player["money"] = 0


# =========================================================
# 10. 狀態文字
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
# 11. 清理模型輸出
# =========================================================

def clean_model_text(text):

    if not text:
        return ""

    text = str(
        text
    ).strip()

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

    first_brace = text.find(
        "{"
    )

    if first_brace > 0:

        text = text[
            first_brace:
        ]

    last_brace = text.rfind(
        "}"
    )

    if last_brace >= 0:

        text = text[
            :last_brace + 1
        ]

    return text.strip()


# =========================================================
# 12. JSON Parser
# =========================================================

def parse_json_response(text):

    cleaned = clean_model_text(
        text
    )

    if not cleaned:
        return None

    try:

        data = json.loads(
            cleaned
        )

        if isinstance(
            data,
            dict
        ):
            return data

    except Exception:
        pass

    start = cleaned.find(
        "{"
    )

    end = cleaned.rfind(
        "}"
    )

    if start >= 0 and end > start:

        candidate = cleaned[
            start:end + 1
        ]

        try:

            data = json.loads(
                candidate
            )

            if isinstance(
                data,
                dict
            ):
                return data

        except Exception:
            pass

    return None


# =========================================================
# 13. OpenRouter API
# =========================================================

def call_nemotron(
    messages,
    timeout_seconds=API_READ_TIMEOUT
):

    api_key = str(
        st.secrets.get(
            "OPENROUTER_API_KEY",
            ""
        )
    ).strip()

    if not api_key:

        raise RuntimeError(
            "找不到 OPENROUTER_API_KEY。"
        )

    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "HTTP-Referer": "https://streamlit.io",
        "X-Title": "Three Realms RPG"
    }

    payload = {
        "model": MODEL_NAME,

        "messages": messages,

        "temperature": 0.8,

        "max_tokens": 2200
    }

    try:

        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=(
                API_CONNECT_TIMEOUT,
                timeout_seconds
            )
        )

    except requests.exceptions.Timeout:

        raise RuntimeError(
            "模型等待超時。\n\n"
            "目前免費模型可能正在排隊，"
            "請稍後再試。"
        )

    except requests.exceptions.ConnectionError:

        raise RuntimeError(
            "無法連接 OpenRouter。\n\n"
            "請檢查網絡連線或稍後再試。"
        )

    except requests.exceptions.RequestException as error:

        raise RuntimeError(
            "OpenRouter 連線失敗："
            + str(error)
        )

    except UnicodeEncodeError:

        raise RuntimeError(
            "API 請求編碼失敗。"
        )

    if response.status_code != 200:

        try:

            error_data = response.json()

            error_message = json.dumps(
                error_data,
                ensure_ascii=False
            )

        except Exception:

            error_message = response.text[
                :1500
            ]

        raise RuntimeError(
            "OpenRouter API 錯誤 "
            + str(
                response.status_code
            )
            + "：\n\n"
            + error_message
        )

    try:

        result = response.json()

    except Exception:

        raise RuntimeError(
            "OpenRouter 返回的內容不是有效 JSON。"
        )

    if not isinstance(
        result,
        dict
    ):

        raise RuntimeError(
            "OpenRouter 返回格式異常。"
        )

    choices = result.get(
        "choices"
    )

    if not choices:

        error_info = result.get(
            "error",
            result
        )

        raise RuntimeError(
            "模型沒有返回有效結果：\n\n"
            + json.dumps(
                error_info,
                ensure_ascii=False
            )[:2000]
        )

    try:

        content = choices[0][
            "message"
        ][
            "content"
        ]

    except Exception:

        raise RuntimeError(
            "模型返回內容格式異常。"
        )

    if isinstance(
        content,
        list
    ):

        content_parts = []

        for part in content:

            if isinstance(
                part,
                dict
            ):

                text_part = part.get(
                    "text",
                    ""
                )

                if text_part:

                    content_parts.append(
                        str(
                            text_part
                        )
                    )

        content = "".join(
            content_parts
        )

    if not content:

        raise RuntimeError(
            "Nemotron 返回空白內容。"
        )

    return str(
        content
    )


# =========================================================
# 14. 建立遊戲 Prompt
# =========================================================

def build_game_prompt(
    action
):

    game = st.session_state.game_state

    player = game["player"]

    recent_history = game.get(
        "story_history",
        []
    )[-6:]

    recent_text = "\n\n".join(
        recent_history
    )

    npc_text = json.dumps(
        game.get(
            "npcs",
            {}
        ),
        ensure_ascii=False
    )

    inventory_text = json.dumps(
        game.get(
            "inventory",
            []
        ),
        ensure_ascii=False
    )

    player_text = json.dumps(
        player,
        ensure_ascii=False
    )

    prompt = f"""
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

如果玩家只是觀察，就必須得到新的資訊。

如果玩家交涉，就讓人物真正回應。

如果玩家探索，就讓探索得到結果。

如果玩家冒險，就必須承擔合理風險。

如果玩家戰鬥，就必須產生實際戰鬥結果。

如果玩家逃跑，就必須處理逃跑結果。

每次必須提供四個新的選項。

請只輸出指定 JSON。
"""

    return prompt


# =========================================================
# 15. 套用玩家數值
# =========================================================

def apply_player_changes(
    data
):

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

    if (
        realm
        and str(realm)
        != "維持不變"
    ):

        player["realm"] = str(
            realm
        )

    location = update.get(
        "location"
    )

    if (
        location
        and str(location)
        != "維持不變"
    ):

        player["location"] = str(
            location
        )

    normalise_player(
        player
    )

    player["status"] = get_status_text(
        player
    )


# =========================================================
# 16. 背包變化
# =========================================================

def apply_inventory_changes(
    data
):

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

    inventory = game["inventory"]

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

                found["count"] += amount

            except Exception:

                found["count"] = amount

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
                    )
                }
            )


# =========================================================
# 17. NPC 更新
# =========================================================

def apply_npc_updates(
    data
):

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

        old = game[
            "npcs"
        ].get(
            name,
            {}
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

            "affinity": npc.get(
                "affinity",
                old.get(
                    "affinity",
                    0
                )
            ),

            "key_memory": npc.get(
                "key_memory",
                old.get(
                    "key_memory",
                    ""
                )
            )
        }

        game[
            "npcs"
        ][name] = merged


# =========================================================
# 18. 防止重複劇情
# =========================================================

def is_duplicate_story(
    new_story
):

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
        new_story
    )

    clean_b = re.sub(
        r"\s+",
        "",
        last_story
    )

    if clean_a == clean_b:
        return True

    return False


# =========================================================
# 19. 生成模型 JSON
# =========================================================

def generate_turn_data(
    action
):

    prompt = build_game_prompt(
        action
    )

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": prompt
        }
    ]

    raw = call_nemotron(
        messages,
        API_READ_TIMEOUT
    )

    data = parse_json_response(
        raw
    )

    if data is not None:
        return data

    # =====================================================
    # 只做一次 JSON 修復
    # =====================================================

    repair_prompt = """
你上一個回答不是合法 JSON。

現在只需要重新輸出合法 JSON。

不要解釋。

不要輸出 Markdown。

不要輸出程式碼區塊。

不要輸出英文。

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

    repair_messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": prompt
        },
        {
            "role": "assistant",
            "content": raw[:6000]
        },
        {
            "role": "user",
            "content": repair_prompt
        }
    ]

    repaired_raw = call_nemotron(
        repair_messages,
        30
    )

    repaired_data = parse_json_response(
        repaired_raw
    )

    if repaired_data is None:

        raise RuntimeError(
            "模型回覆不是有效 JSON。\n\n"
            "請再試一次。"
        )

    return repaired_data


# =========================================================
# 20. 處理玩家回合
# =========================================================

def process_turn(
    action
):

    game = st.session_state.game_state

    if not game:
        return False

    if game.get(
        "processing",
        False
    ):
        return False

    action = str(
        action
    ).strip()

    if not action:
        return False

    # =====================================================
    # 查看狀態
    #
    # 唔需要 API
    # =====================================================

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

        game[
            "story_history"
        ].append(
            status_story
        )

        game[
            "last_action"
        ] = action

        st.session_state.scroll_to_bottom = True

        return True

    # =====================================================
    # Lock
    # =====================================================

    game["processing"] = True

    try:

        game["turn"] += 1

        # =================================================
        # 模型生成
        # =================================================

        with st.spinner(
            "🔮 命運正在推演……"
        ):

            data = generate_turn_data(
                action
            )

        # =================================================
        # Story
        # =================================================

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
                "你沒有貿然行動，而是重新思考下一步。"
            )

        # =================================================
        # 如果完全重複，只提示一次
        #
        # 不再額外呼叫 API。
        #
        # 避免之前等足幾分鐘。
        # =================================================

        if is_duplicate_story(
            story
        ):

            story = (
                "你剛才的行動沒有帶來明顯的新變化。\n\n"
                "然而你注意到，附近的氣氛似乎正在悄悄改變。"
                "你決定暫時保持警惕。"
            )

        # =================================================
        # 套用數值
        # =================================================

        apply_player_changes(
            data
        )

        apply_inventory_changes(
            data
        )

        apply_npc_updates(
            data
        )

        # =================================================
        # 飢餓機制
        # =================================================

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

        # =================================================
        # Summary
        # =================================================

        summary = str(
            data.get(
                "story_summary_update",
                ""
            )
        ).strip()

        if summary:

            game[
                "story_summary"
            ] = summary[:500]

        # =================================================
        # 記錄玩家行動
        # =================================================

        game[
            "story_history"
        ].append(
            "【第 "
            + str(
                game["turn"]
            )
            + " 回合】\n"
            + "你選擇："
            + action
        )

        # =================================================
        # 記錄故事
        # =================================================

        game[
            "story_history"
        ].append(
            story
        )

        game[
            "last_action"
        ] = action

        game[
            "last_story"
        ] = story

        # =================================================
        # 控制歷史長度
        # =================================================

        if len(
            game["story_history"]
        ) > 30:

            game[
                "story_history"
            ] = game[
                "story_history"
            ][-30:]

        # =================================================
        # Options
        # =================================================

        model_options = data.get(
            "options",
            []
        )

        valid_options = []

        if isinstance(
            model_options,
            list
        ):

            for option in model_options:

                option = str(
                    option
                ).strip()

                if (
                    option
                    and option not in valid_options
                ):

                    valid_options.append(
                        option
                    )

        while len(
            valid_options
        ) < 4:

            for default_option in DEFAULT_OPTIONS:

                if default_option not in valid_options:

                    valid_options.append(
                        default_option
                    )

                    break

        valid_options = valid_options[:4]

        valid_options.append(
            "查看狀態"
        )

        game[
            "current_options"
        ] = valid_options

        st.session_state.scroll_to_bottom = True

        return True

    except Exception as error:

        # =================================================
        # API 失敗
        #
        # 回合回退
        # =================================================

        game["turn"] = max(
            0,
            game["turn"] - 1
        )

        st.error(
            "⚠️ 本次行動未完成\n\n"
            + str(error)
        )

        return False

    finally:

        game["processing"] = False


# =========================================================
# 21. 建立存檔
# =========================================================

def create_save():

    game = st.session_state.game_state

    save_data = {
        "version": "V3.5",

        "game_state": game,

        "game_page": st.session_state.get(
            "game_page",
            "📖 主線劇情"
        )
    }

    return json.dumps(
        save_data,
        ensure_ascii=False
    )


# =========================================================
# 22. 讀檔
# =========================================================

def load_save(
    save_string
):

    data = json.loads(
        save_string
    )

    if not isinstance(
        data,
        dict
    ):

        raise ValueError(
            "存檔格式無效。"
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

    # =====================================================
    # 補舊版本資料
    # =====================================================

    game_state.setdefault(
        "version",
        "V3.5"
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

    # =====================================================
    # Player
    # =====================================================

    player = game_state.setdefault(
        "player",
        {}
    )

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

    # =====================================================
    # 資料格式修正
    # =====================================================

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

    if not isinstance(
        game_state["current_options"],
        list
    ):

        game_state["current_options"] = []

    if not isinstance(
        game_state["story_history"],
        list
    ):

        game_state["story_history"] = []

    # =====================================================
    # processing 永遠重設
    # =====================================================

    game_state["processing"] = False

    # =====================================================
    # 真正載入
    # =====================================================

    st.session_state.game_state = game_state

    st.session_state.game_started = True

    # =====================================================
    # 不直接改 radio widget
    #
    # 只寫入 pending。
    #
    # 下一次 rerun 開始之前才會真正設定。
    # =====================================================

    saved_page = data.get(
        "game_page",
        "📖 主線劇情"
    )

    if saved_page not in PAGES:

        saved_page = "📖 主線劇情"

    st.session_state.pending_game_page = (
        saved_page
    )

    st.session_state.scroll_to_bottom = True


# =========================================================
# 23. Pending Page
#
# 這段一定在 radio 建立之前。
# =========================================================

if (
    st.session_state.get(
        "pending_game_page"
    )
    is not None
):

    pending_page = (
        st.session_state.pending_game_page
    )

    st.session_state.pending_game_page = None

    if pending_page in PAGES:

        st.session_state.game_page = (
            pending_page
        )

        st.session_state.page_selector = (
            pending_page
        )


# =========================================================
# 24. 標題
# =========================================================

st.title(
    "🌸 三界奇譚：小薯逆襲記"
)

st.caption(
    "V3.5 · Nemotron Free 穩定版"
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

        start_button = st.form_submit_button(
            "🌸 開始新人生",
            use_container_width=True
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
        height=180,
        key="initial_load_code"
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

        else:

            st.warning(
                "請先貼上存檔內容。"
            )

    st.stop()


# =========================================================
# 26. 取得遊戲
# =========================================================

game = st.session_state.game_state

player = game["player"]


# =========================================================
# 27. Sidebar
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

    # =====================================================
    # ★ 最重要修正
    #
    # radio 使用 page_selector
    #
    # 唔再使用 game_page 作為 widget key。
    #
    # game_page 只用來儲存遊戲頁面狀態。
    # =====================================================

    current_page = st.session_state.get(
        "game_page",
        "📖 主線劇情"
    )

    if current_page not in PAGES:

        current_page = "📖 主線劇情"

        st.session_state.game_page = (
            current_page
        )

    current_index = PAGES.index(
        current_page
    )

    page = st.radio(
        "🗂️ 遊戲功能",
        PAGES,
        index=current_index,
        key="page_selector"
    )

    # =====================================================
    # 如果使用者手動切頁
    # =====================================================

    if page != st.session_state.game_page:

        st.session_state.game_page = page


    st.markdown("---")

    if st.button(
        "🔄 重開新局",
        use_container_width=True
    ):

        st.session_state.game_started = False

        st.session_state.game_state = None

        st.session_state.game_page = (
            "📖 主線劇情"
        )

        st.session_state.page_selector = (
            "📖 主線劇情"
        )

        st.session_state.pending_game_page = None

        st.session_state.scroll_to_bottom = False

        st.rerun()


# =========================================================
# 28. 主線劇情
# =========================================================

if page == "📖 主線劇情":

    st.subheader(
        "📖 主線劇情"
    )

    story_container = st.container()

    with story_container:

        for text in game[
            "story_history"
        ]:

            if text.startswith(
                "【第 "
            ):

                st.info(
                    text
                )

            else:

                st.write(
                    text
                )

        st.markdown(
            '<div id="story-bottom"></div>',
            unsafe_allow_html=True
        )

    # =====================================================
    # Auto Scroll
    # =====================================================

    if st.session_state.get(
        "scroll_to_bottom",
        False
    ):

        st.session_state.scroll_to_bottom = False

        st.markdown(
            """
            <script>
            setTimeout(function() {

                const element =
                    document.getElementById(
                        "story-bottom"
                    );

                if (element) {

                    element.scrollIntoView({
                        behavior: "smooth",
                        block: "end"
                    });

                }

                window.scrollTo(
                    0,
                    document.body.scrollHeight
                );

            }, 150);
            </script>
            """,
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

        options = [
            "仔細觀察四周。",
            "檢查身上物品。",
            "與附近人物交談。",
            "尋找安全地方。",
            "查看狀態"
        ]

        game[
            "current_options"
        ] = options

    # =====================================================
    # 玩家選項
    # =====================================================

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
            )
        ):

            success = process_turn(
                option
            )

            if success:

                st.rerun()

    # =====================================================
    # 自由行動
    # =====================================================

    st.markdown("---")

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
        )
    ):

        if custom_action.strip():

            action = custom_action.strip()

            success = process_turn(
                action
            )

            if success:

                st.session_state.custom_action_input = ""

                st.rerun()

        else:

            st.warning(
                "請先輸入你想做的事情。"
            )


# =========================================================
# 29. 背包
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

    st.markdown("---")

    if st.button(
        "📖 返回主線劇情",
        use_container_width=True
    ):

        st.session_state.pending_game_page = (
            "📖 主線劇情"
        )

        st.session_state.scroll_to_bottom = True

        st.rerun()


# =========================================================
# 30. NPC
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
                + str(
                    affinity
                )
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

    st.markdown("---")

    if st.button(
        "📖 返回主線劇情",
        use_container_width=True
    ):

        st.session_state.pending_game_page = (
            "📖 主線劇情"
        )

        st.session_state.scroll_to_bottom = True

        st.rerun()


# =========================================================
# 31. 存檔／讀檔
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
        key="current_save_display"
    )

    st.markdown("---")

    st.write(
        "📥 載入之前的存檔"
    )

    load_string = st.text_area(
        "貼上存檔",
        height=220,
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

    st.markdown("---")

    if st.button(
        "📖 返回主線劇情",
        use_container_width=True
    ):

        st.session_state.pending_game_page = (
            "📖 主線劇情"
        )

        st.session_state.scroll_to_bottom = True

        st.rerun()


# =========================================================
# 32. Footer
# =========================================================

st.markdown("---")

st.caption(
    "三界奇譚 V3.5 · Nemotron Free · 修仙文字 RPG"
)