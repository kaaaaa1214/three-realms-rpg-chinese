import json
import random
import re
import urllib.request
import urllib.error

import streamlit as st


# =========================================================
# 三界奇譚 V3
# OpenRouter + NVIDIA Nemotron 3 Ultra 免費版
# =========================================================

st.set_page_config(
    page_title="三界奇譚：小薯逆襲記 V3",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# 1. 基本設定
# =========================================================

MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MAX_RECENT_STORIES = 4
MAX_NPCS = 20
MAX_INVENTORY = 30


# =========================================================
# 2. OpenRouter API
# =========================================================

api_key = st.secrets.get("OPENROUTER_API_KEY", "").strip()

if not api_key:
    st.error(
        "⚠️ 尚未設定 OPENROUTER_API_KEY。\n\n"
        "請到 Streamlit → Settings → Secrets 加入：\n\n"
        'OPENROUTER_API_KEY = "你的 API Key"'
    )
    st.stop()


def call_ai(messages):
    """
    使用標準 Python urllib 呼叫 OpenRouter。
    不需要額外安裝 openai 套件。
    """

    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.85,
        "top_p": 0.9,
        "max_tokens": 1800,
        "stream": False,
    }

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    request = urllib.request.Request(
        OPENROUTER_URL,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://three-realms-rpg.streamlit.app",
            "X-Title": "三界奇譚 V3",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            raw = response.read().decode("utf-8")
            result = json.loads(raw)

        choices = result.get("choices", [])

        if not choices:
            raise RuntimeError("OpenRouter 沒有返回有效結果。")

        content = choices[0].get("message", {}).get("content", "")

        if not content:
            raise RuntimeError("AI 返回內容為空。")

        return content

    except urllib.error.HTTPError as e:
        error_body = ""

        try:
            error_body = e.read().decode("utf-8")
        except Exception:
            pass

        try:
            error_json = json.loads(error_body)
            message = error_json.get("error", {}).get("message", error_body)
        except Exception:
            message = error_body or str(e)

        raise RuntimeError(
            f"OpenRouter API 錯誤 {e.code}：{message}"
        )

    except urllib.error.URLError as e:
        raise RuntimeError(
            f"無法連接 OpenRouter：{e.reason}"
        )

    except Exception as e:
        raise RuntimeError(str(e))


# =========================================================
# 3. JSON 安全解析
# =========================================================

def extract_json(text):
    """
    AI 有時會：
    ```json
    {...}
    ```

    或者前後加少量說明。

    呢個 function 會盡量抽出真正 JSON。
    """

    if not text:
        return None

    text = text.strip()

    # 移除 markdown code block
    text = text.replace("```json", "")
    text = text.replace("```JSON", "")
    text = text.replace("```", "")
    text = text.strip()

    # 第一種：直接 JSON
    try:
        return json.loads(text)
    except Exception:
        pass

    # 第二種：尋找第一個 { 到最後一個 }
    start = text.find("{")
    end = text.rfind("}")

    if start >= 0 and end > start:
        candidate = text[start:end + 1]

        try:
            return json.loads(candidate)
        except Exception:
            pass

    return None


# =========================================================
# 4. 基本資料
# =========================================================

LOCATIONS = [
    {
        "loc": "凡間·青石鎮",
        "identity": "街頭乞討的孤苦孤兒",
        "bg": "父母雙亡，每日為下一頓飯發愁，在市井中看盡人情冷暖。"
    },
    {
        "loc": "仙界·凌霄外園",
        "identity": "九霄雲宮最底層雜役仙侍",
        "bg": "每天負責打掃仙園落花與倒夜香，是仙界最卑微的小薯。"
    },
    {
        "loc": "妖界·萬妖山脈",
        "identity": "靈智未開就被放養的半妖奴隸",
        "bg": "混血身份在妖界備受排擠，只能在強大妖獸的爪下艱難求生。"
    },
    {
        "loc": "魔界·黑焰深淵",
        "identity": "最低賤的魔鐵礦奴工",
        "bg": "每日承受魔氣侵蝕與監工皮鞭，過著見不到明天的日子。"
    },
    {
        "loc": "靈界·散修坊市",
        "identity": "擺地攤維生的落魄散修",
        "bg": "靈根低下，功法殘缺，經常被修仙家族欺壓。"
    },
]


POTENTIAL_BLOODLINES = [
    "鳳凰涅槃血脈",
    "鴻蒙神魔同體印",
    "太古星辰帝君遺脈",
    "九幽妖皇真靈",
]


START_OPTIONS = [
    "1 先觀察四周，不急著暴露自己的存在。（靜觀其變，風險較低）",
    "2 主動尋找可以換取食物或錢財的事情。（改善生存條件，但可能被利用）",
    "3 找人套話，先弄清楚這裡的規矩。（獲取情報，但可能引起警惕）",
    "4 尋找偏僻角落，檢查附近是否藏著異常之物。（可能發現機緣，也可能遇到危險）",
    "5 查看當前狀態與身心狀況",
]


# =========================================================
# 5. 遊戲初始化
# =========================================================

def init_game(player_name):

    location = random.choice(LOCATIONS)
    bloodline = random.choice(POTENTIAL_BLOODLINES)

    name = player_name.strip() or "詩柔"

    comprehension = random.randint(8, 12)
    fortune = random.randint(8, 12)
    charm = random.randint(8, 12)

    player = {
        "name": name,
        "identity": f"{location['loc']}·{location['identity']}",

        # 絕對不會在未覺醒前顯示給玩家
        "secret_bloodline": bloodline,
        "bloodline_awakened": False,

        "hp": 100,
        "max_hp": 100,

        "mp": 30,
        "max_mp": 30,

        "fullness": 90,

        "money": 5,

        "realm": "凡俗之軀 / 煉氣期一層",

        "location": location["loc"],

        "status": "健康（平靜）",

        "comprehension": comprehension,
        "fortune": fortune,
        "charm": charm,

        "righteousness": 0,
        "evil_aura": 0,
        "fame": 0,
    }

    opening_story = (
        f"【命運開啟】\n\n"
        f"你睜開眼睛，發現自己正身處在{location['loc']}。\n\n"
        f"你是【{name}】，身上僅剩五文錢。"
        f"此刻的你只是個平凡無奇的{location['identity']}。\n\n"
        f"{location['bg']}\n\n"
        f"晨霧尚未散去，遠處傳來零碎腳步聲。"
        f"沒有人知道你的名字，更沒有人在意你的死活。\n\n"
        f"可你很清楚——"
        f"若想在這個弱肉強食的世界活下去，"
        f"便只能從最卑微的地方，一步一步爬上去。\n\n"
        f"屬於你的逆襲之路，正式開始。"
    )

    st.session_state.game_state = {
        "player": player,

        "inventory": [
            {
                "name": "粗布麻衣",
                "count": 1,
                "desc": "極為普通的日常衣物，已經有些磨損。"
            },
            {
                "name": "乾糧",
                "count": 2,
                "desc": "粗糧製成的乾糧，可以暫時充飢。"
            },
            {
                "name": "清水",
                "count": 1,
                "desc": "普通清水。"
            },
        ],

        "npcs": {},

        "quests": [],

        "clues": [],

        "story_history": [opening_story],

        "story_summary": (
            f"主角{ name }在{location['loc']}白手起家。"
            f"目前身無長物，只有五文錢，尚未發現真正的身世秘密。"
        ),

        "turn": 0,
    }

    st.session_state.current_options = START_OPTIONS.copy()
    st.session_state.game_started = True
    st.session_state.active_tab = "📖 主線劇情"


# =========================================================
# 6. 狀態格式化
# =========================================================

def hp_text(player):
    return f"{player['hp']}/{player['max_hp']}"


def mp_text(player):
    return f"{player['mp']}/{player['max_mp']}"


def fullness_text(player):
    return f"{player['fullness']}/100"


def public_player_state(player):
    """
    給 AI 的玩家資料。

    secret_bloodline 絕對不放入 prompt。
    """

    return {
        "name": player["name"],
        "identity": player["identity"],
        "hp": hp_text(player),
        "mp": mp_text(player),
        "fullness": fullness_text(player),
        "money": player["money"],
        "realm": player["realm"],
        "location": player["location"],
        "status": player["status"],
        "comprehension": player["comprehension"],
        "fortune": player["fortune"],
        "charm": player["charm"],
        "righteousness": player["righteousness"],
        "evil_aura": player["evil_aura"],
        "fame": player["fame"],
        "bloodline_awakened": player["bloodline_awakened"],
    }


# =========================================================
# 7. NPC / 背包安全處理
# =========================================================

def clean_inventory(inventory):

    cleaned = []

    for item in inventory:

        if not isinstance(item, dict):
            continue

        name = str(item.get("name", "")).strip()

        if not name:
            continue

        try:
            count = int(item.get("count", 0))
        except Exception:
            count = 0

        count = max(0, min(count, 999))

        desc = str(item.get("desc", "普通物品。"))

        if count > 0:
            cleaned.append({
                "name": name[:50],
                "count": count,
                "desc": desc[:150],
            })

    return cleaned[:MAX_INVENTORY]


def update_npcs(npc_updates):

    game = st.session_state.game_state

    if not isinstance(npc_updates, list):
        return

    for npc in npc_updates:

        if not isinstance(npc, dict):
            continue

        name = str(npc.get("name", "")).strip()

        if not name:
            continue

        name = name[:30]

        existing = game["npcs"].get(
            name,
            {
                "name": name,
                "identity": "",
                "relationship": "陌生",
                "affinity": 0,
                "key_memory": "",
            }
        )

        existing["identity"] = str(
            npc.get("identity", existing["identity"])
        )[:100]

        existing["relationship"] = str(
            npc.get("relationship", existing["relationship"])
        )[:50]

        try:
            affinity = int(
                npc.get("affinity", existing["affinity"])
            )
        except Exception:
            affinity = existing["affinity"]

        existing["affinity"] = max(-100, min(100, affinity))

        existing["key_memory"] = str(
            npc.get("key_memory", existing["key_memory"])
        )[:200]

        game["npcs"][name] = existing

    # 最多保留 20 個 NPC
    if len(game["npcs"]) > MAX_NPCS:
        names = list(game["npcs"].keys())
        for name in names[:-MAX_NPCS]:
            del game["npcs"][name]


# =========================================================
# 8. 效果處理
# =========================================================

def apply_effects(data):

    game = st.session_state.game_state
    player = game["player"]

    effects = data.get("effects", {})

    if not isinstance(effects, dict):
        effects = {}

    # -------------------------
    # HP
    # -------------------------

    try:
        hp_change = int(effects.get("hp_change", 0))
    except Exception:
        hp_change = 0

    hp_change = max(-30, min(30, hp_change))

    player["hp"] += hp_change
    player["hp"] = max(0, min(player["max_hp"], player["hp"]))

    # -------------------------
    # MP
    # -------------------------

    try:
        mp_change = int(effects.get("mp_change", 0))
    except Exception:
        mp_change = 0

    mp_change = max(-20, min(20, mp_change))

    player["mp"] += mp_change
    player["mp"] = max(0, min(player["max_mp"], player["mp"]))

    # -------------------------
    # 飽腹
    # -------------------------

    try:
        fullness_change = int(
            effects.get("fullness_change", -2)
        )
    except Exception:
        fullness_change = -2

    fullness_change = max(-20, min(20, fullness_change))

    player["fullness"] += fullness_change

    # 每次行動自然消耗
    player["fullness"] -= 2

    player["fullness"] = max(
        0,
        min(100, player["fullness"])
    )

    # 飢餓懲罰
    if player["fullness"] < 15:
        player["hp"] -= 5
        player["hp"] = max(0, player["hp"])
        player["status"] = "極度飢餓"
    elif player["hp"] < 15:
        player["status"] = "瀕死"
    else:
        ai_status = str(effects.get("status", "")).strip()

        if ai_status:
            player["status"] = ai_status[:50]
        else:
            player["status"] = "健康"

    # -------------------------
    # 金錢
    # -------------------------

    try:
        money_change = int(
            effects.get("money_change", 0)
        )
    except Exception:
        money_change = 0

    money_change = max(-50, min(100, money_change))

    player["money"] += money_change
    player["money"] = max(0, player["money"])

    # -------------------------
    # 正氣
    # -------------------------

    try:
        righteousness_change = int(
            effects.get("righteousness_change", 0)
        )
    except Exception:
        righteousness_change = 0

    righteousness_change = max(-10, min(10, righteousness_change))

    player["righteousness"] += righteousness_change

    # -------------------------
    # 煞氣
    # -------------------------

    try:
        evil_change = int(
            effects.get("evil_aura_change", 0)
        )
    except Exception:
        evil_change = 0

    evil_change = max(-10, min(10, evil_change))

    player["evil_aura"] += evil_change

    # -------------------------
    # 威名
    # -------------------------

    try:
        fame_change = int(
            effects.get("fame_change", 0)
        )
    except Exception:
        fame_change = 0

    fame_change = max(-10, min(10, fame_change))

    player["fame"] += fame_change

    # -------------------------
    # 境界
    # -------------------------

    realm_change = effects.get("realm")

    if isinstance(realm_change, str):
        realm_change = realm_change.strip()

        if realm_change and len(realm_change) <= 80:
            player["realm"] = realm_change

    # -------------------------
    # 位置
    # -------------------------

    location_change = effects.get("location")

    if isinstance(location_change, str):
        location_change = location_change.strip()

        if location_change and len(location_change) <= 80:
            player["location"] = location_change

    # -------------------------
    # 物品增加
    # -------------------------

    gain_item = effects.get("gain_item")

    if isinstance(gain_item, dict):

        name = str(gain_item.get("name", "")).strip()
        desc = str(gain_item.get("desc", "普通物品。")).strip()

        try:
            count = int(gain_item.get("count", 1))
        except Exception:
            count = 1

        count = max(1, min(20, count))

        if name:

            found = False

            for item in game["inventory"]:
                if item["name"] == name:
                    item["count"] += count
                    found = True
                    break

            if not found:
                game["inventory"].append({
                    "name": name[:50],
                    "count": count,
                    "desc": desc[:150],
                })

    # -------------------------
    # 物品減少
    # -------------------------

    lose_item = effects.get("lose_item")

    if isinstance(lose_item, dict):

        name = str(lose_item.get("name", "")).strip()

        try:
            count = int(lose_item.get("count", 1))
        except Exception:
            count = 1

        count = max(1, min(20, count))

        for item in game["inventory"]:

            if item["name"] == name:
                item["count"] -= count

    game["inventory"] = clean_inventory(
        game["inventory"]
    )


# =========================================================
# 9. AI System Prompt
# =========================================================

SYSTEM_PROMPT = r"""
你是《三界奇譚》的高品質文字 RPG 遊戲主持人。

你不是聊天機械人。
你是遊戲主持人。
你必須推動故事真正發生事件。

【語言】

所有劇情、對話、選項、摘要必須使用自然流暢的繁體中文。

禁止：
英文單字
英文句子
拼音
程式碼
奇怪的外語

專有名詞可以使用中文創作。

【敘事】

固定使用第二人稱「你」。

文風：
半文半白、古典修仙小說。

要求：
有畫面感。
有環境。
有人物反應。
有危機。
有人心試探。
有真正事件。

不要每一回合都只是聊天。

【非常重要：劇情必須推進】

每次玩家行動後，至少發生一件真正的事件。

例如：

玩家調查
→ 發現線索

玩家套話
→ NPC透露秘密

玩家逃跑
→ 發生追逐

玩家交易
→ 得到物品或欠下人情

玩家修煉
→ 發現異常靈氣

玩家觀察
→ 發現某人正在監視自己

禁止：

「你問他，他問你想知道什麼。」

「你沉默，他看著你。」

「你繼續等待。」

「事情似乎沒有變化。」

除非真的有重要伏筆，否則不能連續兩回合停留在同一個小事件。

【NPC】

NPC 必須有：
身份
目的
性格
秘密
利益

NPC 不會無條件幫助玩家。

NPC 可以：
說謊
試探
利用
交易
欺騙
幫忙
背叛
害怕
逃跑

但所有行為必須符合當前情境。

【玩家】

不要替玩家做重大決定。

不要寫：
「你決定殺死某人。」

除非玩家明確選擇殺人。

不要替玩家說大量台詞。

可以描寫玩家自然反應，但不能替玩家完成重大行動。

【世界】

這是一個弱肉強食的修仙世界。

凡人、修士、仙人、妖族、魔族都有自己的階層。

主角目前非常弱。

不要無理由讓主角突然變強。

不要突然送神級寶物。

機緣必須有代價。

【血脈】

玩家擁有隱藏血脈。

在未覺醒前：
絕對不能直接說出血脈名稱。

不能說：
「你的鳳凰血脈正在覺醒。」

只能使用：
異常體溫
夢境
血液異象
古老氣息
靈獸異常反應
未知感應

除非遊戲真正觸發覺醒。

【數值】

AI 可以提出效果，但必須合理。

單回合：
HP 最大變化 ±30
MP 最大變化 ±20
飽腹最大變化 ±20
金錢最大變化 ±100

不要無理由大幅提升境界。

【選項】

每回合提供 4 個主要選項。

第五個固定：

5 查看當前狀態與身心狀況

四個主要選項必須有不同策略：

1. 穩妥
2. 交涉／情報
3. 冒險
4. 特殊／冷酷／機智

每個選項最後加：
（核心意圖：……）

【劇情長度】

story 約 300～500 個中文字。

不要刻意計算字數。

【JSON】

只輸出 JSON。

不要輸出 markdown。

不要輸出 ```json。

格式：

{
  "story": "劇情",
  "story_summary": "80字內摘要",
  "options": [
    "1 ……（核心意圖：……）",
    "2 ……（核心意圖：……）",
    "3 ……（核心意圖：……）",
    "4 ……（核心意圖：……）",
    "5 查看當前狀態與身心狀況"
  ],
  "effects": {
    "hp_change": 0,
    "mp_change": 0,
    "fullness_change": -2,
    "money_change": 0,
    "righteousness_change": 0,
    "evil_aura_change": 0,
    "fame_change": 0,
    "status": "",
    "realm": "",
    "location": "",
    "gain_item": null,
    "lose_item": null
  },
  "npc_updates": [
    {
      "name": "人物名字",
      "identity": "身份",
      "relationship": "關係",
      "affinity": 0,
      "key_memory": "本回合形成的重要記憶"
    }
  ],
  "quest_update": "",
  "clue_update": ""
}

【非常重要】

不要加入：
player_update

不要自行重新生成：
HP
MP
金錢
背包

只可以在 effects 中提出「變化」。

Python 會負責真正結算。

如果沒有變化：
數值必須是 0。

【JSON安全】

所有 JSON 字串內的雙引號必須正確轉義。

不要在 JSON 外輸出任何文字。
"""


# =========================================================
# 10. 建立 AI Prompt
# =========================================================

def build_prompt(player_action):

    game = st.session_state.game_state
    player = game["player"]

    recent_history = game["story_history"][-MAX_RECENT_STORIES:]

    npc_memory = list(game["npcs"].values())[-10:]

    inventory = game["inventory"]

    quests = game.get("quests", [])[-10:]
    clues = game.get("clues", [])[-10:]

    prompt = f"""
【目前回合】
第 {game["turn"] + 1} 回合

【玩家狀態】
{json.dumps(public_player_state(player), ensure_ascii=False)}

【背包】
{json.dumps(inventory, ensure_ascii=False)}

【NPC記憶】
{json.dumps(npc_memory, ensure_ascii=False)}

【目前任務】
{json.dumps(quests, ensure_ascii=False)}

【目前線索】
{json.dumps(clues, ensure_ascii=False)}

【長期劇情摘要】
{game.get("story_summary", "")}

【最近劇情】
{json.dumps(recent_history, ensure_ascii=False)}

【玩家最新行動】
{player_action}

請根據以上內容推進下一幕。

注意：
這不是單純聊天。
一定要有真正事件發生。

只回傳 JSON。
"""

    return prompt


# =========================================================
# 11. AI 回應安全修復
# =========================================================

def sanitize_story(text):

    if not isinstance(text, str):
        return ""

    text = text.strip()

    # 移除常見 markdown
    text = text.replace("```json", "")
    text = text.replace("```", "")

    # 修正常見英文混入
    replacements = {
        "investigte": "調查",
        "investigate": "調查",
        "investigation": "調查",
        "NPC": "人物",
        "HP": "生命值",
        "MP": "靈力",
        "status": "狀態",
        "quest": "任務",
        "update": "更新",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text.strip()


def validate_ai_data(data):

    if not isinstance(data, dict):
        return None

    story = data.get("story")

    if not isinstance(story, str):
        return None

    story = sanitize_story(story)

    if len(story) < 30:
        return None

    summary = data.get("story_summary", "")

    if not isinstance(summary, str):
        summary = ""

    summary = sanitize_story(summary)[:120]

    options = data.get("options", [])

    if not isinstance(options, list):
        options = []

    clean_options = []

    for option in options[:4]:

        if isinstance(option, str):
            option = sanitize_story(option).strip()

            if option:
                clean_options.append(option)

    while len(clean_options) < 4:

        defaults = [
            "觀察四周局勢，尋找更安全的突破口。（核心意圖：降低風險）",
            "試著與附近人物交談，套取有用情報。（核心意圖：獲取情報）",
            "冒險調查眼前的異常之處。（核心意圖：尋找機緣）",
            "暫時抽身，尋找更有利的位置。（核心意圖：保存實力）",
        ]

        for default in defaults:
            if len(clean_options) >= 4:
                break

            if default not in clean_options:
                clean_options.append(default)

    clean_options = clean_options[:4]

    clean_options.append(
        "5 查看當前狀態與身心狀況"
    )

    effects = data.get("effects", {})

    if not isinstance(effects, dict):
        effects = {}

    npc_updates = data.get("npc_updates", [])

    if not isinstance(npc_updates, list):
        npc_updates = []

    quest_update = data.get("quest_update", "")

    if not isinstance(quest_update, str):
        quest_update = ""

    clue_update = data.get("clue_update", "")

    if not isinstance(clue_update, str):
        clue_update = ""

    return {
        "story": story,
        "story_summary": summary,
        "options": clean_options,
        "effects": effects,
        "npc_updates": npc_updates,
        "quest_update": sanitize_story(quest_update)[:200],
        "clue_update": sanitize_story(clue_update)[:200],
    }


# =========================================================
# 12. AI 失敗時的安全劇情
# =========================================================

def fallback_turn(player_action, error_message):

    game = st.session_state.game_state
    player = game["player"]

    story = (
        "你沒有急著再次行動。\n\n"
        "四周的風聲從耳畔掠過，原本零散的人聲忽然低了下去。"
        "你敏銳地察覺到，附近似乎有人正在注意你的動靜。\n\n"
        "你沒有回頭，只是借著餘光觀察地面的影子。"
        "不遠處，一雙鞋停在了牆角後方。\n\n"
        "那人沒有走近，也沒有離開。\n\n"
        "片刻後，一枚細小的石子從牆角滾了出來，"
        "停在你的腳邊。\n\n"
        "石子下面壓著半片泛黃的紙角。\n\n"
        "你沒有立即伸手去拿。\n\n"
        "在這個地方，太容易得到的東西，往往才是最危險的東西。"
    )

    return {
        "story": story,
        "story_summary": game.get("story_summary", ""),
        "options": [
            "1 暫時不碰紙片，繼續觀察暗中的人。（核心意圖：避免落入陷阱）",
            "2 直接拾起紙片查看內容。（核心意圖：獲取情報）",
            "3 假裝沒有發現，悄悄改變位置。（核心意圖：試探對方）",
            "4 主動走向牆角，逼對方現身。（核心意圖：反客為主）",
            "5 查看當前狀態與身心狀況",
        ],
        "effects": {
            "hp_change": 0,
            "mp_change": 0,
            "fullness_change": -2,
            "money_change": 0,
            "righteousness_change": 0,
            "evil_aura_change": 0,
            "fame_change": 0,
            "status": player["status"],
            "realm": "",
            "location": "",
            "gain_item": None,
            "lose_item": None,
        },
        "npc_updates": [],
        "quest_update": "",
        "clue_update": "暗中似乎有人注意你的行蹤，牆角出現一枚壓著紙片的石子。",
        "_fallback": True,
        "_error": error_message,
    }


# =========================================================
# 13. 處理一個回合
# =========================================================

def process_turn(player_action):

    game = st.session_state.game_state

    player_action = str(player_action).strip()

    if not player_action:
        return

    # -----------------------------------------------------
    # 查看狀態不需要呼叫 AI
    # -----------------------------------------------------

    if player_action.startswith("5 ") or player_action.startswith("5　"):

        show_status_message()

        return

    prompt = build_prompt(player_action)

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

    with st.status(
        "🔮 三界命輪運轉中……",
        expanded=True
    ) as status:

        try:

            st.write(
                "正在召喚 NVIDIA Nemotron 3 Ultra……"
            )

            raw_text = call_ai(messages)

            st.write("正在整理命運結果……")

            data = extract_json(raw_text)

            data = validate_ai_data(data)

            if data is None:
                raise RuntimeError(
                    "AI 回應不是有效 JSON，已啟用安全劇情。"
                )

            # -----------------------------
            # Python 結算
            # -----------------------------

            apply_effects(data)

            update_npcs(
                data.get("npc_updates", [])
            )

            # -----------------------------
            # 任務
            # -----------------------------

            quest_update = data.get(
                "quest_update",
                ""
            ).strip()

            if quest_update:

                game["quests"].append(
                    quest_update
                )

                game["quests"] = game["quests"][-10:]

            # -----------------------------
            # 線索
            # -----------------------------

            clue_update = data.get(
                "clue_update",
                ""
            ).strip()

            if clue_update:

                game["clues"].append(
                    clue_update
                )

                game["clues"] = game["clues"][-15:]

            # -----------------------------
            # 劇情摘要
            # -----------------------------

            summary = data.get(
                "story_summary",
                ""
            ).strip()

            if summary:
                game["story_summary"] = summary

            # -----------------------------
            # 保存歷史
            # -----------------------------

            game["story_history"].append(
                f"👉 你選擇了：{player_action}"
            )

            game["story_history"].append(
                data["story"]
            )

            # 避免瀏覽器頁面越來越長
            if len(game["story_history"]) > 40:
                game["story_history"] = (
                    game["story_history"][-40:]
                )

            game["turn"] += 1

            st.session_state.current_options = (
                data["options"]
            )

            status.update(
                label="✨ 命運已落定",
                state="complete",
                expanded=False,
            )

        except Exception as e:

            # API 失敗也不讓遊戲死掉
            st.write(
                "⚠️ 本回合 AI 暫時沒有正常回應，"
                "已使用安全事件繼續遊戲。"
            )

            data = fallback_turn(
                player_action,
                str(e)
            )

            apply_effects(data)

            if data.get("clue_update"):
                game["clues"].append(
                    data["clue_update"]
                )

            game["story_history"].append(
                f"👉 你選擇了：{player_action}"
            )

            game["story_history"].append(
                data["story"]
            )

            game["turn"] += 1

            st.session_state.current_options = (
                data["options"]
            )

            status.update(
                label="⚠️ AI 暫時繁忙，遊戲仍然繼續",
                state="complete",
                expanded=False,
            )


# =========================================================
# 14. 狀態視窗
# =========================================================

def show_status_message():

    game = st.session_state.game_state
    p = game["player"]

    st.session_state.status_popup = {
        "hp": hp_text(p),
        "mp": mp_text(p),
        "fullness": fullness_text(p),
        "money": p["money"],
        "realm": p["realm"],
        "location": p["location"],
        "status": p["status"],
    }


# =========================================================
# 15. 自訂行動
# =========================================================

def handle_custom_action():

    value = st.session_state.get(
        "custom_input",
        ""
    ).strip()

    if not value:
        return

    process_turn(value)

    st.session_state.custom_input = ""


# =========================================================
# 16. 初始化 Session State
# =========================================================

if "game_started" not in st.session_state:
    st.session_state.game_started = False

if "active_tab" not in st.session_state:
    st.session_state.active_tab = "📖 主線劇情"

if "current_options" not in st.session_state:
    st.session_state.current_options = []

if "status_popup" not in st.session_state:
    st.session_state.status_popup = None


# =========================================================
# 17. 標題
# =========================================================

st.title("🌸 三界奇譚：小薯逆襲記")
st.caption(
    "V3 · OpenRouter · NVIDIA Nemotron 3 Ultra"
)


# =========================================================
# 18. 開局頁
# =========================================================

if not st.session_state.game_started:

    st.subheader("🎲 踏入命途")

    st.write(
        "你將從三界最底層開始。"
        "沒有背景、沒有靠山、只有五文錢。"
    )

    with st.form("start_game_form"):

        input_name = st.text_input(
            "請輸入你的名字：",
            value="詩柔",
        )

        submit_btn = st.form_submit_button(
            "🎲 開啟逆襲人生",
            use_container_width=True,
        )

        if submit_btn:

            init_game(input_name)

            st.rerun()

    st.markdown("---")

    st.subheader("💾 讀取舊存檔")

    load_code = st.text_area(
        "貼上你的存檔代碼：",
        key="initial_load_code",
        height=180,
    )

    if st.button(
        "📂 讀取存檔",
        use_container_width=True,
    ):

        if not load_code.strip():

            st.warning("請先貼上存檔代碼。")

        else:

            try:

                loaded = json.loads(
                    load_code.strip()
                )

                game_state = loaded.get(
                    "game_state"
                )

                if not isinstance(
                    game_state,
                    dict
                ):
                    raise ValueError()

                st.session_state.game_state = (
                    game_state
                )

                st.session_state.current_options = (
                    loaded.get(
                        "current_options",
                        START_OPTIONS.copy()
                    )
                )

                st.session_state.game_started = True

                st.success(
                    "✨ 存檔讀取成功！"
                )

                st.rerun()

            except Exception:

                st.error(
                    "❌ 存檔格式無效，請確認完整複製。"
                )


# =========================================================
# 19. 遊戲主畫面
# =========================================================

else:

    game = st.session_state.game_state
    p = game["player"]

    # =====================================================
    # Sidebar
    # =====================================================

    with st.sidebar:

        st.header("📌 逆襲導航")

        st.write(
            f"👤 **{p['name']}**"
        )

        st.write(
            f"🏷️ **境界**：{p['realm']}"
        )

        st.write(
            f"📍 **位置**：{p['location']}"
        )

        st.markdown("---")

        col1, col2 = st.columns(2)

        col1.metric(
            "❤️ HP",
            hp_text(p)
        )

        col2.metric(
            "💙 MP",
            mp_text(p)
        )

        col3, col4 = st.columns(2)

        col3.metric(
            "🍚 飽腹",
            fullness_text(p)
        )

        col4.metric(
            "💰 金錢",
            f"{p['money']} 文"
        )

        st.markdown("---")

        with st.expander(
            "📊 詳細屬性",
            expanded=True
        ):

            st.write(
                f"🧠 悟性：{p['comprehension']}"
            )

            st.write(
                f"🎲 福緣：{p['fortune']}"
            )

            st.write(
                f"✨ 魅力：{p['charm']}"
            )

            st.write(
                f"⚖️ 正氣：{p['righteousness']}"
            )

            st.write(
                f"🩸 煞氣：{p['evil_aura']}"
            )

            st.write(
                f"👑 威名：{p['fame']}"
            )

            if p["bloodline_awakened"]:

                st.success(
                    "🔥 身世之謎已覺醒"
                )

                # 只有真正覺醒才顯示
                st.write(
                    p.get(
                        "secret_bloodline",
                        "未知血脈"
                    )
                )

            else:

                st.info(
                    "🔒 身世之謎：尚未覺醒"
                )

        st.markdown("---")

        st.subheader("🗂️ 遊戲頁面")

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
            "📜 任務與線索",
            use_container_width=True
        ):
            st.session_state.active_tab = (
                "📜 任務與線索"
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

        st.markdown("---")

        if st.button(
            "🔄 重開新局",
            use_container_width=True
        ):

            st.session_state.game_started = False
            st.session_state.active_tab = (
                "📖 主線劇情"
            )
            st.session_state.current_options = []

            if "game_state" in st.session_state:
                del st.session_state.game_state

            st.rerun()

    # =====================================================
    # 中央畫面
    # =====================================================

    current_view = st.session_state.active_tab

    # -----------------------------------------------------
    # 主線
    # -----------------------------------------------------

    if current_view == "📖 主線劇情":

        st.subheader(
            f"📖 主線劇情 · 第 {game['turn']} 回合"
        )

        # 狀態提示
        if p["hp"] <= 0:

            st.error(
                "💀 你已經失去生命。"
            )

        elif p["hp"] < 15:

            st.warning(
                "⚠️ 瀕死危機：你的生命值已經極低。"
            )

        if p["fullness"] < 15:

            st.warning(
                "🍚 你已經極度飢餓。每次行動會額外損失生命。"
            )

        # 顯示故事
        for text in game["story_history"]:

            if text.startswith("👉"):

                st.info(text)

            else:

                st.markdown(
                    text.replace(
                        "\n",
                        "\n\n"
                    )
                )

        # 狀態 popup
        if st.session_state.status_popup:

            status = st.session_state.status_popup

            st.info(
                f"""
❤️ 生命：{status['hp']}

💙 靈力：{status['mp']}

🍚 飽腹：{status['fullness']}

💰 金錢：{status['money']} 文

🏷️ 境界：{status['realm']}

📍 位置：{status['location']}

🩸 狀態：{status['status']}
"""
            )

            if st.button(
                "關閉狀態",
                use_container_width=True
            ):

                st.session_state.status_popup = None
                st.rerun()

        st.markdown("---")

        st.write(
            "✨ **請選擇你的行動：**"
        )

        for idx, option in enumerate(
            st.session_state.current_options
        ):

            if st.button(
                option,
                key=(
                    f"option_{game['turn']}_{idx}"
                ),
                use_container_width=True,
            ):

                process_turn(option)

                st.rerun()

        st.markdown("---")

        st.write(
            "💭 **自由意念**"
        )

        st.text_input(
            "你想親自做什麼？",
            key="custom_input",
            placeholder="例如：我假裝整理衣物，同時偷偷觀察那名監工。",
        )

        if st.button(
            "✦ 執行自訂行動",
            use_container_width=True,
        ):

            handle_custom_action()

            st.rerun()

    # -----------------------------------------------------
    # 背包
    # -----------------------------------------------------

    elif current_view == "🎒 我的背包":

        st.subheader("🎒 我的背包")

        inventory = game["inventory"]

        if not inventory:

            st.info(
                "你的背包空空如也。"
            )

        else:

            for item in inventory:

                with st.container():

                    st.markdown(
                        f"### 【{item['name']}】 × {item['count']}"
                    )

                    st.write(
                        item["desc"]
                    )

                    st.markdown("---")

    # -----------------------------------------------------
    # NPC
    # -----------------------------------------------------

    elif current_view == "👥 人物關係":

        st.subheader(
            "👥 三界人物關係"
        )

        npcs = game["npcs"]

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
                    f"🌸 {name}　｜　關係：{npc.get('relationship', '未知')}　｜　好感：{affinity}"
                ):

                    st.write(
                        f"**身份：** {npc.get('identity', '未知')}"
                    )

                    st.write(
                        f"**關係：** {npc.get('relationship', '未知')}"
                    )

                    st.write(
                        f"**重要記憶：** {npc.get('key_memory', '暫無')}"
                    )

    # -----------------------------------------------------
    # 任務與線索
    # -----------------------------------------------------

    elif current_view == "📜 任務與線索":

        st.subheader(
            "📜 任務與線索"
        )

        st.markdown("### 📜 任務")

        if not game["quests"]:

            st.info(
                "目前沒有明確任務。"
            )

        else:

            for i, quest in enumerate(
                game["quests"],
                1
            ):

                st.write(
                    f"**{i}.** {quest}"
                )

        st.markdown("---")

        st.markdown("### 🔍 線索")

        if not game["clues"]:

            st.info(
                "目前尚未發現重要線索。"
            )

        else:

            for i, clue in enumerate(
                game["clues"],
                1
            ):

                st.write(
                    f"**{i}.** {clue}"
                )

        st.markdown("---")

        st.markdown("### 📖 長期劇情摘要")

        st.write(
            game.get(
                "story_summary",
                "暫無"
            )
        )

    # -----------------------------------------------------
    # 存檔
    # -----------------------------------------------------

    elif current_view == "💾 存檔與讀檔":

        st.subheader(
            "💾 存檔與讀檔"
        )

        save_data = {
            "version": "V3",
            "model": MODEL,
            "game_state": game,
            "current_options": (
                st.session_state.current_options
            ),
        }

        save_string = json.dumps(
            save_data,
            ensure_ascii=False,
            separators=(",", ":"),
        )

        st.write(
            "📋 複製下面完整文字保存。"
        )

        st.text_area(
            "你的存檔代碼",
            value=save_string,
            height=250,
            key="save_box",
        )

        st.markdown("---")

        load_code = st.text_area(
            "📥 貼上存檔代碼",
            key="load_game_box",
            height=200,
        )

        if st.button(
            "🔄 載入這個存檔",
            use_container_width=True,
        ):

            if not load_code.strip():

                st.warning(
                    "請先貼上存檔代碼。"
                )

            else:

                try:

                    loaded = json.loads(
                        load_code.strip()
                    )

                    loaded_game = loaded.get(
                        "game_state"
                    )

                    if not isinstance(
                        loaded_game,
                        dict
                    ):
                        raise ValueError()

                    st.session_state.game_state = (
                        loaded_game
                    )

                    st.session_state.current_options = (
                        loaded.get(
                            "current_options",
                            START_OPTIONS.copy()
                        )
                    )

                    st.session_state.active_tab = (
                        "📖 主線劇情"
                    )

                    st.success(
                        "✨ 存檔載入成功！"
                    )

                    st.rerun()

                except Exception:

                    st.error(
                        "❌ 存檔無法載入。"
                        "請確認沒有漏複製任何文字。"
                    )
