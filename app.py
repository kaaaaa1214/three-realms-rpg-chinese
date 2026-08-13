import json
import random
import re
import hashlib
import streamlit as st
from openai import OpenAI


# =========================================================
# 三界奇譚 V3.1
# Nemotron 免費版
# =========================================================

st.set_page_config(
    page_title="三界奇譚：小薯逆襲記",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================================================
# API 設定
# =========================================================

MODEL_NAME = "nvidia/nemotron-3-ultra-550b-a55b:free"

api_key = st.secrets.get("OPENROUTER_API_KEY", "")

if not api_key:
    st.error("⚠️ 找不到 OPENROUTER_API_KEY")
    st.info(
        "請到 Streamlit → Settings → Secrets 加入：\n\n"
        'OPENROUTER_API_KEY = "你的 OpenRouter API Key"'
    )
    st.stop()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key
)


# =========================================================
# 世界資料
# =========================================================

LOCATIONS = [
    {
        "realm": "凡間",
        "loc": "青石鎮落魄流民所",
        "identity": "街頭乞討的孤苦孤兒",
        "bg": "父母雙亡，每日為下一頓飯發愁，在市井之中看盡人情冷暖。"
    },
    {
        "realm": "仙界",
        "loc": "凌霄外園雜役司",
        "identity": "九霄雲宮最底層雜役仙侍",
        "bg": "每日負責打掃仙園落花與清理雜役區，是仙界最卑微的存在。"
    },
    {
        "realm": "妖界",
        "loc": "萬妖山脈外圍暗谷",
        "identity": "被放養的半妖奴隸",
        "bg": "混血身份備受排擠，只能在強大妖獸與妖族勢力之間艱難求生。"
    },
    {
        "realm": "魔界",
        "loc": "黑焰深淵礦區",
        "identity": "最低賤的魔鐵礦奴工",
        "bg": "每日承受魔氣侵蝕與監工壓迫，過著看不見明日的生活。"
    },
    {
        "realm": "靈界",
        "loc": "散修坊市破廟",
        "identity": "擺地攤維生的落魄散修",
        "bg": "靈根低下、功法殘缺，經常受到修仙家族與坊市強者欺壓。"
    }
]


POTENTIAL_BLOODLINES = [
    "鳳凰涅槃血脈",
    "鴻蒙神魔同體印",
    "太古星辰帝君遺脈",
    "九幽妖皇真靈",
    "混沌青蓮道體"
]


STARTING_ITEMS = [
    {
        "name": "粗布麻衣",
        "count": 1,
        "desc": "極為普通的日常衣物，已經磨損。"
    },
    {
        "name": "乾糧",
        "count": 2,
        "desc": "普通粗糧，可以稍微恢復飽腹度。"
    },
    {
        "name": "清水",
        "count": 1,
        "desc": "一小壺普通清水。"
    }
]


# =========================================================
# Streamlit Session 初始化
# =========================================================

def ensure_session():

    if "game_started" not in st.session_state:
        st.session_state.game_started = False

    if "processing" not in st.session_state:
        st.session_state.processing = False

    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "📖 主線劇情"

    if "last_action_hash" not in st.session_state:
        st.session_state.last_action_hash = ""

    if "last_story_hash" not in st.session_state:
        st.session_state.last_story_hash = ""

    if "turn" not in st.session_state:
        st.session_state.turn = 0

    if "current_options" not in st.session_state:
        st.session_state.current_options = []


ensure_session()


# =========================================================
# 工具函式
# =========================================================

def safe_int(value, default=0):
    """
    將各種奇怪數值安全轉成整數。
    """

    try:
        if isinstance(value, str):
            match = re.search(r"-?\d+", value)
            if match:
                return int(match.group())
        return int(value)
    except Exception:
        return default


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def story_hash(text):
    """
    用來防止 AI 重複輸出完全相同劇情。
    """

    normalized = re.sub(r"\s+", "", text)
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


def clean_story(text):
    """
    清理模型輸出。
    """

    if not text:
        return ""

    text = text.strip()

    # 移除 Markdown code fence
    text = text.replace("```json", "")
    text = text.replace("```", "")

    # 移除一些模型常見的奇怪前綴
    prefixes = [
        "劇情：",
        "故事：",
        "回合劇情：",
        "【劇情】"
    ]

    for prefix in prefixes:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()

    return text


def remove_accidental_english(text):
    """
    防止故事中混入 investigate / None / English 等。
    不會粗暴刪除所有英文字母，而是針對常見錯誤詞。
    """

    replacements = {
        "None": "",
        "none": "",
        "investigate": "調查",
        "Investigate": "調查",
        "investigation": "調查",
        "Investigation": "調查",
        "NPC": "人物",
        "HP": "生命值",
        "MP": "靈力",
        "AI": "天機",
        "player": "你",
        "Player": "你"
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text.strip()


def item_exists(inventory, name):
    for item in inventory:
        if item.get("name") == name:
            return True
    return False


def add_item(inventory, name, count=1, desc=""):
    """
    加入背包。
    """

    if count <= 0:
        return

    for item in inventory:
        if item.get("name") == name:
            item["count"] = safe_int(item.get("count", 0)) + count
            return

    inventory.append({
        "name": name,
        "count": count,
        "desc": desc
    })


def remove_item(inventory, name, count=1):
    """
    移除背包物品。
    """

    for item in inventory:
        if item.get("name") == name:
            current = safe_int(item.get("count", 0))

            if current <= count:
                inventory.remove(item)
            else:
                item["count"] = current - count

            return True

    return False


def find_item(inventory, name):
    for item in inventory:
        if item.get("name") == name:
            return item

    return None


# =========================================================
# 初始化遊戲
# =========================================================

def init_game(player_name):

    location = random.choice(LOCATIONS)
    bloodline = random.choice(POTENTIAL_BLOODLINES)

    name = player_name.strip()

    if not name:
        name = "詩柔"

    comprehension = random.randint(8, 12)
    fortune = random.randint(8, 12)
    charm = random.randint(8, 12)

    game_state = {

        "turn": 0,

        "player": {
            "name": name,

            "identity": (
                f"{location['loc']}・"
                f"{location['identity']}"
            ),

            "secret_bloodline": bloodline,

            "bloodline_awakened": False,

            "hp": 100,
            "max_hp": 100,

            "mp": 30,
            "max_mp": 30,

            "fullness": 90,

            "money": 5,

            "realm": "凡俗之軀・煉氣期一層",

            "location": location["loc"],

            "status": "健康",

            "comprehension": comprehension,
            "fortune": fortune,
            "charm": charm,

            "righteousness": 0,
            "evil_aura": 0,
            "fame": 0
        },

        "world": {
            "realm": location["realm"],
            "background": location["bg"]
        },

        "inventory": [item.copy() for item in STARTING_ITEMS],

        "npcs": {},

        "story_summary": (
            f"你出生於{location['loc']}，"
            f"目前只是{location['identity']}。"
            f"身上只有五文錢，命途尚未真正開始。"
        ),

        "story_history": [],

        "used_actions": [],

        "flags": {
            "first_clue_found": False,
            "danger_detected": False,
            "bloodline_hint": False,
            "special_encounter": False
        }
    }

    opening_story = (
        f"你睜開眼睛。\n\n"
        f"晨霧尚未散去，冰冷的空氣貼著你的臉頰。"
        f"你躺在{location['loc']}一處不起眼的角落，"
        f"身上的粗布麻衣沾滿塵土。\n\n"
        f"你是【{name}】。\n\n"
        f"如今的你，只是{location['identity']}。\n"
        f"{location['bg']}\n\n"
        f"摸遍全身，你只找到五文錢。\n\n"
        f"五文錢，在這個弱肉強食的世界裡，"
        f"甚至不足以換來一頓像樣的飯。\n\n"
        f"遠處鐘聲悠悠傳來。\n"
        f"人群開始活動，新的日子又一次開始。\n\n"
        f"然而你不知道的是——"
        f"就在你醒來之前，命運已經悄然替你推開了一扇門。\n\n"
        f"只是那扇門後面究竟是機緣，還是死路，"
        f"尚無人知曉。"
    )

    game_state["story_history"].append({
        "type": "story",
        "turn": 0,
        "text": opening_story
    })

    st.session_state.game_state = game_state
    st.session_state.turn = 0

    st.session_state.current_options = [
        "1 仔細觀察四周，先弄清楚自己身處何地。（穩妥探索，可能發現線索）",
        "2 檢查附近是否有可以利用的物品。（尋找資源，但可能暴露自己）",
        "3 找人打聽附近的規矩與消息。（獲取情報，但可能被人注意）",
        "4 暫時找個隱蔽地方休息，觀察局勢變化。（降低風險，但可能錯過機緣）",
        "5 查看當前狀態。（不消耗回合）"
    ]

    st.session_state.game_started = True
    st.session_state.processing = False
    st.session_state.last_action_hash = ""
    st.session_state.last_story_hash = ""


# =========================================================
# 建立給 Nemotron 的劇情提示
# =========================================================

SYSTEM_PROMPT = """
你是一名專業的古典修仙 RPG 遊戲主持人。

你只負責：
一、敘事。
二、NPC 行為。
三、環境描寫。
四、根據玩家行動產生合理事件。
五、提供下一回合選項。

你不能直接修改玩家數值。

【語言】
必須使用自然、流暢、道地的繁體中文。
不可使用英文。
不可使用 None。
不可使用 investigate。
不可使用遊戲程式碼。
不可提及模型、人工智慧、提示詞、系統或 API。

【敘事】
使用第二人稱「你」。
採用半文半白的修仙小說筆法。
每次劇情約 280 至 420 字。
劇情必須真正推進事件。

絕對禁止：
「你沒有急著再次行動」
「命運的齒輪開始轉動」
「一切仍然未知」
「你不知道接下來會發生什麼」
等沒有實質內容的空泛句子反覆出現。

如果上一回合玩家已經調查某件物品，
下一回合必須出現新的資訊、人物、危險或結果。
不能重新描述同一件事情。

NPC 必須有自己的動機。
NPC 不可以無故知道玩家不知道的秘密。

【隱藏血脈】
玩家的隱藏血脈絕對不能直接說出。
只能在極少數特殊情況透過異象、身體反應或古老物件產生模糊暗示。

【世界】
修仙世界不是童話。
弱者可能被欺壓。
善人可能有私心。
惡人也可能遵守自己的規矩。
任何機緣都可能伴隨代價。

【選項】
每次提供四個真正不同的選項。
另外固定提供第五個：
「5 查看當前狀態。（不消耗回合）」

四個選項必須包含不同策略，例如：
探索、交涉、試探、冒險、撤退、利益交換、欺騙、觀察。

不要讓四個選項只是換句話說。

【重要】
你只需要輸出劇情文字。

不要輸出 JSON。
不要輸出選項。
不要輸出數值。
"""


def build_story_prompt(action):

    game = st.session_state.game_state
    player = game["player"]

    history = game["story_history"]

    recent = history[-5:]

    recent_text = ""

    for entry in recent:
        if isinstance(entry, dict):
            recent_text += (
                f"\n【第{entry.get('turn', '?')}回合】\n"
                f"{entry.get('text', '')}\n"
            )

    npc_text = json.dumps(
        game["npcs"],
        ensure_ascii=False
    )

    inventory_text = json.dumps(
        game["inventory"],
        ensure_ascii=False
    )

    flags_text = json.dumps(
        game["flags"],
        ensure_ascii=False
    )

    prompt = f"""
【目前回合】
第 {game['turn'] + 1} 回合

【玩家】
姓名：{player['name']}
身份：{player['identity']}
境界：{player['realm']}
位置：{player['location']}
狀態：{player['status']}

【最近劇情】
{recent_text}

【劇情摘要】
{game['story_summary']}

【背包】
{inventory_text}

【已知人物】
{npc_text}

【世界旗標】
{flags_text}

【玩家這一次的行動】
{action}

現在請直接承接上一回合。

非常重要：

如果玩家剛剛已經做過某件事情，
這一回合不能再次把同一件事情重新描寫一遍。

必須讓事件向前推進。

例如：
如果玩家拾起紙片，
下一回合應該揭示紙片內容、人物反應、危險或新的線索，
而不是再次描寫「紙片在地上」。

如果玩家與 NPC 對話，
下一回合必須讓 NPC 作出新的回應，
而不是重新介紹 NPC。

請只輸出這一回合的完整劇情。
"""
    return prompt


# =========================================================
# 生成劇情
# =========================================================

def call_nemotron(action):

    prompt = build_story_prompt(action)

    try:

        response = client.chat.completions.create(
            model=MODEL_NAME,

            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            temperature=0.85,

            top_p=0.9,

            max_tokens=900,

            # 關閉額外推理展示，盡量減少不必要輸出
            reasoning={
                "effort": "low",
                "exclude": True
            }
        )

        content = response.choices[0].message.content

        if not content:
            raise ValueError("模型沒有返回內容。")

        content = clean_story(content)
        content = remove_accidental_english(content)

        return content

    except Exception as e:
        raise RuntimeError(str(e))


# =========================================================
# 生成下一輪選項
# =========================================================

def generate_options(story):

    """
    選項不再由模型生成。
    由 Python 根據劇情關鍵字提供策略，
    避免模型 JSON 錯誤及大量 token 消耗。
    """

    text = story

    options = []

    if any(word in text for word in [
        "紙片",
        "紙角",
        "信",
        "書",
        "字跡",
        "線索"
    ]):
        options.append(
            "1 仔細查看剛得到的線索，尋找隱藏訊息。（獲取情報，但可能暴露自己）"
        )

        options.append(
            "2 將線索藏好，裝作什麼都沒有發現。（降低風險，但可能錯過追查機會）"
        )

    elif any(word in text for word in [
        "少年",
        "女子",
        "男子",
        "老人",
        "修士",
        "監工",
        "掌櫃"
    ]):
        options.append(
            "1 主動與對方交談，試探他的身份。（獲取情報，但可能暴露意圖）"
        )

        options.append(
            "2 不說話，只觀察對方的細微反應。（穩妥試探，但可能失去先機）"
        )

    else:
        options.append(
            "1 仔細觀察周圍環境，尋找異常之處。（穩妥探索，可能發現線索）"
        )

        options.append(
            "2 主動尋找附近人物打聽消息。（獲取情報，但可能引起注意）"
        )

    options.append(
        "3 暗中尋找可以利用的資源或機會。（可能獲利，也可能遇到危險）"
    )

    options.append(
        "4 暫時抽身離開此地，換一個安全位置觀察。（降低風險，但可能錯過機緣）"
    )

    options.append(
        "5 查看當前狀態。（不消耗回合）"
    )

    return options


# =========================================================
# Python 遊戲數值結算
# =========================================================

def apply_turn_cost(action):

    game = st.session_state.game_state
    player = game["player"]

    # 每次真正行動
    game["turn"] += 1

    # 飽腹自然下降
    player["fullness"] = clamp(
        safe_int(player["fullness"], 90) - 5,
        0,
        100
    )

    # 飢餓懲罰
    if player["fullness"] < 15:

        player["hp"] = clamp(
            safe_int(player["hp"], 100) - 5,
            0,
            player["max_hp"]
        )

        player["status"] = "極度飢餓"

    elif player["fullness"] < 30:

        player["status"] = "飢餓"

    else:

        player["status"] = "健康"


# =========================================================
# 根據玩家行動處理簡單遊戲邏輯
# =========================================================

def process_action_effects(action, story):

    game = st.session_state.game_state
    player = game["player"]
    inventory = game["inventory"]

    action_text = action.lower()

    # -----------------------------------------------------
    # 吃乾糧
    # -----------------------------------------------------

    if any(word in action for word in [
        "吃乾糧",
        "吃東西",
        "食物",
        "吃飯"
    ]):

        item = find_item(inventory, "乾糧")

        if item and item["count"] > 0:

            remove_item(
                inventory,
                "乾糧",
                1
            )

            player["fullness"] = clamp(
                player["fullness"] + 25,
                0,
                100
            )

            player["status"] = "吃飽了一些"


    # -----------------------------------------------------
    # 喝水
    # -----------------------------------------------------

    if "喝水" in action:

        item = find_item(inventory, "清水")

        if item and item["count"] > 0:

            remove_item(
                inventory,
                "清水",
                1
            )

            player["status"] = "精神稍微恢復"


    # -----------------------------------------------------
    # 探索
    # -----------------------------------------------------

    if any(word in action for word in [
        "探索",
        "尋找",
        "查看",
        "觀察"
    ]):

        player["fortune"] = clamp(
            player["fortune"],
            0,
            100
        )


    # -----------------------------------------------------
    # 發現線索
    # -----------------------------------------------------

    if any(word in story for word in [
        "紙片",
        "紙角",
        "線索",
        "密信"
    ]):

        game["flags"]["first_clue_found"] = True


    # -----------------------------------------------------
    # 危險
    # -----------------------------------------------------

    if any(word in story for word in [
        "受傷",
        "刀光",
        "襲擊",
        "鮮血",
        "重擊",
        "倒下"
    ]):

        # 小幅傷害
        player["hp"] = clamp(
            player["hp"] - random.randint(2, 7),
            0,
            player["max_hp"]
        )


    # -----------------------------------------------------
    # 特殊機緣
    # -----------------------------------------------------

    if any(word in story for word in [
        "靈氣",
        "古老符文",
        "奇異光芒",
        "神秘氣息"
    ]):

        game["flags"]["bloodline_hint"] = True


    # -----------------------------------------------------
    # 瀕死
    # -----------------------------------------------------

    if player["hp"] <= 0:

        player["hp"] = 0
        player["status"] = "瀕死"

    elif player["hp"] < 15:

        player["status"] = "重傷瀕死"

    elif player["fullness"] < 15:

        player["status"] = "極度飢餓"


# =========================================================
# NPC 自動記錄
# =========================================================

def detect_npc(story):

    """
    非常簡單的 NPC 記錄。
    不要求模型輸出 JSON，因此更穩定。
    """

    game = st.session_state.game_state

    possible_titles = [
        "少年",
        "少女",
        "老人",
        "老者",
        "男子",
        "女子",
        "監工",
        "掌櫃",
        "師兄",
        "師姐",
        "修士",
        "道人"
    ]

    found = []

    for title in possible_titles:

        if title in story:
            found.append(title)

    for title in found:

        if title not in game["npcs"]:

            game["npcs"][title] = {
                "name": title,
                "identity": "身份尚未完全查明",
                "affinity": 0,
                "relationship": "陌生",
                "key_memory": "初次相遇"
            }


# =========================================================
# 防止重複劇情
# =========================================================

def is_duplicate_story(story):

    current_hash = story_hash(story)

    if current_hash == st.session_state.last_story_hash:
        return True

    # 同時檢查最近兩段
    game = st.session_state.game_state

    recent_stories = []

    for item in game["story_history"][-4:]:

        if isinstance(item, dict):
            recent_stories.append(
                story_hash(item.get("text", ""))
            )

    if current_hash in recent_stories:
        return True

    return False


# =========================================================
# 如果重複，要求模型重新生成
# =========================================================

def regenerate_story(action, previous_story):

    prompt = build_story_prompt(action)

    prompt += f"""

【重要修正】

你剛才生成的劇情與之前內容過於相似。

上一段錯誤劇情：

{previous_story}

請完全避開上一段的描述。

必須產生新的事件推進：
- 新的資訊
- 新的人物反應
- 新的危險
- 新的選擇
- 或新的環境變化

不可再次描寫相同場景。

只輸出新的劇情。
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,

        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=0.95,
        top_p=0.9,
        max_tokens=900,

        reasoning={
            "effort": "low",
            "exclude": True
        }
    )

    content = response.choices[0].message.content

    content = clean_story(content)
    content = remove_accidental_english(content)

    return content


# =========================================================
# 真正處理回合
# =========================================================

def process_turn(action):

    if st.session_state.processing:
        return

    action = action.strip()

    if not action:
        return

    # -----------------------------------------------------
    # 防止同一個按鈕重複提交
    # -----------------------------------------------------

    action_hash = hashlib.md5(
        action.encode("utf-8")
    ).hexdigest()

    if action_hash == st.session_state.last_action_hash:
        st.warning("這個行動剛剛已經執行過了。")
        return

    st.session_state.processing = True

    try:

        game = st.session_state.game_state

        # -------------------------------------------------
        # 查看狀態不消耗回合
        # -------------------------------------------------

        if action.startswith("5 ") or "查看當前狀態" in action:

            st.session_state.active_tab = "📊 狀態"

            st.session_state.processing = False

            return


        # -------------------------------------------------
        # 記錄玩家行動
        # -------------------------------------------------

        current_turn = game["turn"] + 1

        game["story_history"].append({
            "type": "action",
            "turn": current_turn,
            "text": action
        })


        # -------------------------------------------------
        # Python 控制回合及飽腹
        # -------------------------------------------------

        apply_turn_cost(action)


        # -------------------------------------------------
        # 呼叫 Nemotron
        # -------------------------------------------------

        with st.spinner("🔮 天機推演中……"):

            story = call_nemotron(action)


        # -------------------------------------------------
        # 空內容
        # -------------------------------------------------

        if not story:

            raise RuntimeError(
                "模型沒有返回有效劇情。"
            )


        # -------------------------------------------------
        # 防止重複劇情
        # -------------------------------------------------

        if is_duplicate_story(story):

            with st.spinner("🔮 劇情出現重複，正在重新推演……"):

                story = regenerate_story(
                    action,
                    story
                )


        # -------------------------------------------------
        # 再檢查一次
        # -------------------------------------------------

        if not story:

            raise RuntimeError(
                "重新生成後仍然沒有有效劇情。"
            )


        # -------------------------------------------------
        # Python 結算
        # -------------------------------------------------

        process_action_effects(
            action,
            story
        )


        # -------------------------------------------------
        # NPC
        # -------------------------------------------------

        detect_npc(story)


        # -------------------------------------------------
        # 更新摘要
        # -------------------------------------------------

        summary = story

        if len(summary) > 220:
            summary = summary[:220] + "……"

        game["story_summary"] = summary


        # -------------------------------------------------
        # 儲存劇情
        # -------------------------------------------------

        game["story_history"].append({
            "type": "story",
            "turn": game["turn"],
            "text": story
        })


        # -------------------------------------------------
        # 生成下一輪選項
        # -------------------------------------------------

        st.session_state.current_options = generate_options(
            story
        )


        # -------------------------------------------------
        # 更新防重複記錄
        # -------------------------------------------------

        st.session_state.last_action_hash = action_hash
        st.session_state.last_story_hash = story_hash(story)


        # -------------------------------------------------
        # 完成
        # -------------------------------------------------

        st.session_state.processing = False

    except Exception as e:

        st.session_state.processing = False

        st.error(
            "❌ 劇情生成失敗\n\n"
            f"{str(e)}"
        )


# =========================================================
# 存檔
# =========================================================

def create_save():

    data = {
        "version": "V3.1",
        "game_state": st.session_state.game_state,
        "current_options": st.session_state.current_options
    }

    return json.dumps(
        data,
        ensure_ascii=False
    )


def load_save(save_text):

    try:

        data = json.loads(save_text)

        game_state = data.get(
            "game_state",
            {}
        )

        if not game_state:
            raise ValueError("存檔內容為空。")

        st.session_state.game_state = game_state

        st.session_state.current_options = data.get(
            "current_options",
            []
        )

        st.session_state.game_started = True

        st.session_state.processing = False

        st.session_state.last_action_hash = ""

        st.session_state.last_story_hash = ""

        st.session_state.turn = game_state.get(
            "turn",
            0
        )

        return True

    except Exception as e:

        st.error(
            f"❌ 存檔讀取失敗：{str(e)}"
        )

        return False


# =========================================================
# 主頁面
# =========================================================

st.title("🌸 三界奇譚：小薯逆襲記")

st.caption(
    "V3.1 ・ Nemotron 免費版 ・ Python 遊戲邏輯"
)


# =========================================================
# 尚未開始
# =========================================================

if not st.session_state.game_started:

    st.subheader("🎲 踏入命途")

    st.write(
        "五界隨機開局，從最底層開始。"
        "沒有系統送裝備，沒有無敵主角，"
        "每一次選擇都可能改變你的命運。"
    )

    with st.form("start_game"):

        name = st.text_input(
            "請輸入你的名字",
            value="詩柔"
        )

        start = st.form_submit_button(
            "🎲 開啟逆襲人生",
            use_container_width=True
        )

        if start:

            init_game(name)

            st.rerun()


    st.markdown("---")

    st.subheader("💾 讀取舊存檔")

    load_code = st.text_area(
        "貼上你的存檔代碼",
        height=180
    )

    if st.button(
        "📂 讀取存檔",
        use_container_width=True
    ):

        if load_code.strip():

            if load_save(load_code.strip()):

                st.success("讀取成功！")

                st.rerun()

        else:

            st.warning(
                "請先貼上存檔代碼。"
            )


    st.stop()


# =========================================================
# 已開始遊戲
# =========================================================

game = st.session_state.game_state
player = game["player"]


# =========================================================
# 側邊欄
# =========================================================

with st.sidebar:

    st.header("📌 逆襲導航")

    st.write(
        f"👤 **{player['name']}**"
    )

    st.write(
        f"🏷️ **{player['realm']}**"
    )

    st.write(
        f"📍 **{player['location']}**"
    )

    st.markdown("---")


    # -----------------------------------------------------
    # 基本狀態
    # -----------------------------------------------------

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


    st.write(
        f"📖 **第 {game['turn']} 回合**"
    )

    st.write(
        f"🩸 **狀態：{player['status']}**"
    )


    # -----------------------------------------------------
    # 導航
    # -----------------------------------------------------

    st.markdown("---")

    st.subheader("🗂️ 遊戲畫面")

    if st.button(
        "📖 主線劇情",
        use_container_width=True
    ):

        st.session_state.active_tab = "📖 主線劇情"

        st.rerun()


    if st.button(
        "🎒 我的背包",
        use_container_width=True
    ):

        st.session_state.active_tab = "🎒 我的背包"

        st.rerun()


    if st.button(
        "👥 人物關係",
        use_container_width=True
    ):

        st.session_state.active_tab = "👥 人物關係"

        st.rerun()


    if st.button(
        "📊 狀態",
        use_container_width=True
    ):

        st.session_state.active_tab = "📊 狀態"

        st.rerun()


    if st.button(
        "💾 存檔",
        use_container_width=True
    ):

        st.session_state.active_tab = "💾 存檔"

        st.rerun()


    st.markdown("---")


    if st.button(
        "🎲 重開新局",
        use_container_width=True
    ):

        st.session_state.game_started = False
        st.session_state.processing = False
        st.session_state.active_tab = "📖 主線劇情"

        st.rerun()


# =========================================================
# 目前畫面
# =========================================================

current_view = st.session_state.active_tab


# =========================================================
# 主線
# =========================================================

if current_view == "📖 主線劇情":

    st.subheader(
        f"📖 主線劇情・第 {game['turn']} 回合"
    )


    # -----------------------------------------------------
    # 顯示劇情
    # -----------------------------------------------------

    for entry in game["story_history"]:

        if not isinstance(entry, dict):
            continue

        entry_type = entry.get(
            "type",
            "story"
        )

        turn = entry.get(
            "turn",
            0
        )

        text = entry.get(
            "text",
            ""
        )


        if entry_type == "action":

            st.info(
                f"👉 **第 {turn} 回合・你選擇：**\n\n"
                f"{text}"
            )

        else:

            st.write(
                f"### 第 {turn} 回合"
            )

            st.write(text)


    st.markdown("---")


    # -----------------------------------------------------
    # 選項
    # -----------------------------------------------------

    st.subheader(
        "✨ 你準備怎麼做？"
    )


    options = st.session_state.current_options

    if not options:

        options = [
            "1 仔細觀察周圍。（探索）",
            "2 主動與附近人物交談。（交涉）",
            "3 尋找可以利用的資源。（尋寶）",
            "4 暫時離開此地。（撤退）",
            "5 查看當前狀態。（不消耗回合）"
        ]

        st.session_state.current_options = options


    for idx, option in enumerate(options):

        # -------------------------------------------------
        # 唯一按鈕 key
        # -------------------------------------------------

        button_key = (
            f"turn_{game['turn']}_"
            f"option_{idx}"
        )

        if st.button(
            option,
            key=button_key,
            use_container_width=True,
            disabled=st.session_state.processing
        ):

            process_turn(option)

            st.rerun()


    st.markdown("---")


    # -----------------------------------------------------
    # 自由行動
    # -----------------------------------------------------

    st.subheader(
        "💬 自由意念"
    )

    custom_action = st.text_input(
        "你也可以自己決定要做什麼：",
        key=f"custom_action_{game['turn']}"
    )


    if st.button(
        "⚡ 執行自由行動",
        use_container_width=True,
        disabled=st.session_state.processing
    ):

        if custom_action.strip():

            process_turn(
                custom_action.strip()
            )

            st.rerun()

        else:

            st.warning(
                "請先輸入你想做的事情。"
            )


# =========================================================
# 背包
# =========================================================

elif current_view == "🎒 我的背包":

    st.subheader("🎒 我的背包")

    inventory = game["inventory"]

    if not inventory:

        st.info(
            "背包空空如也。"
        )

    else:

        for item in inventory:

            name = item.get(
                "name",
                "未知物品"
            )

            count = safe_int(
                item.get(
                    "count",
                    0
                )
            )

            desc = item.get(
                "desc",
                ""
            )

            with st.expander(
                f"【{name}】 × {count}"
            ):

                st.write(desc)


# =========================================================
# NPC
# =========================================================

elif current_view == "👥 人物關係":

    st.subheader(
        "👥 三界人物關係"
    )

    npcs = game["npcs"]

    if not npcs:

        st.info(
            "目前尚未正式結識任何人物。"
        )

    else:

        for name, npc in npcs.items():

            with st.expander(
                f"🌸 {name}"
            ):

                st.write(
                    f"**身份：** "
                    f"{npc.get('identity', '未知')}"
                )

                st.write(
                    f"**關係：** "
                    f"{npc.get('relationship', '陌生')}"
                )

                st.write(
                    f"**好感：** "
                    f"{npc.get('affinity', 0)}"
                )

                st.write(
                    f"**印象：** "
                    f"{npc.get('key_memory', '')}"
                )


# =========================================================
# 狀態
# =========================================================

elif current_view == "📊 狀態":

    st.subheader(
        "📊 當前角色狀態"
    )

    st.write(
        f"### 👤 {player['name']}"
    )

    st.write(
        f"**身份：** {player['identity']}"
    )

    st.write(
        f"**境界：** {player['realm']}"
    )

    st.write(
        f"**位置：** {player['location']}"
    )

    st.write(
        f"**狀態：** {player['status']}"
    )

    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "❤️ 生命",
        f"{player['hp']}/{player['max_hp']}"
    )

    col2.metric(
        "💙 靈力",
        f"{player['mp']}/{player['max_mp']}"
    )

    col3.metric(
        "🍚 飽腹",
        f"{player['fullness']}/100"
    )

    st.markdown("---")

    st.subheader(
        "🧠 基礎屬性"
    )

    st.write(
        f"🧠 悟性：{player['comprehension']}"
    )

    st.write(
        f"🎲 福緣：{player['fortune']}"
    )

    st.write(
        f"✨ 魅力：{player['charm']}"
    )

    st.write(
        f"⚖️ 正氣：{player['righteousness']}"
    )

    st.write(
        f"🩸 煞氣：{player['evil_aura']}"
    )

    st.write(
        f"👑 威名：{player['fame']}"
    )

    st.markdown("---")

    st.subheader(
        "🔒 身世"
    )

    if player["bloodline_awakened"]:

        st.success(
            f"🔥 血脈已覺醒："
            f"{player['secret_bloodline']}"
        )

    else:

        st.info(
            "你的真正身世仍然藏在迷霧之中。"
        )


# =========================================================
# 存檔
# =========================================================

elif current_view == "💾 存檔":

    st.subheader(
        "💾 遊戲存檔"
    )

    save_string = create_save()

    st.write(
        "複製以下完整內容保存。"
        "之後可以重新貼回遊戲讀取。"
    )

    st.text_area(
        "📋 存檔代碼",
        value=save_string,
        height=300,
        key="save_output"
    )

    st.markdown("---")

    st.subheader(
        "📥 讀取存檔"
    )

    load_text = st.text_area(
        "貼上存檔代碼",
        height=200,
        key="load_input"
    )

    if st.button(
        "🔄 載入這個存檔",
        use_container_width=True
    ):

        if load_text.strip():

            if load_save(
                load_text.strip()
            ):

                st.success(
                    "存檔載入成功！"
                )

                st.rerun()

        else:

            st.warning(
                "請先貼上存檔代碼。"
            )


# =========================================================
# 底部資訊
# =========================================================

st.markdown("---")

st.caption(
    "🌸 三界奇譚 V3.1 ・ "
    "劇情由 Nemotron 推演 ・ "
    "遊戲規則由本地程式控制"
)
