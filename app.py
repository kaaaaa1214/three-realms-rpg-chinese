import json
import random
import re
import streamlit as st
from openai import OpenAI


# =========================================================
# 三界奇譚 V3.2
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

API_KEY = st.secrets.get("OPENROUTER_API_KEY", "")

if not API_KEY:
    st.error(
        "⚠️ 尚未設定 OPENROUTER_API_KEY。\n\n"
        "請到 Streamlit Secrets 加入你的 OpenRouter API Key。"
    )
    st.stop()


client = OpenAI(
    api_key=API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

MODEL_NAME = "nvidia/nemotron-3-ultra-550b-a55b:free"


# =========================================================
# 世界設定
# =========================================================

LOCATIONS = [
    {
        "loc": "凡間·青石鎮",
        "identity": "街頭討生活的落魄孤兒",
        "bg": "自幼無依無靠，只能靠替人跑腿、拾荒與零碎活計維生。"
    },
    {
        "loc": "仙界·凌霄外園",
        "identity": "九霄雲宮最底層雜役仙侍",
        "bg": "每日清掃仙園、搬運雜物，身份低微，連普通仙人都懶得多看你一眼。"
    },
    {
        "loc": "妖界·萬妖山脈外圍",
        "identity": "被妖族部落遺棄的半妖",
        "bg": "血脈混雜，在妖族之中飽受排斥，只能依靠自己在危險山林中活下去。"
    },
    {
        "loc": "魔界·黑焰深淵礦區",
        "identity": "最低階的魔鐵礦奴",
        "bg": "每日挖掘魔鐵，稍有懈怠便會遭到監工責罰，性命根本不值一提。"
    },
    {
        "loc": "靈界·散修坊市",
        "identity": "擺地攤維生的落魄散修",
        "bg": "靈根低下，功法殘缺，經常受到修仙家族與坊市強者欺壓。"
    }
]


BLOODLINES = [
    "鳳凰涅槃血脈",
    "鴻蒙神魔同體印",
    "太古星辰帝君遺脈",
    "九幽妖皇真靈",
    "混沌青蓮本源",
    "太初玄冥道體"
]


# =========================================================
# 初始選項
# =========================================================

START_OPTIONS = [
    "1 仔細觀察四周，先弄清楚自己身處何地。（穩妥探索，可能發現環境線索）",
    "2 檢查破廟與自身物品，看看是否有被忽略的東西。（搜尋資源，可能發現物品）",
    "3 先離開破廟，前往附近坊市看看。（主動接觸外界，可能遇到人物或危險）",
    "4 找個隱蔽地方調息，嘗試感受體內靈力。（冒險修煉，可能觸發特殊機緣）",
    "5 查看當前狀態。（查看自身情況，不推進劇情）"
]


# =========================================================
# Session State 初始化
# =========================================================

DEFAULT_STATE = {
    "game_started": False,
    "active_tab": "📖 主線劇情",
    "turn": 0,
    "last_action": "",
    "last_story": "",
    "current_options": START_OPTIONS.copy(),
    "story_history": [],
    "game_state": {}
}


for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        if isinstance(value, list):
            st.session_state[key] = value.copy()
        elif isinstance(value, dict):
            st.session_state[key] = value.copy()
        else:
            st.session_state[key] = value


# =========================================================
# 工具函數
# =========================================================

def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def extract_number(value):
    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return int(value)

    if isinstance(value, str):
        match = re.search(r"-?\d+", value)
        if match:
            return int(match.group())

    return 0


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def clean_ai_text(text):
    if not isinstance(text, str):
        return ""

    text = text.replace("```json", "")
    text = text.replace("```", "")

    # 常見英文混入修正
    replacements = {
        "investigate": "調查",
        "Investigate": "調查",
        "investigation": "調查",
        "None": "",
        "none": "",
        "NPC": "人物",
        "HP": "生命",
        "MP": "靈力",
        "status": "狀態",
        "location": "位置",
        "money": "金錢",
        "inventory": "背包"
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text.strip()


def clean_option(option):
    if not isinstance(option, str):
        return ""

    option = clean_ai_text(option)

    option = option.replace("\n", " ").strip()

    # 避免 AI 自己加奇怪回合標題
    option = re.sub(
        r"第\s*\d+\s*回合[：:，,]?",
        "",
        option
    ).strip()

    return option


def normalize_hp_mp(value, maximum):
    current = extract_number(value)

    if current <= 0:
        current = maximum

    current = clamp(current, 0, maximum)

    return f"{current}/{maximum}"


def parse_json_response(raw_text):
    """
    優先直接解析。
    如果 AI 多出前後文字，嘗試抽取最外層 JSON。
    """

    if not raw_text:
        raise ValueError("模型沒有返回內容")

    text = raw_text.strip()

    text = text.replace("```json", "")
    text = text.replace("```", "")
    text = text.strip()

    # 直接解析
    try:
        return json.loads(text)
    except Exception:
        pass

    # 抽取第一個 { 到最後一個 }
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        candidate = text[start:end + 1]

        try:
            return json.loads(candidate)
        except Exception:
            pass

    raise ValueError("模型返回的內容不是有效 JSON")


# =========================================================
# 遊戲初始化
# =========================================================

def init_game(player_name):
    location = random.choice(LOCATIONS)
    bloodline = random.choice(BLOODLINES)

    if not player_name.strip():
        player_name = "詩柔"

    comprehension = random.randint(8, 12)
    fortune = random.randint(8, 12)
    charm = random.randint(8, 12)

    st.session_state.game_started = True
    st.session_state.turn = 0
    st.session_state.last_action = ""
    st.session_state.last_story = ""
    st.session_state.active_tab = "📖 主線劇情"

    st.session_state.game_state = {
        "player": {
            "name": player_name,
            "identity": f"{location['loc']}·{location['identity']}",
            "secret_bloodline": bloodline,
            "bloodline_awakened": False,

            "hp": "100/100",
            "mp": "30/30",
            "fullness": "90/100",

            "money": 5,

            "realm": "凡俗之軀 / 煉氣期一層",
            "location": location["loc"],
            "status": "健康",

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
                "desc": "磨損嚴重的普通衣物。"
            },
            {
                "name": "乾糧清水",
                "count": 2,
                "desc": "普通粗糧與清水，可稍微恢復飽腹度。"
            }
        ],

        "npcs": {},

        "world_flags": [],

        "story_summary": (
            f"你以五文錢開始人生，目前身處{location['loc']}，"
            f"身份低微，尚未掌握任何真正的修煉力量。"
        ),

        "used_actions": []
    }

    opening = (
        f"你睜開眼睛。\n\n"
        f"晨霧尚未散去，冰冷的空氣貼著你的臉頰。"
        f"你躺在{location['loc']}一處不起眼的角落，"
        f"身上的粗布麻衣沾滿塵土。\n\n"
        f"你是【{player_name}】。\n\n"
        f"如今的你，只是{location['identity']}。"
        f"{location['bg']}\n\n"
        f"摸遍全身，你只找到五文錢。\n\n"
        f"五文錢，在這個弱肉強食的世界裡，"
        f"甚至不足以換來一頓像樣的飯。\n\n"
        f"遠處鐘聲悠悠傳來，人群開始活動。"
        f"新的一日，又一次開始。\n\n"
        f"然而你並不知道，就在你醒來之前，"
        f"命運已經悄然替你推開了一扇門。\n\n"
        f"只是那扇門後面究竟是機緣，還是死路，"
        f"尚無人知曉。"
    )

    st.session_state.story_history = [
        {
            "turn": 0,
            "type": "story",
            "text": opening
        }
    ]

    st.session_state.last_story = opening
    st.session_state.current_options = START_OPTIONS.copy()


# =========================================================
# 狀態摘要
# =========================================================

def build_state_for_ai():
    game = st.session_state.game_state

    player = game["player"]

    return {
        "回合": st.session_state.turn,
        "主角": {
            "名字": player["name"],
            "身份": player["identity"],
            "境界": player["realm"],
            "位置": player["location"],
            "生命": player["hp"],
            "靈力": player["mp"],
            "飽腹": player["fullness"],
            "金錢": player["money"],
            "狀態": player["status"],
            "悟性": player["comprehension"],
            "福緣": player["fortune"],
            "魅力": player["charm"],
            "正氣": player["righteousness"],
            "煞氣": player["evil_aura"],
            "威名": player["fame"]
        },
        "背包": game["inventory"],
        "人物": game["npcs"],
        "世界標記": game["world_flags"],
        "劇情摘要": game["story_summary"],
        "最近行動": st.session_state.last_action,
        "上一幕劇情": st.session_state.last_story
    }


# =========================================================
# 建立最近歷史
# =========================================================

def recent_history_text():
    history = st.session_state.story_history[-8:]

    result = []

    for item in history:
        if item.get("type") == "story":
            result.append(
                f"第{item.get('turn', 0)}回合劇情：\n{item.get('text', '')}"
            )

        elif item.get("type") == "action":
            result.append(
                f"玩家行動：\n{item.get('text', '')}"
            )

    return "\n\n".join(result)


# =========================================================
# AI 系統指令
# =========================================================

SYSTEM_PROMPT = """
你是一名極高品質的中文修仙角色扮演遊戲主持人。

遊戲名稱：《三界奇譚：小薯逆襲記》。

你不是普通小說作者。
你必須根據玩家的實際行動、人物狀態、背包、世界標記及歷史劇情來推進遊戲。

【語言規則】

所有玩家可見內容必須使用自然、流暢、道地的繁體中文。

禁止出現：
英文單字
英文縮寫
英文程式詞彙
None
null
investigate
investigation
NPC
HP
MP
status
location
JSON
markdown

即使資料欄位名稱使用其他文字，玩家看到的劇情仍然必須完全中文。

【敘事風格】

使用半文半白的修仙小說筆法。

必須使用第二人稱「你」。

文字需要有：
環境描寫
人物表情
人物動機
細微動作
危機感
利益衝突
未知情報
合理因果

不要寫空泛內容。

禁止使用：
「命運的齒輪開始轉動」
「四周一片寂靜」
「你感到一切都很神秘」
「似乎有什麼事情即將發生」

除非後面立即發生具體事件。

【最重要：劇情推進規則】

玩家每次做出行動後，你必須讓世界產生至少一項具體變化。

具體變化可以是：

發現新物品
發現新人物
獲得情報
失去金錢
獲得金錢
受傷
恢復
飽腹度下降
觸發事件
NPC態度改變
地點改變
世界標記改變
發現危險
發現修煉線索
產生新的敵人
產生新的盟友
解開部分謎團

不能只是重新描述上一幕。

【禁止重複】

上一回合玩家做過的事情，不可以在下一回合原封不動再做一次。

上一回合已經發現的東西，不可以假裝從未發現。

上一回合已經描述過的事件，不可以重新播放。

新的劇情必須承接上一幕。

【選項規則】

每次必須提供四個新的主要行動。

另外第五項固定：

5 查看當前狀態。（查看資料，不推進劇情）

四個主要行動必須有不同策略，例如：

探索
交涉
冒險
修煉
交易
欺騙
逃跑
戰鬥
觀察
跟蹤
利用環境

不能四個選項都是「觀察」。

不能把上一回合相同的選項重新放回來。

【主角能力】

生命低於十五時，必須呈現瀕死危機。

飽腹低於十五時，主角會受到飢餓影響。

飽腹低於十五時，每次真正推進劇情的行動至少扣除五點生命。

不能無理由增加生命。

【隱藏血脈】

主角的隱藏血脈：

絕對不能在未覺醒前直接說出名稱。

不能寫：
「你其實擁有鳳凰血脈」
「你的血脈是……」

只能用異常現象暗示。

例如：
體內突然發熱
古老氣息一閃而逝
陌生夢境
奇異符文
身體對某種力量產生反應

【NPC】

人物必須有自己的目的。

不要讓所有人物都對主角友善。

人物可能：
欺騙
利用
威脅
試探
交易
幫助
背叛

人物記憶必須連貫。

【數值】

你可以合理改變：
生命
靈力
飽腹
金錢
境界
狀態
悟性
福緣
魅力
正氣
煞氣
威名

但是不要無理由暴增。

【非常重要】

不要自行增加回合數。

不要在劇情內寫：
第幾回合

不要生成：
👉
你選擇了

程式會自行顯示這些內容。

【輸出】

只能輸出一個 JSON 物件。

不要使用程式碼區塊。

不要在 JSON 前後加入任何文字。

JSON 必須包含：

story
story_summary_update
options
player_update
inventory_update
npc_updates
world_flags_update

story：
約三百至五百字。

story_summary_update：
八十字以內。

options：
五個字串。

前四個是不同的行動。
第五個必須是：
5 查看當前狀態。（查看資料，不推進劇情）

player_update：
只需要提供有變化或需要保留的主角資料。

inventory_update：
提供完整背包。

npc_updates：
只提供本回合新出現或有變化的人物。

world_flags_update：
提供目前重要世界標記。

【絕對不要輸出額外文字】
"""


# =========================================================
# 建立 AI Prompt
# =========================================================

def build_prompt(player_action):
    state = build_state_for_ai()
    history = recent_history_text()

    used_actions = st.session_state.game_state.get(
        "used_actions",
        []
    )

    banned_options = used_actions[-12:]

    prompt = f"""
【目前遊戲狀態】

{json.dumps(state, ensure_ascii=False, indent=2)}

【最近劇情】

{history}

【玩家這次真正採取的行動】

{player_action}

【最近已經使用過的玩家行動】

{json.dumps(banned_options, ensure_ascii=False)}

【重要要求】

你現在必須處理玩家這一次的行動。

不要重新播放上一幕。

必須讓事情向前發展。

必須產生至少一個具體世界變化。

必須生成四個與上一輪不同的新行動。

如果玩家的行動本身合理，必須讓它產生合理結果。

如果玩家的行動危險，可以讓玩家受傷、失敗或陷入危機。

如果玩家嘗試發現秘密，不可以直接揭露隱藏血脈。

請直接返回純 JSON。
"""

    return prompt


# =========================================================
# 驗證 AI 結果
# =========================================================

def validate_ai_result(data):
    if not isinstance(data, dict):
        raise ValueError("模型返回資料不是物件")

    required = [
        "story",
        "story_summary_update",
        "options",
        "player_update",
        "inventory_update",
        "npc_updates",
        "world_flags_update"
    ]

    for key in required:
        if key not in data:
            raise ValueError(f"模型缺少資料：{key}")

    story = clean_ai_text(data.get("story", ""))

    if len(story) < 80:
        raise ValueError("劇情內容太短")

    options = data.get("options", [])

    if not isinstance(options, list):
        raise ValueError("選項格式錯誤")

    cleaned_options = []

    for option in options:
        option = clean_option(option)

        if option:
            cleaned_options.append(option)

    # 至少要有 4 個
    if len(cleaned_options) < 4:
        raise ValueError("選項不足")

    # 去除重複
    unique_options = []

    for option in cleaned_options:
        normalized = re.sub(r"^\d+\s*", "", option)

        if normalized not in [
            re.sub(r"^\d+\s*", "", x)
            for x in unique_options
        ]:
            unique_options.append(option)

    if len(unique_options) < 4:
        raise ValueError("選項存在重複")

    # 只取前四個主要行動
    final_options = unique_options[:4]

    final_options.append(
        "5 查看當前狀態。（查看資料，不推進劇情）"
    )

    # 防止選項和最近行動完全相同
    recent_used = st.session_state.game_state.get(
        "used_actions",
        []
    )[-10:]

    for option in final_options[:4]:
        option_text = re.sub(
            r"^\d+\s*",
            "",
            option
        )

        for old_action in recent_used:
            if option_text in old_action or old_action in option_text:
                raise ValueError("模型生成了重複行動")

    # 防止劇情重複
    previous_story = st.session_state.last_story

    if previous_story:
        current_words = set(
            re.findall(r"[\u4e00-\u9fff]{2,}", story)
        )

        previous_words = set(
            re.findall(r"[\u4e00-\u9fff]{2,}", previous_story)
        )

        if current_words and previous_words:
            overlap = len(
                current_words & previous_words
            ) / max(
                1,
                len(current_words | previous_words)
            )

            if overlap > 0.72:
                raise ValueError("模型生成了高度重複劇情")

    data["story"] = story
    data["story_summary_update"] = clean_ai_text(
        data.get("story_summary_update", "")
    )[:100]

    data["options"] = final_options

    return data


# =========================================================
# 整理玩家數值
# =========================================================

def apply_player_update(update):
    game = st.session_state.game_state
    player = game["player"]

    if not isinstance(update, dict):
        return

    allowed = [
        "identity",
        "bloodline_awakened",
        "realm",
        "location",
        "status",
        "comprehension",
        "fortune",
        "charm",
        "righteousness",
        "evil_aura",
        "fame",
        "money"
    ]

    for key in allowed:
        if key in update:
            value = update[key]

            if key in [
                "comprehension",
                "fortune",
                "charm",
                "righteousness",
                "evil_aura",
                "fame",
                "money"
            ]:
                if key == "money":
                    value = max(0, extract_number(value))
                else:
                    value = extract_number(value)

            if key == "bloodline_awakened":
                value = bool(value)

            if isinstance(value, str):
                value = clean_ai_text(value)

            player[key] = value

    # 生命
    if "hp" in update:
        hp_value = extract_number(update["hp"])
        hp_value = clamp(hp_value, 0, 100)
        player["hp"] = f"{hp_value}/100"

    # 靈力
    if "mp" in update:
        mp_value = extract_number(update["mp"])
        mp_value = clamp(mp_value, 0, 100)
        player["mp"] = f"{mp_value}/100"

    # 飽腹
    if "fullness" in update:
        fullness_value = extract_number(update["fullness"])
        fullness_value = clamp(
            fullness_value,
            0,
            100
        )
        player["fullness"] = f"{fullness_value}/100"

    # 防止血脈在未覺醒時洩漏
    if not player.get("bloodline_awakened", False):
        # 不從 AI 更新血脈名稱
        pass

    # 飢餓機制
    fullness = extract_number(player["fullness"])
    hp = extract_number(player["hp"])

    if fullness < 15:
        hp = max(0, hp - 5)

        player["hp"] = f"{hp}/100"

        if hp <= 0:
            player["status"] = "瀕死"

        elif hp < 15:
            player["status"] = "極度虛弱"

        else:
            player["status"] = "飢餓"


# =========================================================
# 整理背包
# =========================================================

def apply_inventory_update(items):
    if not isinstance(items, list):
        return

    cleaned = []

    for item in items:
        if not isinstance(item, dict):
            continue

        name = clean_ai_text(
            str(item.get("name", "")).strip()
        )

        desc = clean_ai_text(
            str(item.get("desc", "")).strip()
        )

        count = extract_number(
            item.get("count", 0)
        )

        if not name:
            continue

        if count <= 0:
            continue

        cleaned.append({
            "name": name,
            "count": count,
            "desc": desc
        })

    st.session_state.game_state["inventory"] = cleaned


# =========================================================
# NPC
# =========================================================

def apply_npcs(npc_updates):
    if not isinstance(npc_updates, list):
        return

    npcs = st.session_state.game_state["npcs"]

    for npc in npc_updates:

        if not isinstance(npc, dict):
            continue

        name = clean_ai_text(
            str(npc.get("name", "")).strip()
        )

        if not name:
            continue

        npc_data = {
            "name": name,
            "identity": clean_ai_text(
                str(npc.get("identity", ""))
            ),
            "relationship": clean_ai_text(
                str(npc.get("relationship", ""))
            ),
            "affinity": extract_number(
                npc.get("affinity", 0)
            ),
            "key_memory": clean_ai_text(
                str(npc.get("key_memory", ""))
            )
        }

        npcs[name] = npc_data


# =========================================================
# 世界標記
# =========================================================

def apply_world_flags(flags):
    if not isinstance(flags, list):
        return

    cleaned = []

    for flag in flags:
        if isinstance(flag, str):
            flag = clean_ai_text(flag)

            if flag and flag not in cleaned:
                cleaned.append(flag)

    st.session_state.game_state["world_flags"] = cleaned[-30:]


# =========================================================
# 取得 AI 劇情
# =========================================================

def generate_story(player_action):

    game = st.session_state.game_state

    # 狀態查看不應該呼叫 AI
    if player_action.startswith("5 查看當前狀態"):
        return None

    # 防止完全重複行動
    normalized_action = player_action.strip()

    used_actions = game.get(
        "used_actions",
        []
    )

    if normalized_action in used_actions[-10:]:
        st.warning("⚠️ 這個行動剛剛已經採取過，請選擇其他行動。")
        return None

    prompt = build_prompt(player_action)

    with st.status(
        "🔮 正在推演三界命途……",
        expanded=True
    ) as status:

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
                temperature=0.8,
                max_tokens=2500
            )

            raw = response.choices[0].message.content

            status.write("正在解析命途結果……")

            data = parse_json_response(raw)

            data = validate_ai_result(data)

            status.update(
                label="✨ 命途推演完成",
                state="complete",
                expanded=False
            )

            return data

        except Exception as error:

            status.update(
                label="❌ 劇情生成失敗",
                state="error",
                expanded=True
            )

            st.error(
                "這一回合生成失敗。\n\n"
                f"原因：{str(error)}"
            )

            return None


# =========================================================
# 執行玩家行動
# =========================================================

def process_turn(player_action):

    player_action = clean_option(
        player_action
    )

    if not player_action:
        return

    # 查看狀態不消耗回合
    if player_action.startswith("5 查看當前狀態"):
        st.session_state.active_tab = "📊 當前狀態"
        return

    data = generate_story(
        player_action
    )

    if not data:
        return

    game = st.session_state.game_state

    # -----------------------------------------------------
    # 回合 +1
    # -----------------------------------------------------

    st.session_state.turn += 1

    current_turn = st.session_state.turn

    # -----------------------------------------------------
    # 保存玩家行動
    # -----------------------------------------------------

    game["used_actions"].append(
        player_action
    )

    game["used_actions"] = game["used_actions"][-30:]

    st.session_state.story_history.append({
        "turn": current_turn,
        "type": "action",
        "text": player_action
    })

    # -----------------------------------------------------
    # 更新玩家
    # -----------------------------------------------------

    apply_player_update(
        data.get("player_update", {})
    )

    # -----------------------------------------------------
    # 更新背包
    # -----------------------------------------------------

    apply_inventory_update(
        data.get("inventory_update", [])
    )

    # -----------------------------------------------------
    # 更新人物
    # -----------------------------------------------------

    apply_npcs(
        data.get("npc_updates", [])
    )

    # -----------------------------------------------------
    # 更新世界
    # -----------------------------------------------------

    apply_world_flags(
        data.get("world_flags_update", [])
    )

    # -----------------------------------------------------
    # 劇情
    # -----------------------------------------------------

    story = clean_ai_text(
        data.get("story", "")
    )

    st.session_state.story_history.append({
        "turn": current_turn,
        "type": "story",
        "text": story
    })

    st.session_state.last_story = story

    # -----------------------------------------------------
    # 摘要
    # -----------------------------------------------------

    summary = clean_ai_text(
        data.get(
            "story_summary_update",
            ""
        )
    )

    if summary:
        game["story_summary"] = summary

    # -----------------------------------------------------
    # 選項
    # -----------------------------------------------------

    options = data.get(
        "options",
        []
    )

    if len(options) >= 5:
        st.session_state.current_options = options[:5]

    else:
        st.session_state.current_options = [
            "1 仔細觀察眼前變化，尋找新的線索。（穩妥探索）",
            "2 嘗試與附近人物交涉，套取情報。（人際互動）",
            "3 暫時離開危險區域，尋找更安全的落腳處。（避險）",
            "4 利用手上的資源尋找新的機會。（資源經營）",
            "5 查看當前狀態。（查看資料，不推進劇情）"
        ]


# =========================================================
# 存檔
# =========================================================

def create_save_data():

    return {
        "version": "3.2",
        "game_started": True,
        "turn": st.session_state.turn,
        "game_state": st.session_state.game_state,
        "story_history": st.session_state.story_history,
        "current_options": st.session_state.current_options,
        "last_action": st.session_state.last_action,
        "last_story": st.session_state.last_story
    }


def load_save_data(save_string):

    loaded = json.loads(
        save_string
    )

    if not isinstance(loaded, dict):
        raise ValueError("存檔不是有效資料")

    game_state = loaded.get(
        "game_state"
    )

    if not isinstance(game_state, dict):
        raise ValueError("缺少遊戲狀態")

    if "player" not in game_state:
        raise ValueError("存檔缺少主角資料")

    st.session_state.game_started = True

    st.session_state.turn = safe_int(
        loaded.get("turn", 0)
    )

    st.session_state.game_state = game_state

    st.session_state.story_history = loaded.get(
        "story_history",
        []
    )

    st.session_state.current_options = loaded.get(
        "current_options",
        START_OPTIONS.copy()
    )

    st.session_state.last_action = loaded.get(
        "last_action",
        ""
    )

    st.session_state.last_story = loaded.get(
        "last_story",
        ""
    )

    st.session_state.active_tab = "📖 主線劇情"


# =========================================================
# 顯示狀態
# =========================================================

def display_status():

    game = st.session_state.game_state
    p = game["player"]

    st.subheader("📊 當前狀態")

    st.write(
        f"### 👤 {p['name']}"
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "❤️ 生命",
        p["hp"]
    )

    col2.metric(
        "💙 靈力",
        p["mp"]
    )

    col3.metric(
        "🍚 飽腹",
        p["fullness"]
    )

    col4.metric(
        "💰 金錢",
        f"{p.get('money', 0)} 文"
    )

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:

        st.write(
            f"**身份：** {p['identity']}"
        )

        st.write(
            f"**境界：** {p['realm']}"
        )

        st.write(
            f"**位置：** {p['location']}"
        )

        st.write(
            f"**狀態：** {p['status']}"
        )

    with col2:

        st.write(
            f"**悟性：** {p['comprehension']}"
        )

        st.write(
            f"**福緣：** {p['fortune']}"
        )

        st.write(
            f"**魅力：** {p['charm']}"
        )

        st.write(
            f"**正氣：** {p['righteousness']}"
        )

        st.write(
            f"**煞氣：** {p['evil_aura']}"
        )

        st.write(
            f"**威名：** {p['fame']}"
        )

    st.markdown("---")

    if p.get("bloodline_awakened", False):

        st.success(
            f"🔥 身世已覺醒：{p.get('secret_bloodline', '未知')}"
        )

    else:

        st.info(
            "🔒 身世之謎：尚未覺醒"
        )

    st.markdown("---")

    st.write(
        f"**劇情摘要：** {game.get('story_summary', '')}"
    )


# =========================================================
# 側邊欄
# =========================================================

def render_sidebar():

    with st.sidebar:

        st.header("📌 三界逆襲導航")

        if not st.session_state.game_started:
            return

        game = st.session_state.game_state
        p = game["player"]

        st.write(
            f"👤 **{p['name']}**"
        )

        st.write(
            f"🌀 第 **{st.session_state.turn}** 回合"
        )

        st.write(
            f"🏷️ {p['realm']}"
        )

        st.write(
            f"📍 {p['location']}"
        )

        st.markdown("---")

        col1, col2 = st.columns(2)

        col1.metric(
            "❤️ 生命",
            p["hp"]
        )

        col2.metric(
            "💙 靈力",
            p["mp"]
        )

        col3, col4 = st.columns(2)

        col3.metric(
            "🍚 飽腹",
            p["fullness"]
        )

        col4.metric(
            "💰 金錢",
            f"{p.get('money', 0)}"
        )

        st.markdown("---")

        if st.button(
            "📖 主線劇情",
            use_container_width=True
        ):

            st.session_state.active_tab = "📖 主線劇情"

            st.rerun()

        if st.button(
            "📊 當前狀態",
            use_container_width=True
        ):

            st.session_state.active_tab = "📊 當前狀態"

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
            "🌏 世界線索",
            use_container_width=True
        ):

            st.session_state.active_tab = "🌏 世界線索"

            st.rerun()

        if st.button(
            "💾 存檔／讀檔",
            use_container_width=True
        ):

            st.session_state.active_tab = "💾 存檔／讀檔"

            st.rerun()

        st.markdown("---")

        if st.button(
            "🎲 重開新人生",
            use_container_width=True
        ):

            st.session_state.game_started = False
            st.session_state.turn = 0
            st.session_state.story_history = []
            st.session_state.current_options = START_OPTIONS.copy()
            st.session_state.game_state = {}
            st.session_state.last_action = ""
            st.session_state.last_story = ""

            st.rerun()


# =========================================================
# 主頁面
# =========================================================

st.title(
    "🌸 三界奇譚：小薯逆襲記"
)


# =========================================================
# 開始遊戲
# =========================================================

if not st.session_state.game_started:

    st.subheader(
        "🎲 踏入命途"
    )

    st.write(
        "你將從三界最底層開始。"
        "沒有顯赫身世，沒有強大神通，"
        "只有五文錢，以及一條未知的命。"
    )

    st.markdown("---")

    with st.form(
        "start_game_form"
    ):

        player_name = st.text_input(
            "請輸入你的名字",
            value="詩柔"
        )

        start_button = st.form_submit_button(
            "🌸 開始逆襲人生",
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
        height=180
    )

    if st.button(
        "📂 讀取存檔",
        use_container_width=True
    ):

        if not load_code.strip():

            st.warning(
                "請先貼上存檔代碼。"
            )

        else:

            try:

                load_save_data(
                    load_code.strip()
                )

                st.success(
                    "✨ 存檔讀取成功！"
                )

                st.rerun()

            except Exception as error:

                st.error(
                    f"存檔讀取失敗：{error}"
                )

    st.stop()


# =========================================================
# 顯示側邊欄
# =========================================================

render_sidebar()


# =========================================================
# 主線劇情
# =========================================================

current_view = st.session_state.active_tab


if current_view == "📖 主線劇情":

    st.subheader(
        "📖 主線劇情與冒險"
    )

    history = st.session_state.story_history

    for item in history:

        turn = item.get(
            "turn",
            0
        )

        item_type = item.get(
            "type",
            "story"
        )

        text = item.get(
            "text",
            ""
        )

        if item_type == "action":

            st.info(
                f"👉 你選擇了：{text}"
            )

        else:

            if turn == 0:

                st.markdown(
                    text
                )

            else:

                st.markdown(
                    f"### 第 {turn} 回合\n\n{text}"
                )

    st.markdown("---")

    st.write(
        "### ✨ 你打算怎樣行動？"
    )

    options = st.session_state.current_options

    for index, option in enumerate(options):

        button_key = (
            f"option_{"
            f"st.session_state.turn}_"
            f"{index}"
        )

        if st.button(
            option,
            key=button_key,
            use_container_width=True
        ):

            st.session_state.last_action = option

            process_turn(
                option
            )

            st.rerun()

    st.markdown("---")

    st.write(
        "### 💬 自由意念"
    )

    st.caption(
        "你也可以不選選項，直接描述自己想做什麼。"
    )

    custom_action = st.text_input(
        "例如：我想偷偷跟蹤那名黑衣修士。",
        key="custom_action"
    )

    if st.button(
        "✦ 執行我的行動",
        use_container_width=True
    ):

        if custom_action.strip():

            st.session_state.last_action = custom_action.strip()

            process_turn(
                custom_action.strip()
            )

            st.rerun()

        else:

            st.warning(
                "請先輸入你的行動。"
            )


# =========================================================
# 狀態
# =========================================================

elif current_view == "📊 當前狀態":

    display_status()

    if st.button(
        "⬅️ 返回主線",
        use_container_width=True
    ):

        st.session_state.active_tab = "📖 主線劇情"

        st.rerun()


# =========================================================
# 背包
# =========================================================

elif current_view == "🎒 我的背包":

    st.subheader(
        "🎒 我的背包"
    )

    inventory = st.session_state.game_state.get(
        "inventory",
        []
    )

    if not inventory:

        st.info(
            "你的背包空空如也。"
        )

    else:

        for item in inventory:

            with st.container(
                border=True
            ):

                st.write(
                    f"### 【{item['name']}】 × {item['count']}"
                )

                st.write(
                    item.get(
                        "desc",
                        ""
                    )
                )

    if st.button(
        "⬅️ 返回主線",
        use_container_width=True
    ):

        st.session_state.active_tab = "📖 主線劇情"

        st.rerun()


# =========================================================
# NPC
# =========================================================

elif current_view == "👥 人物關係":

    st.subheader(
        "👥 三界人物關係"
    )

    npcs = st.session_state.game_state.get(
        "npcs",
        {}
    )

    if not npcs:

        st.info(
            "目前尚未真正結識任何重要人物。"
        )

    else:

        for name, npc in npcs.items():

            affinity = npc.get(
                "affinity",
                0
            )

            with st.expander(
                f"🌸 {name}　｜　關係：{affinity}"
            ):

                st.write(
                    f"**身份：** {npc.get('identity', '')}"
                )

                st.write(
                    f"**關係：** {npc.get('relationship', '')}"
                )

                st.write(
                    f"**記憶：** {npc.get('key_memory', '')}"
                )

    if st.button(
        "⬅️ 返回主線",
        use_container_width=True
    ):

        st.session_state.active_tab = "📖 主線劇情"

        st.rerun()


# =========================================================
# 世界線索
# =========================================================

elif current_view == "🌏 世界線索":

    st.subheader(
        "🌏 世界線索"
    )

    flags = st.session_state.game_state.get(
        "world_flags",
        []
    )

    if not flags:

        st.info(
            "目前尚未掌握任何重要線索。"
        )

    else:

        for index, flag in enumerate(flags, 1):

            st.write(
                f"**{index}.** {flag}"
            )

    st.markdown("---")

    st.write(
        "### 📜 當前劇情摘要"
    )

    st.write(
        st.session_state.game_state.get(
            "story_summary",
            ""
        )
    )

    if st.button(
        "⬅️ 返回主線",
        use_container_width=True
    ):

        st.session_state.active_tab = "📖 主線劇情"

        st.rerun()


# =========================================================
# 存檔／讀檔
# =========================================================

elif current_view == "💾 存檔／讀檔":

    st.subheader(
        "💾 存檔／讀檔"
    )

    save_data = create_save_data()

    save_string = json.dumps(
        save_data,
        ensure_ascii=False
    )

    st.write(
        "### 📋 當前存檔"
    )

    st.text_area(
        "請全選並複製以下內容保存",
        value=save_string,
        height=260,
        key="save_output"
    )

    st.markdown("---")

    st.write(
        "### 📥 讀取存檔"
    )

    load_string = st.text_area(
        "把之前的存檔貼在這裡",
        height=200,
        key="save_input"
    )

    if st.button(
        "🔄 載入存檔",
        use_container_width=True
    ):

        if not load_string.strip():

            st.warning(
                "請先貼上存檔。"
            )

        else:

            try:

                load_save_data(
                    load_string.strip()
                )

                st.success(
                    "✨ 讀檔成功！"
                )

                st.rerun()

            except Exception as error:

                st.error(
                    f"讀檔失敗：{error}"
                )

    st.markdown("---")

    if st.button(
        "⬅️ 返回主線",
        use_container_width=True
    ):

        st.session_state.active_tab = "📖 主線劇情"

        st.rerun()
