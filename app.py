import json
import random
import re
import time

import streamlit as st
from groq import Groq


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

API_KEY = st.secrets.get("GROQ_API_KEY", "")

if not API_KEY:
    st.error("⚠️ 請先在 Streamlit Secrets 設定 GROQ_API_KEY")
    st.stop()

client = Groq(api_key=API_KEY)

# 目前使用較省 quota 的模型
MODEL_NAME = "llama-3.1-8b-instant"


# ============================================================
# 3. Session State 初始化
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


# ============================================================
# 4. 世界觀：五界隨機開局
# ============================================================

LOCATIONS = [
    {
        "loc": "凡間·青石鎮落魄流民所",
        "identity": "街頭乞討的孤苦孤兒",
        "bg": "父母雙亡，每日為下一頓飯發愁，在市井中看盡人情冷暖。"
    },
    {
        "loc": "仙界·凌霄外園雜役司",
        "identity": "九霄雲宮最底層雜役仙侍",
        "bg": "每天負責打掃仙園落花與倒夜香，是仙界最卑微的小薯。"
    },
    {
        "loc": "妖界·萬妖山脈外圍暗谷",
        "identity": "靈智未開就被放養的半妖奴隸",
        "bg": "混血身份在妖界備受排擠，只能在強大妖獸的爪下艱難求生。"
    },
    {
        "loc": "魔界·黑焰深淵礦區",
        "identity": "最低賤的魔鐵礦奴工",
        "bg": "每日承受著魔氣侵蝕與監工皮鞭，過著見不到明天的日子。"
    },
    {
        "loc": "靈界·散修坊市散亂破廟",
        "identity": "擺地攤維生的底層落魄散修",
        "bg": "靈根低下，功法殘缺，經常被強買強賣的修仙家族欺壓。"
    }
]


POTENTIAL_BLOODLINES = [
    "鳳凰涅槃血脈",
    "鴻蒙神魔同體印",
    "太古星辰帝君遺脈",
    "九幽妖皇真靈寄宿"
]


# ============================================================
# 5. 初始化遊戲
# ============================================================

def init_game(player_name):

    loc_info = random.choice(LOCATIONS)
    hidden_bloodline = random.choice(POTENTIAL_BLOODLINES)

    name = player_name.strip()

    if not name:
        name = "詩柔"

    comprehension = random.randint(8, 12)
    fortune = random.randint(8, 12)
    charm = random.randint(8, 12)

    st.session_state.game_state = {
        "player": {
            "name": name,

            "identity": (
                f"{loc_info['loc']}·"
                f"{loc_info['identity']}"
            ),

            # 這個資料只保存在本地遊戲狀態
            # 不會送給 AI
            "secret_bloodline": hidden_bloodline,

            "bloodline_awakened": False,

            "hp": "100/100",
            "mp": "30/30",
            "fullness": "90/100",

            "money": 5,

            "realm": "凡俗之軀 / 煉氣期一層",

            "location": loc_info["loc"],

            "status": "健康（平靜）",

            "comprehension": comprehension,
            "fortune": fortune,
            "charm": charm,

            "righteousness": 0,
            "evil_aura": 0,
            "fame": 0
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
                "desc": "填飽肚子的普通粗糧與清水。"
            }
        ],

        "npcs": {},

        "story_history": [
            (
                "【命運開啟】\n\n"
                f"你睜開眼睛，發現自己正身處在"
                f"**{loc_info['loc']}**。\n\n"
                f"你是【{name}】，身上僅剩下微薄的"
                f"**5文錢**，目前只是一個平凡無奇的"
                f"{loc_info['identity']}。\n\n"
                f"{loc_info['bg']}\n\n"
                "身無長物，萬事開頭難。"
                "茫茫三界，弱肉強食，"
                "屬於你的白手起家逆襲之路正式展開……"
            )
        ],

        "story_summary": (
            "白手起家開局，主角身懷5文錢，"
            "目前處於命運起點，等待發掘機緣。"
        )
    }

    st.session_state.current_options = [
        "1 冷眼旁觀周圍動靜，先找出對自己最有利的破局契機。（靜觀其變）",

        "2 默默觀察周遭環境，尋找被遺棄的有用物品或落腳之處。（低調求生）",

        "3 主動向附近人物打聽這裡的規矩與掌權者。（探聽情報）",

        "4 找一個偏僻角落，看看能否避開耳目尋找機緣。（暗中探索）",

        "5 查看當前狀態與身心狀況"
    ]

    st.session_state.game_started = True
    st.session_state.active_tab = "📖 主線劇情"
    st.session_state.last_usage = None
    st.session_state.last_error = ""


# ============================================================
# 6. AI 系統指令
# ============================================================

SYSTEM_INSTRUCTION = """
你是一個高品質古典修仙風格的三界跨界RPG遊戲主持人。

【語言規則】
必須全程使用繁體中文。
不要使用英文單字。
不要使用英文縮寫。
不要輸出Markdown。
最終只能輸出有效JSON。

【敘事視角】
全程使用第二人稱「你」。

【寫作風格】
半文半白的古典修仙小說筆法。
有畫面感、環境描寫、人物微表情、心理試探。
修仙世界冷酷現實，人心叵測。
NPC 有自己的性格、利益、目的和記憶。
NPC 不會因為玩家是主角就無條件幫助玩家。

【劇情長度】
每輪劇情約300至450字。
劇情必須承接上一輪。
不要突然跳過大量時間。
不要無故讓玩家獲得逆天能力。

【遊戲數值】
HP、MP、飽腹度、金錢、物品、境界必須合理變化。

沒有受傷，不要扣大量HP。
沒有使用法術，不要大量扣MP。
沒有購買東西，不要扣錢。
沒有取得物品，不要增加物品。
沒有修煉或特殊機緣，不要提升境界。

HP低於15時，必須描寫瀕死危機。
飽腹度低於15時，必須出現飢餓與負面影響。

【隱藏血脈】
玩家的真正血脈是絕對秘密。
在血脈覺醒之前，不可以直接說出血脈名稱。
只能透過異象、夢境、身體反應、古老氣息等方式暗示。
NPC也不可以無故知道玩家血脈。

【選項】
每輪必須提供5個選項。
前4個選項必須有不同策略。
第5個固定為查看狀態。

【JSON】
必須輸出：

{
  "story": "劇情",
  "story_summary_update": "80字內摘要",
  "options": [
    "1 選項（意圖或風險）",
    "2 選項（意圖或風險）",
    "3 選項（意圖或風險）",
    "4 選項（意圖或風險）",
    "5 查看當前狀態與身心狀況"
  ],
  "player_update": {
    "hp": "100/100",
    "mp": "30/30",
    "fullness": "85/100",
    "money": 5,
    "realm": "境界",
    "location": "位置",
    "status": "狀態",
    "comprehension": 10,
    "fortune": 10,
    "charm": 10,
    "righteousness": 0,
    "evil_aura": 0,
    "fame": 0,
    "bloodline_awakened": false
  },
  "inventory_update": [],
  "npc_updates": []
}
"""


# ============================================================
# 7. 數值工具
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


def make_value(number, maximum):

    number = max(0, min(number, maximum))

    return f"{number}/{maximum}"


def clamp(number, minimum, maximum):

    try:
        number = int(number)
    except Exception:
        number = minimum

    return max(minimum, min(number, maximum))


# ============================================================
# 8. 保護玩家數值
# ============================================================

def protect_player_update(old_player, ai_update):

    new_player = old_player.copy()

    # --------------------------------------------------------
    # HP
    # --------------------------------------------------------

    old_hp = get_number(
        old_player.get("hp", "100/100"),
        100
    )

    if "hp" in ai_update:

        new_hp = get_number(
            ai_update["hp"],
            old_hp
        )

        new_hp = clamp(
            new_hp,
            max(0, old_hp - 30),
            min(100, old_hp + 10)
        )

        new_player["hp"] = make_value(
            new_hp,
            100
        )

    # --------------------------------------------------------
    # MP
    # --------------------------------------------------------

    old_mp = get_number(
        old_player.get("mp", "30/30"),
        30
    )

    if "mp" in ai_update:

        new_mp = get_number(
            ai_update["mp"],
            old_mp
        )

        new_mp = clamp(
            new_mp,
            max(0, old_mp - 20),
            min(30, old_mp + 10)
        )

        new_player["mp"] = make_value(
            new_mp,
            30
        )

    # --------------------------------------------------------
    # 飽腹度
    # --------------------------------------------------------

    old_fullness = get_number(
        old_player.get("fullness", "90/100"),
        90
    )

    if "fullness" in ai_update:

        new_fullness = get_number(
            ai_update["fullness"],
            old_fullness
        )

        # 普通一回合最多下降5
        new_fullness = clamp(
            new_fullness,
            max(0, old_fullness - 5),
            min(100, old_fullness + 30)
        )

        new_player["fullness"] = make_value(
            new_fullness,
            100
        )

    # --------------------------------------------------------
    # 金錢
    # --------------------------------------------------------

    old_money = get_number(
        old_player.get("money", 0),
        0
    )

    if "money" in ai_update:

        new_money = get_number(
            ai_update["money"],
            old_money
        )

        # 每輪最多增加20 / 減少20
        new_money = clamp(
            new_money,
            max(0, old_money - 20),
            old_money + 20
        )

        new_player["money"] = new_money

    # --------------------------------------------------------
    # 文字狀態
    # --------------------------------------------------------

    text_fields = [
        "identity",
        "realm",
        "location",
        "status"
    ]

    for field in text_fields:

        if field in ai_update:

            value = ai_update[field]

            if isinstance(value, str):

                value = value.strip()

                if value:
                    new_player[field] = value

    # --------------------------------------------------------
    # 屬性
    # --------------------------------------------------------

    numeric_fields = [
        "comprehension",
        "fortune",
        "charm",
        "righteousness",
        "evil_aura",
        "fame"
    ]

    for field in numeric_fields:

        if field in ai_update:

            old_value = get_number(
                old_player.get(field, 0),
                0
            )

            new_value = get_number(
                ai_update[field],
                old_value
            )

            # 單輪最多變10
            new_value = clamp(
                new_value,
                old_value - 10,
                old_value + 10
            )

            new_player[field] = new_value

    # --------------------------------------------------------
    # 血脈覺醒
    # --------------------------------------------------------

    old_awakened = bool(
        old_player.get(
            "bloodline_awakened",
            False
        )
    )

    ai_awakened = bool(
        ai_update.get(
            "bloodline_awakened",
            False
        )
    )

    # 只能由 False -> True
    new_player["bloodline_awakened"] = (
        old_awakened or ai_awakened
    )

    return new_player


# ============================================================
# 9. 清理背包
# ============================================================

def clean_inventory(items):

    if not isinstance(items, list):
        return []

    cleaned = []

    for item in items:

        if not isinstance(item, dict):
            continue

        name = str(
            item.get("name", "")
        ).strip()

        if not name:
            continue

        count = get_number(
            item.get("count", 0),
            0
        )

        if count <= 0:
            continue

        desc = str(
            item.get(
                "desc",
                "普通物品。"
            )
        )

        cleaned.append({
            "name": name,
            "count": count,
            "desc": desc
        })

    return cleaned


# ============================================================
# 10. 清理NPC
# ============================================================

def clean_npcs(items):

    if not isinstance(items, list):
        return []

    cleaned = []

    for npc in items:

        if not isinstance(npc, dict):
            continue

        name = str(
            npc.get("name", "")
        ).strip()

        if not name:
            continue

        cleaned.append({
            "name": name,

            "identity": str(
                npc.get(
                    "identity",
                    "身份不明"
                )
            ),

            "affinity": get_number(
                npc.get(
                    "affinity",
                    0
                ),
                0
            ),

            "relationship": str(
                npc.get(
                    "relationship",
                    "陌生"
                )
            ),

            "key_memory": str(
                npc.get(
                    "key_memory",
                    ""
                )
            )
        })

    return cleaned


# ============================================================
# 11. 建立低 Token Prompt
# ============================================================

def build_game_prompt(player_action):

    game_state = st.session_state.game_state

    player = game_state["player"]

    # --------------------------------------------------------
    # 非常重要：
    # 只取最近2幕
    # --------------------------------------------------------

    recent_history = (
        game_state
        .get("story_history", [])[-2:]
    )

    # --------------------------------------------------------
    # 只取最近5個NPC
    # --------------------------------------------------------

    npc_dict = game_state.get(
        "npcs",
        {}
    )

    recent_npcs = dict(
        list(npc_dict.items())[-5:]
    )

    # --------------------------------------------------------
    # 不要把 secret_bloodline 傳給 AI
    # --------------------------------------------------------

    safe_player = {
        "name": player.get("name"),
        "identity": player.get("identity"),
        "bloodline_awakened": player.get(
            "bloodline_awakened",
            False
        ),
        "hp": player.get("hp"),
        "mp": player.get("mp"),
        "fullness": player.get("fullness"),
        "money": player.get("money"),
        "realm": player.get("realm"),
        "location": player.get("location"),
        "status": player.get("status"),
        "comprehension": player.get(
            "comprehension"
        ),
        "fortune": player.get(
            "fortune"
        ),
        "charm": player.get(
            "charm"
        ),
        "righteousness": player.get(
            "righteousness"
        ),
        "evil_aura": player.get(
            "evil_aura"
        ),
        "fame": player.get(
            "fame"
        )
    }

    prompt_data = {
        "劇情摘要": game_state.get(
            "story_summary",
            ""
        ),

        "最近劇情": recent_history,

        "玩家狀態": safe_player,

        "背包": game_state.get(
            "inventory",
            []
        ),

        "人物": recent_npcs,

        "玩家行動": player_action
    }

    prompt = (
        "請根據以下遊戲資料推進下一幕。\n"
        "只處理玩家這一次行動，不要重新開始故事。\n"
        "必須承接最近劇情。\n"
        "不要洩露玩家隱藏血脈。\n\n"
        + json.dumps(
            prompt_data,
            ensure_ascii=False,
            separators=(",", ":")
        )
    )

    return prompt


# ============================================================
# 12. 查看狀態
# ============================================================

def show_status():

    p = st.session_state.game_state["player"]

    st.info(
        f"""
❤️ HP：{p["hp"]}

💙 MP：{p["mp"]}

🍚 飽腹：{p["fullness"]}

💰 金錢：{p.get("money", 0)} 文

🏷️ 境界：{p["realm"]}

📍 位置：{p["location"]}

🧠 悟性：{p["comprehension"]}

🎲 福緣：{p["fortune"]}

✨ 魅力：{p["charm"]}

⚖️ 正氣：{p["righteousness"]}

🩸 煞氣：{p["evil_aura"]}

👑 威名：{p["fame"]}

🩺 狀態：{p["status"]}
"""
    )


# ============================================================
# 13. AI 回合
# ============================================================

def process_turn(player_action):

    game_state = st.session_state.game_state

    prompt = build_game_prompt(
        player_action
    )

    with st.status(
        "🔮 正在推演劇情……",
        expanded=True
    ) as status:

        try:

            st.write(
                f"正在使用 {MODEL_NAME}"
            )

            response = client.chat.completions.create(

                model=MODEL_NAME,

                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_INSTRUCTION
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],

                temperature=0.85,

                # 控制輸出量
                max_tokens=900,

                response_format={
                    "type": "json_object"
                }
            )

            # ------------------------------------------------
            # Token 使用量
            # ------------------------------------------------

            usage = getattr(
                response,
                "usage",
                None
            )

            if usage:

                prompt_tokens = getattr(
                    usage,
                    "prompt_tokens",
                    0
                )

                completion_tokens = getattr(
                    usage,
                    "completion_tokens",
                    0
                )

                total_tokens = getattr(
                    usage,
                    "total_tokens",
                    0
                )

                st.session_state.last_usage = {
                    "prompt": prompt_tokens,
                    "completion": completion_tokens,
                    "total": total_tokens
                }

                st.caption(
                    f"本回合：輸入 "
                    f"{prompt_tokens} tokens｜"
                    f"輸出 "
                    f"{completion_tokens} tokens｜"
                    f"合計 "
                    f"{total_tokens} tokens"
                )

            # ------------------------------------------------
            # 取得文字
            # ------------------------------------------------

            raw_text = (
                response
                .choices[0]
                .message
                .content
            )

            if not raw_text:
                raise ValueError(
                    "AI 沒有返回內容。"
                )

            # ------------------------------------------------
            # 清理 JSON
            # ------------------------------------------------

            clean_text = raw_text.strip()

            if clean_text.startswith(
                "```json"
            ):
                clean_text = (
                    clean_text[7:]
                )

            if clean_text.endswith(
                "```"
            ):
                clean_text = (
                    clean_text[:-3]
                )

            clean_text = clean_text.strip()

            # ------------------------------------------------
            # JSON Parse
            # ------------------------------------------------

            data = json.loads(
                clean_text
            )

            # ------------------------------------------------
            # Story
            # ------------------------------------------------

            story = data.get(
                "story",
                ""
            )

            if not story:
                story = (
                    "四周一片寂靜。"
                    "你站在原地，感覺到命運的齒輪"
                    "似乎正在暗中轉動。"
                )

            # ------------------------------------------------
            # Summary
            # ------------------------------------------------

            summary = data.get(
                "story_summary_update",
                game_state.get(
                    "story_summary",
                    ""
                )
            )

            summary = str(summary)[:500]

            # ------------------------------------------------
            # 玩家數值
            # ------------------------------------------------

            ai_player_update = data.get(
                "player_update",
                {}
            )

            if not isinstance(
                ai_player_update,
                dict
            ):
                ai_player_update = {}

            game_state["player"] = (
                protect_player_update(
                    game_state["player"],
                    ai_player_update
                )
            )

            # ------------------------------------------------
            # 背包
            # ------------------------------------------------

            if "inventory_update" in data:

                new_inventory = clean_inventory(
                    data["inventory_update"]
                )

                game_state["inventory"] = (
                    new_inventory
                )

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

                game_state["npcs"][
                    npc["name"]
                ] = npc

            # ------------------------------------------------
            # Summary
            # ------------------------------------------------

            game_state[
                "story_summary"
            ] = summary

            # ------------------------------------------------
            # History
            # ------------------------------------------------

            game_state[
                "story_history"
            ].append(
                f"👉 **你選擇了**：{player_action}"
            )

            game_state[
                "story_history"
            ].append(story)

            # ------------------------------------------------
            # 限制 History 大小
            #
            # 這只影響本地存檔大小。
            # AI 本身只會收到最近2幕。
            # ------------------------------------------------

            if len(
                game_state["story_history"]
            ) > 30:

                game_state[
                    "story_history"
                ] = (
                    game_state[
                        "story_history"
                    ][-30:]
                )

            # ------------------------------------------------
            # 選項
            # ------------------------------------------------

            options = data.get(
                "options",
                []
            )

            if (
                not isinstance(options, list)
                or len(options) < 5
            ):

                options = [
                    "1 冷靜觀察四周局勢，尋找突破口。（靜觀其變）",

                    "2 嘗試與附近人物交談，探聽情報。（試探風險）",

                    "3 找隱蔽地方調息，先穩住自身狀態。（保守求生）",

                    "4 搜查附近環境，尋找物品或機緣。（探索風險）",

                    "5 查看當前狀態與身心狀況"
                ]

            # 只保留前5個
            st.session_state.current_options = (
                options[:5]
            )

            status.update(
                label="✨ 劇情生成完畢！",
                state="complete",
                expanded=False
            )

            st.session_state.last_error = ""

        except json.JSONDecodeError:

            status.update(
                label="❌ JSON 解析失敗",
                state="error",
                expanded=True
            )

            st.session_state.last_error = (
                "AI 返回的資料不是有效 JSON。"
            )

            st.error(
                "⚠️ AI 返回格式有問題，"
                "請再按一次行動。"
            )

        except Exception as e:

            error_text = str(e)

            status.update(
                label="❌ AI 呼叫失敗",
                state="error",
                expanded=True
            )

            st.session_state.last_error = (
                error_text
            )

            if (
                "429" in error_text
                or "rate_limit" in error_text.lower()
            ):

                st.error(
                    "⚠️ Groq 暫時達到 Rate Limit。\n\n"
                    "通常是每分鐘 Token / Request 限制，"
                    "等一陣再試即可。"
                )

            else:

                st.error(
                    "❌ 發生錯誤：\n"
                    + error_text
                )


# ============================================================
# 14. 存檔
# ============================================================

def create_save():

    save_data = {
        "game_state":
            st.session_state.game_state,

        "current_options":
            st.session_state.current_options
    }

    return json.dumps(
        save_data,
        ensure_ascii=False
    )


# ============================================================
# 15. 讀檔
# ============================================================

def load_save(save_string):

    try:

        data = json.loads(
            save_string.strip()
        )

        game_state = data.get(
            "game_state"
        )

        options = data.get(
            "current_options",
            []
        )

        if not isinstance(
            game_state,
            dict
        ):
            return False

        if "player" not in game_state:
            return False

        if "inventory" not in game_state:
            game_state["inventory"] = []

        if "npcs" not in game_state:
            game_state["npcs"] = {}

        if "story_history" not in game_state:
            game_state["story_history"] = []

        if "story_summary" not in game_state:
            game_state["story_summary"] = ""

        st.session_state.game_state = (
            game_state
        )

        st.session_state.current_options = (
            options
        )

        st.session_state.game_started = True

        return True

    except Exception:
        return False


# ============================================================
# 16. 標題
# ============================================================

st.title(
    "🌸 三界奇譚：小薯逆襲記"
)


# ============================================================
# 17. 開始畫面
# ============================================================

if not st.session_state.game_started:

    st.subheader(
        "🎲 踏入命途｜白手起家隨機開局"
    )

    with st.form(
        "start_game_form"
    ):

        input_name = st.text_input(
            "請輸入你的名字：",
            value="詩柔"
        )

        start_button = (
            st.form_submit_button(
                "🎲 開啟逆襲人生 🚀",
                use_container_width=True
            )
        )

        if start_button:

            init_game(
                input_name
            )

            st.rerun()

    st.markdown("---")

    st.subheader(
        "💾 讀取舊存檔"
    )

    old_save = st.text_area(
        "請貼上你的存檔代碼：",
        height=180,
        key="start_load_code"
    )

    if st.button(
        "讀取存檔進度 📂",
        use_container_width=True
    ):

        if old_save.strip():

            if load_save(old_save):

                st.success(
                    "讀取存檔成功！"
                )

                st.rerun()

            else:

                st.error(
                    "❌ 存檔格式無效。"
                )


# ============================================================
# 18. 遊戲畫面
# ============================================================

else:

    game_state = (
        st.session_state.game_state
    )

    player = game_state["player"]

    # ========================================================
    # Sidebar
    # ========================================================

    with st.sidebar:

        st.header(
            "📌 逆襲導航與狀態"
        )

        st.write(
            f"👤 **{player['name']}**"
        )

        st.write(
            f"🏷️ 境界：{player['realm']}"
        )

        st.write(
            f"📍 位置：{player['location']}"
        )

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
            f"{player.get('money', 0)} 文"
        )

        # ----------------------------------------------------
        # 詳細屬性
        # ----------------------------------------------------

        with st.expander(
            "📊 詳細屬性數據",
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
                    "🔒 身世之謎："
                    "尚未覺醒"
                )

        # ----------------------------------------------------
        # 最近一次 Token
        # ----------------------------------------------------

        if st.session_state.last_usage:

            with st.expander(
                "📊 本次 AI 用量",
                expanded=False
            ):

                usage = (
                    st.session_state.last_usage
                )

                st.write(
                    "輸入："
                    f"{usage['prompt']} tokens"
                )

                st.write(
                    "輸出："
                    f"{usage['completion']} tokens"
                )

                st.write(
                    "合計："
                    f"{usage['total']} tokens"
                )

        # ----------------------------------------------------
        # 導航
        # ----------------------------------------------------

        st.markdown("---")

        st.subheader(
            "🗂️ 畫面檢視"
        )

        if st.button(
            "📖 主線劇情與冒險",
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
            "👥 三界人物關係",
            use_container_width=True
        ):

            st.session_state.active_tab = (
                "👥 三界人物關係"
            )

            st.rerun()

        if st.button(
            "💾 存檔與讀檔",
            use_container_width=True
        ):

            st.session_state.active_tab = (
                "💾 存檔與讀檔"
            )

            st.rerun()

        # ----------------------------------------------------
        # 重開
        # ----------------------------------------------------

        st.markdown("---")

        if st.button(
            "🎲 重開新局",
            use_container_width=True
        ):

            st.session_state.game_started = False

            st.session_state.active_tab = (
                "📖 主線劇情"
            )

            st.session_state.current_options = []

            st.session_state.game_state = {}

            st.rerun()

    # ========================================================
    # 中央畫面
    # ========================================================

    current_view = (
        st.session_state.get(
            "active_tab",
            "📖 主線劇情"
        )
    )

    # ========================================================
    # 主線
    # ========================================================

    if current_view == "📖 主線劇情":

        st.subheader(
            "📖 主線劇情與冒險"
        )

        # ----------------------------------------------------
        # 顯示劇情
        # ----------------------------------------------------

        for text in game_state[
            "story_history"
        ]:

            if text.startswith(
                "👉"
            ):

                st.info(text)

            else:

                st.write(text)

        st.markdown("---")

        st.write(
            "✨ **請選擇你的行動：**"
        )

        # ----------------------------------------------------
        # 選項
        # ----------------------------------------------------

        history_length = len(
            game_state[
                "story_history"
            ]
        )

        for idx, option in enumerate(
            st.session_state.current_options
        ):

            button_key = (
                f"option_"
                f"{history_length}_"
                f"{idx}"
            )

            if st.button(
                option,
                key=button_key,
                use_container_width=True
            ):

                # 第5項查看狀態
                if option.startswith("5"):

                    show_status()

                else:

                    process_turn(
                        option
                    )

                    st.rerun()

        # ----------------------------------------------------
        # 自由輸入
        # ----------------------------------------------------

        st.markdown("---")

        st.write(
            "💬 **自由意念**"
        )

        custom_action = st.text_input(
            "你想做什麼？",
            key="custom_action",
            placeholder=(
                "例如：我先不靠近那個老人，"
                "而是躲在牆後觀察他的行動。"
            )
        )

        if st.button(
            "發送自訂行動 🚀",
            use_container_width=True
        ):

            if custom_action.strip():

                process_turn(
                    custom_action.strip()
                )

                st.session_state.custom_action = ""

                st.rerun()

            else:

                st.warning(
                    "請先輸入你想做的事情。"
                )

    # ========================================================
    # 背包
    # ========================================================

    elif current_view == "🎒 我的背包":

        st.subheader(
            "🎒 我的背包物品欄"
        )

        inventory = game_state[
            "inventory"
        ]

        if not inventory:

            st.info(
                "背包空空如也。"
            )

        else:

            for item in inventory:

                st.success(
                    f"**【{item['name']}】 "
                    f"x {item['count']}**\n\n"
                    f"說明：{item['desc']}"
                )

    # ========================================================
    # NPC
    # ========================================================

    elif current_view == "👥 三界人物關係":

        st.subheader(
            "👥 三界人物誌與好感度"
        )

        npcs = game_state[
            "npcs"
        ]

        if not npcs:

            st.info(
                "目前尚未結識任何三界角色。"
            )

        else:

            for name, npc in npcs.items():

                affinity = npc.get(
                    "affinity",
                    0
                )

                with st.expander(
                    f"🌸 {name}"
                    f"（好感/敬意："
                    f"{affinity}）",
                    expanded=True
                ):

                    st.write(
                        "**身份：** "
                        + npc.get(
                            "identity",
                            "未知"
                        )
                    )

                    st.write(
                        "**關係：** "
                        + npc.get(
                            "relationship",
                            "陌生"
                        )
                    )

                    st.write(
                        "**印象關鍵：** "
                        + npc.get(
                            "key_memory",
                            ""
                        )
                    )

    # ========================================================
    # 存檔
    # ========================================================

    elif current_view == "💾 存檔與讀檔":

        st.subheader(
            "💾 遊戲存檔與讀檔管理"
        )

        if st.button(
            "⬅️ 返回主線劇情",
            use_container_width=True
        ):

            st.session_state.active_tab = (
                "📖 主線劇情"
            )

            st.rerun()

        st.markdown("---")

        save_string = create_save()

        st.text_area(
            "📋 當前存檔代碼（全選複製保存）：",
            value=save_string,
            height=220,
            key="save_box"
        )

        st.markdown("---")

        load_string = st.text_area(
            "📥 貼上存檔代碼：",
            height=220,
            key="load_box"
        )

        if st.button(
            "確認載入存檔 🔄",
            use_container_width=True
        ):

            if not load_string.strip():

                st.warning(
                    "請先貼上存檔代碼。"
                )

            else:

                if load_save(
                    load_string
                ):

                    st.success(
                        "✅ 存檔載入成功！"
                    )

                    st.rerun()

                else:

                    st.error(
                        "❌ 存檔格式錯誤，"
                        "請確認整段代碼已完整複製。"
                    )
