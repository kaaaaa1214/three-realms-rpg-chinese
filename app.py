import streamlit as st
import requests
import json
import random
import re
import time
import base64
from difflib import SequenceMatcher


# =========================================================
# 1. Streamlit 設定
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


def get_api_key():

    key = st.secrets.get(
        "OPENROUTER_API_KEY",
        ""
    )

    if key is None:
        return ""

    key = str(key)

    key = key.strip()
    key = key.replace("\r", "")
    key = key.replace("\n", "")
    key = key.replace("\ufeff", "")

    key = key.strip("\"'")
    key = key.strip("「」")
    key = key.strip("“”")

    if key.startswith(
        "OPENROUTER_API_KEY="
    ):
        key = key.split(
            "=",
            1
        )[1].strip()

    return key


OPENROUTER_API_KEY = get_api_key()


if not OPENROUTER_API_KEY:

    st.error(
        "⚠️ 找不到 OPENROUTER_API_KEY。\n\n"
        "請到 Streamlit Cloud → Settings → Secrets 設定：\n\n"
        'OPENROUTER_API_KEY = "你的 API Key"'
    )

    st.stop()


# =========================================================
# 3. 遊戲世界
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
# 4. 初始化
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

    state = {

        "version": "V3.5",

        "turn": 0,

        "processing": False,

        "last_error": "",

        "last_error_time": "",

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

            "comprehension": random.randint(
                8,
                12
            ),

            "fortune": random.randint(
                8,
                12
            ),

            "charm": random.randint(
                8,
                12
            ),

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


def get_status_text(player):

    hp = player.get(
        "hp",
        100
    )

    fullness = player.get(
        "fullness",
        90
    )

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
                player.get(
                    key,
                    0
                )
            )
        except Exception:
            player[key] = 0

    player["status"] = get_status_text(
        player
    )


# =========================================================
# 6. System Prompt
# =========================================================

SYSTEM_PROMPT = """
你是《三界奇譚》的專業修仙 RPG 遊戲主持人。

你負責根據玩家的行動推進劇情。

【語言】

全程使用繁體中文。

劇情、人物對話、選項全部使用繁體中文。

不要輸出英文。

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

【選項】

每次提供四個新的行動選項。

第五個由程式固定加入查看狀態。

四個選項應具有不同策略。

【數值】

只可以提出變化。

不要重新建立完整玩家狀態。

不要修改玩家姓名。

不要修改隱藏血脈。

不要自行增加不存在的屬性。

【JSON】

只可以輸出合法 JSON。

不要 Markdown。

不要三個反引號。

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
# 7. API Key
# =========================================================

def clean_api_key_for_header(key):

    if key is None:
        return ""

    key = str(key)

    key = key.strip()
    key = key.replace(
        "\r",
        ""
    )
    key = key.replace(
        "\n",
        ""
    )
    key = key.replace(
        "\ufeff",
        ""
    )

    key = key.strip("\"'")
    key = key.strip("「」")
    key = key.strip("“”")

    if key.startswith(
        "OPENROUTER_API_KEY="
    ):
        key = key.split(
            "=",
            1
        )[1].strip()

    try:

        key.encode(
            "latin-1"
        )

    except UnicodeEncodeError:

        key = key.encode(
            "ascii",
            errors="ignore"
        ).decode(
            "ascii"
        )

    return key


# =========================================================
# 8. OpenRouter API
# =========================================================

def call_nemotron(
    messages,
    status_placeholder=None
):

    api_key = clean_api_key_for_header(
        OPENROUTER_API_KEY
    )

    if not api_key:

        raise RuntimeError(
            "OpenRouter API Key 是空白的。"
        )

    headers = {

        "Authorization":
            "Bearer " + api_key,

        "Content-Type":
            "application/json",

        "Accept":
            "application/json",

        "HTTP-Referer":
            "https://openrouter.ai",

        "X-Title":
            "Three Realms RPG",

    }

    payload = {

        "model":
            MODEL_NAME,

        "messages":
            messages,

        "temperature":
            0.8,

        "max_tokens":
            2500,

    }

    max_attempts = 3

    last_error = ""

    for attempt in range(
        1,
        max_attempts + 1
    ):

        try:

            if status_placeholder is not None:

                if attempt == 1:

                    status_placeholder.info(
                        "📡 正在連接 OpenRouter……"
                    )

                else:

                    status_placeholder.warning(
                        f"⏳ 第 {attempt} 次嘗試……"
                    )

            response = requests.post(

                OPENROUTER_URL,

                headers=headers,

                json=payload,

                timeout=120,

            )

        except UnicodeEncodeError as error:

            raise RuntimeError(
                "API Header 含有無法傳送的特殊字元。\n\n"
                "請檢查 Streamlit Secrets 中的 "
                "OPENROUTER_API_KEY。\n\n"
                f"詳細錯誤：{error}"
            )

        except requests.exceptions.Timeout:

            last_error = (
                "OpenRouter 回應逾時。"
            )

            if attempt < max_attempts:

                if status_placeholder:

                    status_placeholder.warning(
                        "⏳ AI 回應較慢，準備重新連接……"
                    )

                time.sleep(
                    3 * attempt
                )

                continue

            raise RuntimeError(
                last_error
                + "\n\n"
                "可能是免費模型目前繁忙。"
            )

        except requests.exceptions.RequestException as error:

            raise RuntimeError(
                "連接 OpenRouter 失敗：\n\n"
                + str(error)
            )

        status_code = response.status_code

        try:

            result = response.json()

        except Exception:

            result = {}

        if status_code == 200:

            if not isinstance(
                result,
                dict
            ):

                raise RuntimeError(
                    "OpenRouter 返回格式異常。"
                )

            if "error" in result:

                error_text = json.dumps(
                    result.get(
                        "error"
                    ),
                    ensure_ascii=False
                )

                raise RuntimeError(
                    "模型 API 發生錯誤：\n"
                    + error_text
                )

            choices = result.get(
                "choices"
            )

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

            if isinstance(
                content,
                list
            ):

                parts = []

                for part in content:

                    if isinstance(
                        part,
                        dict
                    ):

                        if "text" in part:

                            parts.append(
                                str(
                                    part["text"]
                                )
                            )

                content = "".join(
                    parts
                )

            if not content:

                raise RuntimeError(
                    "Nemotron 返回空白內容。"
                )

            if status_placeholder:

                status_placeholder.success(
                    "✅ AI 劇情生成完成"
                )

            return str(
                content
            )

        # -------------------------------------------------
        # 429
        # -------------------------------------------------

        if status_code == 429:

            try:

                error_data = result.get(
                    "error",
                    {}
                )

                error_message = str(
                    error_data.get(
                        "message",
                        ""
                    )
                )

            except Exception:

                error_message = ""

            last_error = (
                "OpenRouter 回覆 429。"
            )

            if error_message:

                last_error += (
                    "\n\n"
                    + error_message
                )

            if attempt < max_attempts:

                wait_seconds = (
                    4 * attempt
                )

                if status_placeholder:

                    status_placeholder.warning(
                        "⚠️ AI 暫時達到限制（429）"
                        f"，{wait_seconds} 秒後自動重試……"
                    )

                time.sleep(
                    wait_seconds
                )

                continue

            raise RuntimeError(
                last_error
                + "\n\n"
                "可能原因：\n"
                "• 免費模型目前 Rate Limit\n"
                "• 免費模型暫時繁忙\n"
                "• OpenRouter 免費額度已達限制\n"
                "• 同一時間請求過多\n\n"
                "請稍後再試。"
            )

        # -------------------------------------------------
        # 401
        # -------------------------------------------------

        if status_code == 401:

            raise RuntimeError(
                "OpenRouter API Key 無效或未授權。\n\n"
                "請檢查 Streamlit Secrets。"
            )

        # -------------------------------------------------
        # 403
        # -------------------------------------------------

        if status_code == 403:

            raise RuntimeError(
                "OpenRouter 拒絕這次請求（403）。\n\n"
                "可能是 API Key 權限或模型存取問題。"
            )

        # -------------------------------------------------
        # 其他錯誤
        # -------------------------------------------------

        try:

            error_text = json.dumps(
                result,
                ensure_ascii=False
            )

        except Exception:

            error_text = response.text

        raise RuntimeError(
            f"OpenRouter API 錯誤 {status_code}\n\n"
            + error_text[:2000]
        )

    raise RuntimeError(
        last_error or
        "OpenRouter 請求失敗。"
    )


# =========================================================
# 9. 模型輸出清理
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

    first = text.find(
        "{"
    )

    last = text.rfind(
        "}"
    )

    if first >= 0 and last > first:

        text = text[
            first:last + 1
        ]

    return text.strip()


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

    return None


# =========================================================
# 10. 建立 Prompt
# =========================================================

def build_game_prompt(action):

    game = st.session_state.game_state

    player = game["player"]

    recent_history = game.get(
        "story_history",
        []
    )[-8:]

    recent_text = "\n\n".join(
        str(x)
        for x in recent_history
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

你現在必須讓故事繼續向前發展。

不要重新描述相同事件。

如果玩家觀察：
必須得到新的資訊。

如果玩家交涉：
讓 NPC 回應。

如果玩家探索：
讓探索得到結果。

如果玩家冒險：
讓冒險產生合理風險。

如果玩家做出明顯危險行動：
可以讓玩家受傷、失去物品或金錢。

如果玩家成功：
也不應該每次都直接得到巨大機緣。

請按照系統指定 JSON 格式輸出。
"""


# =========================================================
# 11. 玩家更新
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

    def safe_int(
        value
    ):

        try:
            return int(
                value
            )
        except Exception:
            return 0

    player["hp"] += safe_int(
        update.get(
            "hp_change",
            0
        )
    )

    player["mp"] += safe_int(
        update.get(
            "mp_change",
            0
        )
    )

    player["fullness"] += safe_int(
        update.get(
            "fullness_change",
            0
        )
    )

    player["money"] += safe_int(
        update.get(
            "money_change",
            0
        )
    )

    realm = update.get(
        "realm"
    )

    if realm:

        realm = str(
            realm
        ).strip()

        if realm and realm != "維持不變":

            player["realm"] = realm

    location = update.get(
        "location"
    )

    if location:

        location = str(
            location
        ).strip()

        if location and location != "維持不變":

            player["location"] = location

    normalise_player(
        player
    )


# =========================================================
# 12. 背包
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

            found["count"] = (
                int(
                    found.get(
                        "count",
                        0
                    )
                )
                + amount
            )

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
# 13. NPC
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

        old = game["npcs"].get(
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

        game["npcs"][name] = {

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


# =========================================================
# 14. 重複劇情
# =========================================================

def is_duplicate_story(
    new_story
):

    game = st.session_state.game_state

    last_story = game.get(
        "last_story",
        ""
    )

    if not new_story:
        return True

    if not last_story:
        return False

    a = re.sub(
        r"\s+",
        "",
        str(new_story)
    )

    b = re.sub(
        r"\s+",
        "",
        str(last_story)
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
# 15. 預設選項
# =========================================================

DEFAULT_OPTIONS = [

    "仔細觀察附近環境，尋找新的線索。",

    "主動與附近的人交談，試探對方的目的。",

    "暫時避開人群，找一個安全地方思考下一步。",

    "冒險靠近剛才發現的異常之處。",

]


# =========================================================
# 16. 處理回合
# =========================================================

def process_turn(
    action
):

    game = st.session_state.game_state

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

    game["processing"] = True

    game["last_error"] = ""

    success = False

    try:

        # =================================================
        # 查看狀態
        # =================================================

        if action.startswith(
            "查看狀態"
        ):

            player = game["player"]

            status_story = (

                "你暫時停下腳步。\n\n"

                "你仔細整理自己的狀態。\n\n"

                f"目前生命狀態為【"
                f"{player['hp']}/{player['max_hp']}"
                f"】。\n"

                f"體內靈力為【"
                f"{player['mp']}/{player['max_mp']}"
                f"】。\n"

                f"飽腹程度為【"
                f"{player['fullness']}/100"
                f"】。\n"

                f"身上共有【"
                f"{player['money']}"
                f"文錢】。\n\n"

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

            success = True

            return True

        # =================================================
        # AI
        # =================================================

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

        status_box = st.empty()

        status_box.info(
            "🔮 AI 正在推演劇情……"
        )

        # -------------------------------------------------
        # API
        # -------------------------------------------------

        raw = call_nemotron(
            messages,
            status_box
        )

        # -------------------------------------------------
        # JSON
        # -------------------------------------------------

        data = parse_json_response(
            raw
        )

        # -------------------------------------------------
        # JSON 修復
        # -------------------------------------------------

        if data is None:

            status_box.warning(
                "🛠️ AI 格式不完整，正在重新整理……"
            )

            repair_prompt = """
你上一個回答不是合法 JSON。

請重新輸出。

只可以輸出合法 JSON。

不要 Markdown。
不要三個反引號。
不要英文。

格式：

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

            repair_messages = [

                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },

                {
                    "role": "user",
                    "content": (
                        prompt
                        + "\n\n"
                        + "以下是模型剛才的回答：\n"
                        + raw[:6000]
                        + "\n\n"
                        + repair_prompt
                    ),
                },

            ]

            raw = call_nemotron(
                repair_messages,
                status_box
            )

            data = parse_json_response(
                raw
            )

        if data is None:

            raise RuntimeError(
                "模型連續兩次沒有回傳有效 JSON。"
            )

        # =================================================
        # 劇情
        # =================================================

        story = str(
            data.get(
                "story",
                ""
            )
        ).strip()

        if not story:

            raise RuntimeError(
                "模型成功連接，但沒有返回劇情內容。"
            )

        # =================================================
        # 重複檢查
        # =================================================

        if is_duplicate_story(
            story
        ):

            status_box.warning(
                "🔄 劇情過於相似，正在重新推演……"
            )

            retry_prompt = (
                build_game_prompt(
                    action
                )
                + """

上一個生成結果與上一回合過於相似。

這一次必須發生新的事件。

不要重複相同描述。

必須讓劇情真正向前發展。

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

            retry_raw = call_nemotron(
                retry_messages,
                status_box
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

        # =================================================
        # 更新數值
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

        player = game["player"]

        # =================================================
        # 飢餓
        # =================================================

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

        normalise_player(
            player
        )

        # =================================================
        # 回合數
        # =================================================

        game["turn"] += 1

        # =================================================
        # 摘要
        # =================================================

        summary = str(
            data.get(
                "story_summary_update",
                ""
            )
        ).strip()

        if summary:

            game["story_summary"] = (
                summary[:600]
            )

        # =================================================
        # 歷史
        # =================================================

        game["story_history"].append(

            "【第 "
            + str(
                game["turn"]
            )
            + " 回合】\n"
            + "你選擇："
            + action

        )

        game["story_history"].append(
            story
        )

        game["last_action"] = action

        game["last_story"] = story

        # =================================================
        # 限制歷史
        # =================================================

        if len(
            game["story_history"]
        ) > 40:

            game["story_history"] = (
                game["story_history"][-40:]
            )

        # =================================================
        # 選項
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

                if option:

                    valid_options.append(
                        option
                    )

        while len(
            valid_options
        ) < 4:

            valid_options.append(
                DEFAULT_OPTIONS[
                    len(valid_options)
                ]
            )

        valid_options = valid_options[:4]

        valid_options.append(
            "查看狀態"
        )

        game["current_options"] = (
            valid_options
        )

        game["last_error"] = ""

        success = True

        status_box.success(
            "✅ 本回合完成"
        )

        time.sleep(
            0.2
        )

        return True

    except Exception as error:

        # =================================================
        # 重要：
        # 錯誤一定保存到 session_state
        # 唔會再因 rerun 消失
        # =================================================

        error_text = str(
            error
        ).strip()

        if not error_text:

            error_text = (
                "未知錯誤。"
            )

        game["last_error"] = (
            error_text
        )

        game["last_error_time"] = (
            time.strftime(
                "%H:%M:%S"
            )
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

        "t": game.get(
            "turn",
            0
        ),

        "p": game.get(
            "player",
            {}
        ),

        "i": game.get(
            "inventory",
            []
        ),

        "n": game.get(
            "npcs",
            {}
        ),

        "s": game.get(
            "story_summary",
            ""
        ),

        "h": game.get(
            "story_history",
            []
        ),

        "o": game.get(
            "current_options",
            []
        ),

        "a": game.get(
            "last_action",
            ""
        ),

        "l": game.get(
            "last_story",
            ""
        ),

    }

    raw = json.dumps(
        save_data,
        ensure_ascii=False,
        separators=(
            ",",
            ":"
        )
    )

    return base64.b64encode(
        raw.encode(
            "utf-8"
        )
    ).decode(
        "ascii"
    )


# =========================================================
# 18. 讀檔
# =========================================================

def load_save(
    save_string
):

    save_string = str(
        save_string
    ).strip()

    if not save_string:

        raise ValueError(
            "存檔內容是空白的。"
        )

    data = None

    # -----------------------------------------------------
    # Base64
    # -----------------------------------------------------

    try:

        decoded = base64.b64decode(
            save_string
        ).decode(
            "utf-8"
        )

        data = json.loads(
            decoded
        )

    except Exception:

        # -------------------------------------------------
        # 舊 JSON
        # -------------------------------------------------

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
    # 新格式
    # -----------------------------------------------------

    if "p" in data:

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

            "last_error": "",

            "last_error_time": "",

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

        game_state["processing"] = False

        game_state["last_error"] = ""

        game_state["last_error_time"] = ""

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

    game_state["processing"] = False

    game_state["last_error"] = ""

    game_state["last_error_time"] = ""

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

    normalise_player(
        player
    )

    st.session_state.game_state = (
        game_state
    )

    st.session_state.game_started = True


# =========================================================
# 19. Session 初始化
# =========================================================

if "game_started" not in st.session_state:

    st.session_state.game_started = False


if "game_state" not in st.session_state:

    st.session_state.game_state = None


# =========================================================
# 20. CSS
# =========================================================

st.markdown(
    """
    <style>

    .story-box {
        border: 1px solid rgba(128,128,128,0.35);
        border-radius: 12px;
        padding: 18px;
        background: rgba(128,128,128,0.04);
    }

    .error-box {
        border: 1px solid #ff4b4b;
        border-radius: 10px;
        padding: 15px;
        background: rgba(255,75,75,0.08);
    }

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# 21. 標題
# =========================================================

st.title(
    "🌸 三界奇譚：小薯逆襲記"
)

st.caption(
    "V3.5 · Nemotron Free · 修仙文字 RPG"
)


# =========================================================
# 22. 開始頁
# =========================================================

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
# 23. 遊戲資料
# =========================================================

game = st.session_state.game_state

player = game["player"]

normalise_player(
    player
)


# =========================================================
# 24. Sidebar
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
        ]
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
# 25. 主線劇情
# =========================================================

if page == "📖 主線劇情":

    st.subheader(
        "📖 主線劇情"
    )

    # =====================================================
    # 錯誤顯示
    # =====================================================

    if game.get(
        "last_error",
        ""
    ):

        st.error(
            "❌ 今次行動沒有完成"
        )

        st.markdown(
            '<div class="error-box">',
            unsafe_allow_html=True
        )

        st.write(
            "錯誤時間："
            + str(
                game.get(
                    "last_error_time",
                    ""
                )
            )
        )

        st.write(
            game.get(
                "last_error",
                "未知錯誤"
            )
        )

        st.markdown(
            "</div>",
            unsafe_allow_html=True
        )

        if st.button(
            "✖️ 關閉錯誤提示",
            key="clear_error"
        ):

            game["last_error"] = ""

            game["last_error_time"] = ""

            st.rerun()

    # =====================================================
    # 劇情獨立滾動區
    # =====================================================

    story_height = 620

    with st.container(
        height=story_height,
        border=True
    ):

        for text in game.get(
            "story_history",
            []
        ):

            text = str(
                text
            )

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

        # -------------------------------------------------
        # 最底位置
        # -------------------------------------------------

        st.markdown(
            '<div id="rpg-story-bottom"></div>',
            unsafe_allow_html=True
        )

    # =====================================================
    # 到最底
    # =====================================================

    st.markdown(
        """
        <script>
        function scrollRPGStoryToBottom() {

            const elements =
                window.parent.document.querySelectorAll(
                    '[data-testid="stVerticalBlock"]'
                );

            if (!elements || elements.length === 0) {
                return;
            }

            let best = null;

            elements.forEach(function(el) {

                const style =
                    window.parent.getComputedStyle(el);

                if (
                    style.overflowY === "auto" ||
                    style.overflowY === "scroll"
                ) {

                    if (
                        !best ||
                        el.scrollHeight > best.scrollHeight
                    ) {
                        best = el;
                    }

                }

            });

            if (best) {

                best.scrollTo({
                    top: best.scrollHeight,
                    behavior: "smooth"
                });

            }

        }
        </script>

        <div style="
            display:flex;
            justify-content:flex-end;
            margin-top:8px;
            margin-bottom:8px;
        ">

        <button
            onclick="scrollRPGStoryToBottom()"
            style="
                border:1px solid rgba(128,128,128,0.5);
                border-radius:20px;
                padding:8px 16px;
                background:white;
                cursor:pointer;
                font-weight:600;
            "
        >
            ⬇️ 到最底
        </button>

        </div>
        """,
        unsafe_allow_html=True
    )

    # =====================================================
    # AI 狀態
    # =====================================================

    if game.get(
        "processing",
        False
    ):

        st.info(
            "🔮 AI 正在推演劇情……"
        )

    # =====================================================
    # 選項
    # =====================================================

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

        game["current_options"] = (
            options
        )

    for idx, option in enumerate(
        options
    ):

        button_key = (
            "turn_"
            + str(
                game["turn"]
            )
            + "_option_"
            + str(
                idx
            )
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

            # ------------------------------------------------
            # 重要修正：
            #
            # 成功 → rerun 更新畫面
            #
            # 失敗 → 都唔即刻 rerun
            #       令錯誤留喺畫面
            # ------------------------------------------------

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
# 26. 背包
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
                    desc
                )


# =========================================================
# 27. NPC
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
                f"🌸 {name}｜好感：{affinity}"
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
# 28. 存檔／讀檔
# =========================================================

elif page == "💾 存檔／讀檔":

    st.subheader(
        "💾 存檔／讀檔"
    )

    st.write(
        "新版存檔已經壓縮成較短的代碼，"
        "直接複製整段即可。"
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

                time.sleep(
                    0.3
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
# 29. Footer
# =========================================================

st.markdown("---")

st.caption(
    "三界奇譚 V3.5 · Nemotron Free · 修仙文字 RPG"
)
