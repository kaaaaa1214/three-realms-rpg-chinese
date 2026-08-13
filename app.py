import json
import random
import re
import time

import streamlit as st
from groq import Groq


# ============================================================
# 三界奇譚 V2
# ============================================================


# ============================================================
# 1. 頁面設定
# ============================================================

st.set_page_config(
    page_title="三界奇譚：小薯逆襲記",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# 2. Groq 設定
# ============================================================

GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")

if not GROQ_API_KEY:
    st.error("⚠️ 請先在 Streamlit Secrets 設定 GROQ_API_KEY")
    st.stop()

client = Groq(api_key=GROQ_API_KEY)

# 2026-08-12：
# Groq 官方已公告舊 Llama 3.1 8B 將於 2026-08-16 停用。
# 因此 V2 直接使用官方建議替代模型。
MODEL_NAME = "openai/gpt-oss-20b"


# ============================================================
# 3. Session State
# ============================================================

if "game_started" not in st.session_state:
    st.session_state.game_started = False

if "active_tab" not in st.session_state:
    st.session_state.active_tab = "📖 主線劇情"

if "current_options" not in st.session_state:
    st.session_state.current_options = []

if "last_usage" not in st.session_state:
    st.session_state.last_usage = None

if "last_error" not in st.session_state:
    st.session_state.last_error = ""

if "turn_number" not in st.session_state:
    st.session_state.turn_number = 0


# ============================================================
# 4. 五界開局資料
# ============================================================

LOCATIONS = [
    {
        "realm": "凡間",
        "loc": "凡間·青石鎮落魄流民所",
        "identity": "街頭乞討的孤苦孤兒",
        "bg": "父母雙亡，每日為下一頓飯發愁，在市井中看盡人情冷暖。",
        "style": "凡間講究人情、利益、權勢與生存。"
    },
    {
        "realm": "仙界",
        "loc": "仙界·凌霄外園雜役司",
        "identity": "九霄雲宮最底層雜役仙侍",
        "bg": "每天負責打掃仙園落花與倒夜香，是仙界最卑微的小薯。",
        "style": "仙界表面祥和莊嚴，實則階級森嚴，低階仙侍命如草芥。"
    },
    {
        "realm": "妖界",
        "loc": "妖界·萬妖山脈外圍暗谷",
        "identity": "被放養於荒谷的半妖奴隸",
        "bg": "混血身份在妖界備受排擠，只能在強大妖獸的爪下艱難求生。",
        "style": "妖界信奉血脈、力量與弱肉強食。"
    },
    {
        "realm": "魔界",
        "loc": "魔界·黑焰深淵礦區",
        "identity": "最低賤的魔鐵礦奴工",
        "bg": "每日承受魔氣侵蝕與監工皮鞭，過著見不到明天的日子。",
        "style": "魔界利益至上，弱者是資源，強者制定規則。"
    },
    {
        "realm": "靈界",
        "loc": "靈界·散修坊市破廟",
        "identity": "擺地攤維生的落魄散修",
        "bg": "靈根低下，功法殘缺，經常被修仙家族欺壓。",
        "style": "靈界宗門林立，散修、商會與世家互相角力。"
    }
]


POTENTIAL_BLOODLINES = [
    {
        "name": "鳳凰涅槃血脈",
        "hint": "偶爾會對火焰產生異常親近感，重傷時體內可能出現微弱暖意。"
    },
    {
        "name": "鴻蒙神魔同體印",
        "hint": "靈魂深處偶爾傳來神魔交織般的悸動。"
    },
    {
        "name": "太古星辰帝君遺脈",
        "hint": "夜空中的星辰偶爾會讓你產生莫名共鳴。"
    },
    {
        "name": "九幽妖皇真靈寄宿",
        "hint": "某些妖獸靠近你時，偶爾會出現本能性的畏懼。"
    }
]


# ============================================================
# 5. 開局事件庫
# ============================================================

OPENING_EVENTS = [
    {
        "type": "strange_object",
        "event": "你在不起眼的角落發現一件明顯不屬於底層人物的奇怪物品。",
        "hook": "物品看似普通，卻留下了一絲不尋常的靈力痕跡。"
    },
    {
        "type": "npc",
        "event": "你意外撞見一名行蹤可疑的人物。",
        "hook": "對方似乎正在隱瞞某件事情，而且並沒有注意到你的存在。"
    },
    {
        "type": "secret",
        "event": "你無意間聽見兩個身份不低的人談論一件不能讓外人知道的事情。",
        "hook": "你只聽見其中一部分，但足以察覺事情並不簡單。"
    },
    {
        "type": "danger",
        "event": "原本平靜的環境突然出現危險。",
        "hook": "危險並非直接衝著你而來，但你很可能被牽連。"
    },
    {
        "type": "opportunity",
        "event": "你發現了一個極其微小、卻可能改變命運的機會。",
        "hook": "機會看似唾手可得，但背後似乎也藏著代價。"
    }
]


# ============================================================
# 6. 工具函數
# ============================================================

def get_number(value, default=0):
    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return int(value)

    if isinstance(value, str):
        match = re.search(r"-?\d+", value)

        if match:
            return int(match.group())

    return default


def clamp(value, minimum, maximum):
    try:
        value = int(value)
    except Exception:
        value = minimum

    return max(minimum, min(value, maximum))


def make_stat(value, maximum):
    value = clamp(value, 0, maximum)
    return f"{value}/{maximum}"


def strip_markdown(text):
    if not isinstance(text, str):
        return ""

    text = text.replace("```json", "")
    text = text.replace("```", "")

    return text.strip()


def safe_json_load(text):
    text = strip_markdown(text)

    try:
        return json.loads(text)

    except Exception:

        start = text.find("{")
        end = text.rfind("}")

        if start >= 0 and end > start:

            possible = text[start:end + 1]

            return json.loads(possible)

        raise


# ============================================================
# 7. 初始化遊戲
# ============================================================

def create_initial_game(player_name):

    location = random.choice(LOCATIONS)

    bloodline = random.choice(
        POTENTIAL_BLOODLINES
    )

    opening_event = random.choice(
        OPENING_EVENTS
    )

    name = player_name.strip()

    if not name:
        name = "詩柔"

    player = {
        "name": name,

        "identity": (
            f"{location['loc']}·"
            f"{location['identity']}"
        ),

        "secret_bloodline": bloodline["name"],

        "bloodline_hint": bloodline["hint"],

        "bloodline_awakened": False,

        "hp": "100/100",
        "mp": "30/30",
        "fullness": "90/100",

        "money": 5,

        "realm": "凡俗之軀 / 煉氣期一層",

        "location": location["loc"],

        "status": "健康",

        "comprehension": random.randint(8, 12),
        "fortune": random.randint(8, 12),
        "charm": random.randint(8, 12),

        "righteousness": 0,
        "evil_aura": 0,
        "fame": 0
    }

    game_state = {

        "player": player,

        "world": {
            "realm": location["realm"],
            "location": location["loc"],
            "world_style": location["style"],
            "background": location["bg"],

            "opening_event": opening_event,

            "turn": 0
        },

        "inventory": [
            {
                "name": "粗布麻衣",
                "count": 1,
                "desc": "極為普通的日常衣物，早已磨損。"
            },
            {
                "name": "乾糧清水",
                "count": 2,
                "desc": "普通粗糧與清水，可暫時充飢。"
            }
        ],

        "npcs": {},

        "story_history": [],

        "story_summary": (
            f"你目前身處{location['loc']}，"
            f"身份是{location['identity']}。"
            f"身無長物，只剩5文錢。"
        ),

        "clues": [],

        "quests": [],

        "last_scene": "",

        "turn": 0
    }

    return game_state


# ============================================================
# 8. 初始劇情 AI Prompt
# ============================================================

OPENING_SYSTEM = """
你是古典修仙文字RPG的遊戲主持人。

你現在要替玩家建立真正的第一幕。

不要寫成遊戲說明書。
不要只是描述「你醒來了」然後結束。
第一幕必須在開頭就出現一個具體事件、人物、異常、危機或機會。

要求：

一、全程使用繁體中文。
二、全程使用第二人稱「你」。
三、半文半白古典修仙小說風格。
四、約350至500字。
五、一定要有具體環境描寫。
六、一定要有一個可以繼續追查的事件。
七、至少出現一個具體線索。
八、不要直接揭露玩家隱藏血脈。
九、不要讓玩家突然獲得強大力量。
十、不要讓劇情一次跳過數日或數月。
十一、不要自行修改玩家的身份與開局設定。

最後必須輸出純JSON：

{
  "story": "第一幕完整劇情",
  "story_summary": "80字內摘要",
  "clues": ["線索1", "線索2"],
  "options": [
    "1 ...（意圖或風險）",
    "2 ...（意圖或風險）",
    "3 ...（意圖或風險）",
    "4 ...（意圖或風險）",
    "5 查看當前狀態與身心狀況"
  ],
  "npc_updates": []
}

選項1至4必須完全根據剛才發生的劇情設計。
不能突然出現上一幕不存在的地點、人物或物品。
"""


def generate_opening(player_name):

    game = create_initial_game(
        player_name
    )

    player = game["player"]
    world = game["world"]

    prompt_data = {
        "玩家": {
            "名字": player["name"],
            "身份": player["identity"],
            "境界": player["realm"],
            "位置": player["location"],
            "金錢": player["money"]
        },

        "世界": {
            "界域": world["realm"],
            "背景": world["background"],
            "世界規則": world["world_style"]
        },

        "開局事件": world["opening_event"],

        "重要規則": [
            "玩家身懷秘密血脈，但你不知道其真實名稱。",
            "不能直接揭露秘密血脈。",
            "玩家目前極其弱小。",
            "第一幕必須有具體事件。",
            "選項必須根據第一幕內容生成。"
        ]
    }

    prompt = json.dumps(
        prompt_data,
        ensure_ascii=False,
        separators=(",", ":")
    )

    with st.status(
        "🌌 正在為你生成命運開局……",
        expanded=True
    ) as status:

        try:

            response = client.chat.completions.create(

                model=MODEL_NAME,

                messages=[
                    {
                        "role": "system",
                        "content": OPENING_SYSTEM
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],

                temperature=0.9,

                max_tokens=1000,

                response_format={
                    "type": "json_object"
                }
            )

            raw = (
                response
                .choices[0]
                .message
                .content
            )

            data = safe_json_load(raw)

            story = data.get(
                "story",
                ""
            )

            if not story:
                raise ValueError(
                    "AI 沒有生成開局劇情。"
                )

            game["story_history"] = [
                story
            ]

            game["last_scene"] = story

            game["story_summary"] = (
                str(
                    data.get(
                        "story_summary",
                        game["story_summary"]
                    )
                )[:500]
            )

            game["clues"] = [
                str(x)
                for x in data.get(
                    "clues",
                    []
                )
            ][:5]

            npc_updates = clean_npcs(
                data.get(
                    "npc_updates",
                    []
                )
            )

            for npc in npc_updates:
                game["npcs"][
                    npc["name"]
                ] = npc

            options = clean_options(
                data.get(
                    "options",
                    []
                )
            )

            game["turn"] = 1

            st.session_state.game_state = game

            st.session_state.current_options = options

            st.session_state.game_started = True

            st.session_state.turn_number = 1

            usage = getattr(
                response,
                "usage",
                None
            )

            if usage:

                st.session_state.last_usage = {
                    "prompt": getattr(
                        usage,
                        "prompt_tokens",
                        0
                    ),

                    "completion": getattr(
                        usage,
                        "completion_tokens",
                        0
                    ),

                    "total": getattr(
                        usage,
                        "total_tokens",
                        0
                    )
                }

            status.update(
                label="✨ 命運已開啟",
                state="complete",
                expanded=False
            )

            return True

        except Exception as e:

            status.update(
                label="❌ 開局生成失敗",
                state="error",
                expanded=True
            )

            st.session_state.last_error = str(e)

            st.error(
                f"開局失敗：{str(e)}"
            )

            return False


# ============================================================
# 9. 選項清理
# ============================================================

def clean_options(options):

    if not isinstance(
        options,
        list
    ):
        options = []

    cleaned = []

    for option in options:

        if not isinstance(
            option,
            str
        ):
            continue

        option = option.strip()

        if not option:
            continue

        cleaned.append(option)

    if len(cleaned) >= 4:

        cleaned = cleaned[:4]

    else:

        cleaned = [
            "1 暫時躲在暗處觀察周圍動靜。（安全，但可能錯過機會）",

            "2 主動接近眼前的人物，試探對方身份。（可能獲得情報，也可能暴露自己）",

            "3 搜查附近環境，尋找更多線索。（可能發現機緣，也可能觸發危險）",

            "4 先行離開現場，尋找更安全的位置。（穩妥，但可能失去機會）"
        ]

    cleaned.append(
        "5 查看當前狀態與身心狀況"
    )

    return cleaned


# ============================================================
# 10. NPC 清理
# ============================================================

def clean_npcs(items):

    if not isinstance(
        items,
        list
    ):
        return []

    cleaned = []

    for npc in items:

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

        affinity = clamp(
            get_number(
                npc.get(
                    "affinity",
                    0
                ),
                0
            ),
            -100,
            100
        )

        cleaned.append(
            {
                "name": name,

                "identity": str(
                    npc.get(
                        "identity",
                        "身份不明"
                    )
                )[:100],

                "affinity": affinity,

                "relationship": str(
                    npc.get(
                        "relationship",
                        "陌生"
                    )
                )[:100],

                "key_memory": str(
                    npc.get(
                        "key_memory",
                        ""
                    )
                )[:300],

                "motivation": str(
                    npc.get(
                        "motivation",
                        ""
                    )
                )[:200]
            }
        )

    return cleaned


# ============================================================
# 11. 玩家數值保護
# ============================================================

def apply_player_update(old, update):

    new = old.copy()

    if not isinstance(
        update,
        dict
    ):
        return new

    # --------------------------------------------------------
    # HP
    # --------------------------------------------------------

    old_hp = get_number(
        old.get(
            "hp",
            "100/100"
        ),
        100
    )

    if "hp" in update:

        new_hp = get_number(
            update["hp"],
            old_hp
        )

        new_hp = clamp(
            new_hp,
            max(0, old_hp - 30),
            min(100, old_hp + 15)
        )

        new["hp"] = make_stat(
            new_hp,
            100
        )

    # --------------------------------------------------------
    # MP
    # --------------------------------------------------------

    old_mp = get_number(
        old.get(
            "mp",
            "30/30"
        ),
        30
    )

    if "mp" in update:

        new_mp = get_number(
            update["mp"],
            old_mp
        )

        new_mp = clamp(
            new_mp,
            max(0, old_mp - 20),
            min(30, old_mp + 15)
        )

        new["mp"] = make_stat(
            new_mp,
            30
        )

    # --------------------------------------------------------
    # 飽腹
    # --------------------------------------------------------

    old_fullness = get_number(
        old.get(
            "fullness",
            "90/100"
        ),
        90
    )

    if "fullness" in update:

        new_fullness = get_number(
            update["fullness"],
            old_fullness
        )

        new_fullness = clamp(
            new_fullness,
            max(0, old_fullness - 8),
            min(100, old_fullness + 30)
        )

        new["fullness"] = make_stat(
            new_fullness,
            100
        )

    # --------------------------------------------------------
    # 金錢
    # --------------------------------------------------------

    old_money = get_number(
        old.get(
            "money",
            0
        ),
        0
    )

    if "money" in update:

        new_money = get_number(
            update["money"],
            old_money
        )

        new_money = clamp(
            new_money,
            max(0, old_money - 50),
            old_money + 50
        )

        new["money"] = new_money

    # --------------------------------------------------------
    # 文字資料
    # --------------------------------------------------------

    for field in [
        "identity",
        "realm",
        "location",
        "status"
    ]:

        if field in update:

            value = str(
                update[field]
            ).strip()

            if value:
                new[field] = value

    # --------------------------------------------------------
    # 屬性
    # --------------------------------------------------------

    for field in [
        "comprehension",
        "fortune",
        "charm",
        "righteousness",
        "evil_aura",
        "fame"
    ]:

        if field in update:

            old_value = get_number(
                old.get(
                    field,
                    0
                ),
                0
            )

            new_value = get_number(
                update[field],
                old_value
            )

            new_value = clamp(
                new_value,
                old_value - 10,
                old_value + 10
            )

            new[field] = new_value

    # --------------------------------------------------------
    # 血脈覺醒
    # --------------------------------------------------------

    if old.get(
        "bloodline_awakened",
        False
    ):

        new["bloodline_awakened"] = True

    else:

        new["bloodline_awakened"] = bool(
            update.get(
                "bloodline_awakened",
                False
            )
        )

    return new


# ============================================================
# 12. 背包清理
# ============================================================

def clean_inventory(items):

    if not isinstance(
        items,
        list
    ):
        return []

    cleaned = []

    for item in items:

        if not isinstance(
            item,
            dict
        ):
            continue

        name = str(
            item.get(
                "name",
                ""
            )
        ).strip()

        if not name:
            continue

        count = get_number(
            item.get(
                "count",
                0
            ),
            0
        )

        if count <= 0:
            continue

        cleaned.append(
            {
                "name": name[:80],

                "count": min(
                    count,
                    999
                ),

                "desc": str(
                    item.get(
                        "desc",
                        "普通物品。"
                    )
                )[:200]
            }
        )

    return cleaned


# ============================================================
# 13. 建立精簡記憶
# ============================================================

def build_memory():

    game = st.session_state.game_state

    player = game["player"]

    # --------------------------------------------------------
    # 只保留真正有用的玩家資料
    # --------------------------------------------------------

    safe_player = {

        "名字": player["name"],

        "身份": player["identity"],

        "境界": player["realm"],

        "位置": player["location"],

        "狀態": player["status"],

        "生命": player["hp"],

        "靈力": player["mp"],

        "飽腹": player["fullness"],

        "金錢": player["money"],

        "悟性": player["comprehension"],

        "福緣": player["fortune"],

        "魅力": player["charm"],

        "正氣": player["righteousness"],

        "煞氣": player["evil_aura"],

        "威名": player["fame"],

        "血脈是否覺醒": player[
            "bloodline_awakened"
        ]
    }

    # --------------------------------------------------------
    # 最近兩幕
    # --------------------------------------------------------

    history = game.get(
        "story_history",
        []
    )

    recent_history = history[-2:]

    # --------------------------------------------------------
    # 最近NPC
    # --------------------------------------------------------

    npcs = game.get(
        "npcs",
        {}
    )

    npc_list = list(
        npcs.values()
    )[-6:]

    # --------------------------------------------------------
    # 最近線索
    # --------------------------------------------------------

    clues = game.get(
        "clues",
        []
    )[-8:]

    return {

        "劇情摘要": game.get(
            "story_summary",
            ""
        ),

        "上一幕": game.get(
            "last_scene",
            ""
        ),

        "最近劇情": recent_history,

        "玩家": safe_player,

        "背包": game.get(
            "inventory",
            []
        ),

        "已知人物": npc_list,

        "已知線索": clues,

        "回合": game.get(
            "turn",
            0
        )
    }


# ============================================================
# 14. RPG 主系統指令
# ============================================================

GAME_SYSTEM = """
你是一個高品質古典修仙文字RPG的遊戲主持人。

你的工作不是單純寫小說，而是維持一個可以長期遊玩的互動世界。

【語言】

必須全程使用自然、流暢的繁體中文。
不得輸出英文。
不得輸出Markdown。
最終只能輸出有效JSON。

【視角】

永遠使用第二人稱「你」。

【風格】

半文半白古典修仙小說。

文字要有：
環境；
聲音；
氣味；
光影；
人物表情；
人物動機；
危機；
線索；
選擇後果。

避免空泛句子，例如：
「命運的齒輪開始轉動。」
「一切似乎都在等待著你。」
「四周一片寂靜。」

除非這些句子真的服務劇情，否則不要使用。

【核心原則】

你必須承接上一幕。

玩家做了什麼，就從那件事繼續。

不要重複描述玩家剛剛做過的事情。

不要重新介紹世界。

不要突然增加不存在的人物、地點、物品。

如果要新增人物、地點或物品，必須在劇情中自然介紹。

【世界邏輯】

玩家目前非常弱。

不能因為玩家是主角，就讓NPC無條件尊敬玩家。

NPC有自己的：
身份；
利益；
秘密；
性格；
目標；
恐懼。

NPC可能撒謊。
NPC可能利用玩家。
NPC也可能幫助玩家。

【隱藏血脈】

玩家有一條秘密血脈。

你不知道秘密血脈的真正名稱。

絕對不能猜測、揭露或直接寫出血脈名稱。

只有當遊戲資料明確表示「血脈已覺醒」時，才可以描寫覺醒。

在覺醒之前，只能出現非常微弱的異象，而且不能明說原因。

【數值】

不要亂改數值。

普通行動不應突然讓玩家：
大幅回血；
大幅增加金錢；
突然提升境界；
突然獲得神級法寶。

戰鬥、受傷、修煉、吃東西、購買物品，都要有合理原因。

【劇情長度】

每回合約350至500字。

不要一次跳過大量時間。

一回合最多推進一小段事件。

【選項】

劇情結束後提供4個真正有意義的行動。

四個選項必須根據本幕劇情而來。

例如玩家剛發現一個可疑人物：

1 可以跟蹤；
2 可以接近試探；
3 可以躲起來觀察；
4 可以離開並尋找情報。

不要提供與本幕無關的選項。

第五個固定：

5 查看當前狀態與身心狀況

【線索】

如果本幕產生重要線索，加入 clues_update。

線索必須真實存在於劇情。

【NPC】

如果新人物出現，加入npc_updates。

如果舊人物的態度或記憶改變，也更新該人物。

【輸出】

必須輸出：

{
  "story": "350至500字劇情",
  "story_summary_update": "80字內摘要",
  "clues_update": [
    "本幕新線索"
  ],
  "player_update": {
    "hp": "100/100",
    "mp": "30/30",
    "fullness": "85/100",
    "money": 5,
    "realm": "目前境界",
    "location": "目前位置",
    "status": "目前狀態",
    "comprehension": 10,
    "fortune": 10,
    "charm": 10,
    "righteousness": 0,
    "evil_aura": 0,
    "fame": 0,
    "bloodline_awakened": false
  },
  "inventory_update": [],
  "npc_updates": [],
  "options": [
    "1 ...（意圖或風險）",
    "2 ...（意圖或風險）",
    "3 ...（意圖或風險）",
    "4 ...（意圖或風險）",
    "5 查看當前狀態與身心狀況"
  ]
}

不要輸出任何其他內容。
"""


# ============================================================
# 15. 建立回合 Prompt
# ============================================================

def build_turn_prompt(action):

    memory = build_memory()

    prompt_data = {

        "遊戲記憶": memory,

        "玩家這一回合的行動": action,

        "重要規則": [
            "必須承接上一幕。",
            "不能重複玩家剛剛做過的事情。",
            "不能洩露秘密血脈。",
            "不要突然提升玩家境界。",
            "選項必須從本幕劇情產生。",
            "本幕必須出現具體事件或發展。",
            "如果玩家行動很普通，也要讓世界自然產生反應。"
        ]
    }

    return json.dumps(
        prompt_data,
        ensure_ascii=False,
        separators=(",", ":")
    )


# ============================================================
# 16. 處理回合
# ============================================================

def process_turn(player_action):

    game = st.session_state.game_state

    prompt = build_turn_prompt(
        player_action
    )

    with st.status(
        "🔮 正在推演三界命運……",
        expanded=True
    ) as status:

        try:

            response = client.chat.completions.create(

                model=MODEL_NAME,

                messages=[
                    {
                        "role": "system",
                        "content": GAME_SYSTEM
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],

                temperature=0.82,

                max_tokens=1100,

                response_format={
                    "type": "json_object"
                }
            )

            raw = (
                response
                .choices[0]
                .message
                .content
            )

            data = safe_json_load(
                raw
            )

            # ------------------------------------------------
            # 劇情
            # ------------------------------------------------

            story = str(
                data.get(
                    "story",
                    ""
                )
            ).strip()

            if not story:

                raise ValueError(
                    "AI 沒有返回劇情。"
                )

            # ------------------------------------------------
            # 玩家行動紀錄
            # ------------------------------------------------

            game[
                "story_history"
            ].append(
                {
                    "type": "action",
                    "text": player_action
                }
            )

            game[
                "story_history"
            ].append(
                {
                    "type": "story",
                    "text": story
                }
            )

            # ------------------------------------------------
            # 玩家數值
            # ------------------------------------------------

            update = data.get(
                "player_update",
                {}
            )

            game["player"] = (
                apply_player_update(
                    game["player"],
                    update
                )
            )

            # ------------------------------------------------
            # 背包
            # ------------------------------------------------

            if "inventory_update" in data:

                inventory = clean_inventory(
                    data["inventory_update"]
                )

                if inventory:

                    game[
                        "inventory"
                    ] = inventory

            # ------------------------------------------------
            # NPC
            # ------------------------------------------------

            npc_updates = clean_npcs(
                data.get(
                    "npc_updates",
                    []
                )
            )

            for npc in npc_updates:

                game[
                    "npcs"
                ][npc["name"]] = npc

            # ------------------------------------------------
            # 線索
            # ------------------------------------------------

            new_clues = data.get(
                "clues_update",
                []
            )

            if isinstance(
                new_clues,
                list
            ):

                for clue in new_clues:

                    clue = str(
                        clue
                    ).strip()

                    if (
                        clue
                        and clue not in game[
                            "clues"
                        ]
                    ):

                        game[
                            "clues"
                        ].append(
                            clue
                        )

            # 最多保留15條
            game["clues"] = game[
                "clues"
            ][-15:]

            # ------------------------------------------------
            # 摘要
            # ------------------------------------------------

            summary = str(
                data.get(
                    "story_summary_update",
                    game.get(
                        "story_summary",
                        ""
                    )
                )
            )

            game[
                "story_summary"
            ] = summary[:600]

            # ------------------------------------------------
            # Last Scene
            # ------------------------------------------------

            game[
                "last_scene"
            ] = story

            # ------------------------------------------------
            # Turn
            # ------------------------------------------------

            game["turn"] = (
                game.get(
                    "turn",
                    0
                ) + 1
            )

            st.session_state.turn_number = (
                game["turn"]
            )

            # ------------------------------------------------
            # 限制本地歷史
            #
            # 只影響存檔大小。
            # AI 只會收到最近兩幕。
            # ------------------------------------------------

            if len(
                game["story_history"]
            ) > 40:

                game[
                    "story_history"
                ] = (
                    game[
                        "story_history"
                    ][-40:]
                )

            # ------------------------------------------------
            # 選項
            # ------------------------------------------------

            options = clean_options(
                data.get(
                    "options",
                    []
                )
            )

            st.session_state.current_options = (
                options
            )

            # ------------------------------------------------
            # Usage
            # ------------------------------------------------

            usage = getattr(
                response,
                "usage",
                None
            )

            if usage:

                st.session_state.last_usage = {

                    "prompt":
                        getattr(
                            usage,
                            "prompt_tokens",
                            0
                        ),

                    "completion":
                        getattr(
                            usage,
                            "completion_tokens",
                            0
                        ),

                    "total":
                        getattr(
                            usage,
                            "total_tokens",
                            0
                        )
                }

            st.session_state.last_error = ""

            status.update(
                label="✨ 命運推演完成",
                state="complete",
                expanded=False
            )

        except Exception as e:

            error = str(e)

            st.session_state.last_error = (
                error
            )

            status.update(
                label="❌ 劇情生成失敗",
                state="error",
                expanded=True
            )

            if (
                "429" in error
                or "rate_limit" in error.lower()
            ):

                st.error(
                    "⚠️ Groq 目前達到速率限制。\n\n"
                    "通常是短時間內 Token 使用量太高。"
                    "稍等一陣再試即可。"
                )

            elif (
                "json" in error.lower()
                or "parse" in error.lower()
            ):

                st.error(
                    "⚠️ AI 返回格式異常。\n"
                    "請再試一次相同選項。"
                )

            else:

                st.error(
                    "❌ AI 發生錯誤：\n"
                    + error
                )


# ============================================================
# 17. 狀態頁
# ============================================================

def render_status():

    p = st.session_state.game_state[
        "player"
    ]

    st.subheader(
        "📊 當前狀態"
    )

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "❤️ 生命",
            p["hp"]
        )

        st.metric(
            "💙 靈力",
            p["mp"]
        )

        st.metric(
            "🍚 飽腹",
            p["fullness"]
        )

        st.metric(
            "💰 金錢",
            f"{p['money']} 文"
        )

    with col2:

        st.write(
            f"🏷️ **境界：** {p['realm']}"
        )

        st.write(
            f"📍 **位置：** {p['location']}"
        )

        st.write(
            f"🩺 **狀態：** {p['status']}"
        )

        st.write(
            f"🧠 **悟性：** {p['comprehension']}"
        )

        st.write(
            f"🎲 **福緣：** {p['fortune']}"
        )

        st.write(
            f"✨ **魅力：** {p['charm']}"
        )

        st.write(
            f"⚖️ **正氣：** {p['righteousness']}"
        )

        st.write(
            f"🩸 **煞氣：** {p['evil_aura']}"
        )

        st.write(
            f"👑 **威名：** {p['fame']}"
        )


# ============================================================
# 18. 存檔
# ============================================================

def create_save_data():

    return {
        "version": "V2",

        "game_state":
            st.session_state.game_state,

        "current_options":
            st.session_state.current_options
    }


def create_save_string():

    return json.dumps(
        create_save_data(),
        ensure_ascii=False
    )


# ============================================================
# 19. 讀檔
# ============================================================

def load_save_string(save_string):

    try:

        data = json.loads(
            save_string.strip()
        )

        game = data.get(
            "game_state"
        )

        if not isinstance(
            game,
            dict
        ):
            return False

        if "player" not in game:
            return False

        if "inventory" not in game:
            game["inventory"] = []

        if "npcs" not in game:
            game["npcs"] = {}

        if "story_history" not in game:
            game["story_history"] = []

        if "story_summary" not in game:
            game["story_summary"] = ""

        if "clues" not in game:
            game["clues"] = []

        if "last_scene" not in game:
            game["last_scene"] = ""

        if "turn" not in game:
            game["turn"] = 0

        st.session_state.game_state = game

        st.session_state.current_options = (
            data.get(
                "current_options",
                []
            )
        )

        st.session_state.game_started = True

        st.session_state.turn_number = (
            game.get(
                "turn",
                0
            )
        )

        return True

    except Exception:

        return False


# ============================================================
# 20. 標題
# ============================================================

st.title(
    "🌸 三界奇譚：小薯逆襲記"
)


# ============================================================
# 21. 未開始遊戲
# ============================================================

if not st.session_state.game_started:

    st.subheader(
        "🎲 踏入命途"
    )

    st.write(
        "五界隨機開局，每一次人生都可能完全不同。"
    )

    with st.form(
        "start_game_form"
    ):

        player_name = st.text_input(
            "請輸入你的名字：",
            value="詩柔"
        )

        start = st.form_submit_button(
            "🎲 開啟逆襲人生",
            use_container_width=True
        )

        if start:

            if generate_opening(
                player_name
            ):

                st.rerun()

    st.markdown("---")

    st.subheader(
        "💾 讀取舊存檔"
    )

    old_save = st.text_area(
        "請貼上存檔代碼：",
        height=200,
        key="opening_load"
    )

    if st.button(
        "📂 讀取存檔",
        use_container_width=True
    ):

        if old_save.strip():

            if load_save_string(
                old_save
            ):

                st.success(
                    "✅ 讀取成功！"
                )

                st.rerun()

            else:

                st.error(
                    "❌ 存檔格式錯誤。"
                )


# ============================================================
# 22. 遊戲開始後
# ============================================================

else:

    game = (
        st.session_state.game_state
    )

    player = game["player"]

    # ========================================================
    # Sidebar
    # ========================================================

    with st.sidebar:

        st.header(
            "📌 逆襲導航"
        )

        st.write(
            f"👤 **{player['name']}**"
        )

        st.write(
            f"🏷️ {player['realm']}"
        )

        st.write(
            f"📍 {player['location']}"
        )

        st.markdown("---")

        col1, col2 = st.columns(2)

        col1.metric(
            "❤️ HP",
            player["hp"]
        )

        col2.metric(
            "💙 MP",
            player["mp"]
        )

        col3, col4 = st.columns(2)

        col3.metric(
            "🍚 飽腹",
            player["fullness"]
        )

        col4.metric(
            "💰 金錢",
            f"{player['money']} 文"
        )

        # ----------------------------------------------------
        # 屬性
        # ----------------------------------------------------

        with st.expander(
            "📊 詳細屬性",
            expanded=True
        ):

            st.write(
                f"🧠 悟性："
                f"{player['comprehension']}"
            )

            st.write(
                f"🎲 福緣："
                f"{player['fortune']}"
            )

            st.write(
                f"✨ 魅力："
                f"{player['charm']}"
            )

            st.write(
                f"⚖️ 正氣："
                f"{player['righteousness']}"
            )

            st.write(
                f"🩸 煞氣："
                f"{player['evil_aura']}"
            )

            st.write(
                f"👑 威名："
                f"{player['fame']}"
            )

            st.write(
                f"🩺 狀態："
                f"{player['status']}"
            )

            if player.get(
                "bloodline_awakened",
                False
            ):

                st.success(
                    "🔥 身世已覺醒："
                    + player[
                        "secret_bloodline"
                    ]
                )

            else:

                st.info(
                    "🔒 身世之謎：尚未覺醒"
                )

        # ----------------------------------------------------
        # Token
        # ----------------------------------------------------

        if st.session_state.last_usage:

            with st.expander(
                "📊 最近一次 AI 用量",
                expanded=False
            ):

                usage = (
                    st.session_state.last_usage
                )

                st.write(
                    f"輸入："
                    f"{usage['prompt']} tokens"
                )

                st.write(
                    f"輸出："
                    f"{usage['completion']} tokens"
                )

                st.write(
                    f"合計："
                    f"{usage['total']} tokens"
                )

        # ----------------------------------------------------
        # 導航
        # ----------------------------------------------------

        st.markdown("---")

        if st.button(
            "📖 主線劇情",
            use_container_width=True
        ):

            st.session_state.active_tab = (
                "📖 主線劇情"
            )

            st.rerun()

        if st.button(
            "🎒 我的背包",
            use_container_width=True
        ):

            st.session_state.active_tab = (
                "🎒 我的背包"
            )

            st.rerun()

        if st.button(
            "👥 人物關係",
            use_container_width=True
        ):

            st.session_state.active_tab = (
                "👥 人物關係"
            )

            st.rerun()

        if st.button(
            "🔎 已知線索",
            use_container_width=True
        ):

            st.session_state.active_tab = (
                "🔎 已知線索"
            )

            st.rerun()

        if st.button(
            "💾 存檔 / 讀檔",
            use_container_width=True
        ):

            st.session_state.active_tab = (
                "💾 存檔 / 讀檔"
            )

            st.rerun()

        st.markdown("---")

        if st.button(
            "🎲 重開新局",
            use_container_width=True
        ):

            st.session_state.game_started = False

            st.session_state.game_state = {}

            st.session_state.current_options = []

            st.session_state.turn_number = 0

            st.session_state.active_tab = (
                "📖 主線劇情"
            )

            st.rerun()

    # ========================================================
    # 主要內容
    # ========================================================

    current_view = (
        st.session_state.active_tab
    )

    # ========================================================
    # 主線劇情
    # ========================================================

    if current_view == "📖 主線劇情":

        st.subheader(
            f"📖 主線劇情"
            f"　｜　第 {game.get('turn', 0)} 回合"
        )

        # ----------------------------------------------------
        # 顯示歷史
        # ----------------------------------------------------

        for entry in game[
            "story_history"
        ]:

            if isinstance(
                entry,
                dict
            ):

                entry_type = entry.get(
                    "type"
                )

                text = entry.get(
                    "text",
                    ""
                )

                if entry_type == "action":

                    st.info(
                        f"👉 **你選擇了：**\n\n"
                        f"{text}"
                    )

                else:

                    st.write(text)

            else:

                st.write(entry)

        # ----------------------------------------------------
        # 線索提醒
        # ----------------------------------------------------

        if game.get(
            "clues"
        ):

            with st.expander(
                "🔎 目前掌握的線索",
                expanded=False
            ):

                for clue in game[
                    "clues"
                ][-5:]:

                    st.write(
                        "• " + clue
                    )

        st.markdown("---")

        st.write(
            "✨ **你打算怎麼做？**"
        )

        # ----------------------------------------------------
        # 選項
        # ----------------------------------------------------

        option_key_base = (
            f"turn_{game.get('turn', 0)}"
        )

        for index, option in enumerate(
            st.session_state.current_options
        ):

            key = (
                f"{option_key_base}_"
                f"option_{index}"
            )

            if st.button(
                option,
                key=key,
                use_container_width=True
            ):

                if option.startswith(
                    "5"
                ):

                    render_status()

                else:

                    process_turn(
                        option
                    )

                    st.rerun()

        # ----------------------------------------------------
        # 自由行動
        # ----------------------------------------------------

        st.markdown("---")

        st.write(
            "💬 **自由意念**"
        )

        custom_action = st.text_input(
            "不一定要跟選項走，你可以自己決定行動：",
            key="custom_action",
            placeholder=(
                "例如：我不靠近那個人，"
                "而是先躲到柱子後面偷聽。"
            )
        )

        if st.button(
            "🚀 執行我的行動",
            use_container_width=True
        ):

            action = custom_action.strip()

            if action:

                process_turn(
                    action
                )

                st.session_state.custom_action = ""

                st.rerun()

            else:

                st.warning(
                    "請先輸入你的行動。"
                )

    # ========================================================
    # 背包
    # ========================================================

    elif current_view == "🎒 我的背包":

        st.subheader(
            "🎒 我的背包"
        )

        inventory = game[
            "inventory"
        ]

        if not inventory:

            st.info(
                "背包目前是空的。"
            )

        else:

            for item in inventory:

                with st.container(
                    border=True
                ):

                    st.write(
                        f"### "
                        f"【{item['name']}】"
                    )

                    st.write(
                        f"數量："
                        f"{item['count']}"
                    )

                    st.write(
                        item["desc"]
                    )

    # ========================================================
    # NPC
    # ========================================================

    elif current_view == "👥 人物關係":

        st.subheader(
            "👥 三界人物關係"
        )

        npcs = game[
            "npcs"
        ]

        if not npcs:

            st.info(
                "目前尚未結識任何重要人物。"
            )

        else:

            for name, npc in npcs.items():

                affinity = npc.get(
                    "affinity",
                    0
                )

                with st.expander(
                    f"🌸 {name}"
                    f"　｜　好感：{affinity}",
                    expanded=True
                ):

                    st.write(
                        f"**身份：** "
                        f"{npc.get('identity', '')}"
                    )

                    st.write(
                        f"**關係：** "
                        f"{npc.get('relationship', '')}"
                    )

                    st.write(
                        f"**印象：** "
                        f"{npc.get('key_memory', '')}"
                    )

                    if npc.get(
                        "motivation"
                    ):

                        st.write(
                            f"**目前目的：** "
                            f"{npc['motivation']}"
                        )

    # ========================================================
    # 線索
    # ========================================================

    elif current_view == "🔎 已知線索":

        st.subheader(
            "🔎 已知線索"
        )

        clues = game.get(
            "clues",
            []
        )

        if not clues:

            st.info(
                "目前沒有明確線索。"
            )

        else:

            for index, clue in enumerate(
                clues,
                start=1
            ):

                st.write(
                    f"**線索 {index}**"
                )

                st.info(
                    clue
                )

    # ========================================================
    # 存檔
    # ========================================================

    elif current_view == "💾 存檔 / 讀檔":

        st.subheader(
            "💾 存檔與讀檔"
        )

        st.write(
            "將以下存檔代碼完整複製保存。"
            "日後可以貼回來繼續遊戲。"
        )

        save_string = create_save_string()

        st.text_area(
            "📋 當前存檔代碼",
            value=save_string,
            height=300,
            key="save_output"
        )

        st.markdown("---")

        load_string = st.text_area(
            "📥 貼上舊存檔代碼",
            height=300,
            key="load_input"
        )

        if st.button(
            "🔄 載入存檔",
            use_container_width=True
        ):

            if not load_string.strip():

                st.warning(
                    "請先貼上存檔代碼。"
                )

            else:

                if load_save_string(
                    load_string
                ):

                    st.success(
                        "✅ 存檔載入成功！"
                    )

                    time.sleep(0.5)

                    st.rerun()

                else:

                    st.error(
                        "❌ 存檔格式錯誤，"
                        "請確認是否完整複製。"
                    )
