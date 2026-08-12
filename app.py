import json
import random
import streamlit as st
from google import genai
from google.genai import types

# ---------------------------------------------------------
# 1. 頁面設定 (適合手機瀏覽)
# ---------------------------------------------------------
st.set_page_config(
    page_title="三界奇譚：仙界小薯逆襲記",
    page_icon="🌸",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ---------------------------------------------------------
# 2. 初始化 Gemini API Key (從 Streamlit Secrets 讀取)
# ---------------------------------------------------------
api_key = st.secrets.get("GEMINI_API_KEY", "")

if not api_key:
    st.error("⚠️ 請在 Streamlit Secrets 中設定 GEMINI_API_KEY！")
    st.stop()

# 建立 Client 物件
client = genai.Client(api_key=api_key)

# ---------------------------------------------------------
# 3. 隨機開局庫與初始化遊戲狀態
# ---------------------------------------------------------
if "game_started" not in st.session_state:
    st.session_state.game_started = False

LOCATIONS = [
    {"loc": "仙界·凌霄外園雜役司", "identity": "九霄雲宮雜役仙侍", "bg": "每天負責打掃仙園落花，是仙界最底層的小薯。"},
    {"loc": "仙界·洗髓池畔殘垣", "identity": "無依無靠的洗髓池棄兒", "bg": "從小被拋棄在仙界洗髓池邊，靠撿拾廢棄仙草長大。"},
    {"loc": "仙界·荒古藥園角落", "identity": "藥王谷看守藥童", "bg": "每天負責照料珍稀仙草，經常被仙官差遣打雜。"},
    {"loc": "仙界·神兵鍛造坊後山", "identity": "打鐵小工奴侍", "bg": "在仙界鍛造坊幹粗活，整天與仙火碎石打交道。"}
]

SECRET_BLOODLINES = [
    "鳳凰涅槃血脈（未覺醒：體內隱隱有金黑色涅槃火光流轉）",
    "鴻蒙神魔同體印（未覺醒：左眼偶爾閃過魔氣，右眼透出仙光）",
    "太古星辰仙帝遺脈（封印中：眉心隱藏著一枚殘破的星辰印記）",
    "九幽妖皇真靈寄宿（沉睡中：胸口處生有一枚古老的妖族聖紋）"
]

SPECIAL_ITEMS = [
    {"name": "殘破玉佩", "count": 1, "desc": "從小隨身攜帶的殘破玉佩，散發著微弱的古老氣息。"},
    {"name": "無字天書殘頁", "count": 1, "desc": "在廢墟中撿到的古舊紙頁，隱隱有文字流轉。"},
    {"name": "鏽蝕仙劍", "count": 1, "desc": "看似一把普通廢鐵劍，卻能在深夜發出陣陣劍鳴。"},
    {"name": "神秘獸牙", "count": 1, "desc": "散發著淡淡野性威壓的獸牙佩飾。"}
]

def init_game(player_name):
    loc_info = random.choice(LOCATIONS)
    secret_bloodline = random.choice(SECRET_BLOODLINES)
    special_item = random.choice(SPECIAL_ITEMS)
    
    comprehension = random.randint(8, 12)
    fortune = random.randint(8, 12)
    charm = random.randint(8, 12)

    st.session_state.game_state = {
        "player": {
            "name": player_name if player_name.strip() else "詩柔",
            "identity": f"{loc_info['loc']}·{loc_info['identity']}",
            "secret_bloodline": secret_bloodline,
            "hp": "100/100",
            "mp": "30/30",
            "fullness": "90/100",
            "realm": "微末小仙 / 煉氣初期",
            "location": loc_info['loc'],
            "status": "健康（平靜）",
            "comprehension": comprehension,
            "fortune": fortune,
            "charm": charm,
            "righteousness": 0,
            "evil_aura": 0,
            "fame": 0
        },
        "inventory": [
            {"name": "掃靈帚", "count": 1, "desc": "打掃或幹雜活用的普通工具。"},
            {"name": "下品仙露", "count": 2, "desc": "仙界最普通的飲品，補充 20 點飽腹度與少量靈力。"},
            special_item
        ],
        "npcs": {},
        "story_history": [
            f"【仙途開啟】\n你睜開眼睛，發現自己正身處在**{loc_info['loc']}**。\n"
            f"你是【{player_name}】，目前只是一個平凡的{loc_info['identity']}（{loc_info['bg']}）。\n"
            f"浩瀚三界，無窮玄秘，屬於你的逆襲仙途正式展開……"
        ]
    }
    st.session_state.current_options = [
        "🧹 踏實幹活：開始做今天的日常雜務",
        f"🔍 仔細端詳：拿出背包裡的【{special_item['name']}】認真研究",
        "👀 四處探索：觀察周圍環境，看看有沒有值得注意的事物",
        "🧘 靜心打坐：嘗試運轉呼吸吐納，感受天地間微弱的靈氣",
        "💬 試探互動：向身邊路過的其他仙官或雜役打招呼套近乎"
    ]
    st.session_state.game_started = True

SYSTEM_INSTRUCTION = """
你是一個高品質的【仙俠 RPG 遊戲主持人（GM）】。

【玩家背景與隱藏設定】：
- 玩家開局是一個普通底層小薯。
- 玩家有一個隱藏身世/血脈記錄在 `secret_bloodline` 中。
- ⚠️ **重要規則**：切勿在剛開局就直接公開或說明隱藏身世！必須隨著劇情推進、遭遇奇遇、危急時刻或修為突破時，才通過細節描寫（如異象、神秘感應）逐步引導覺醒。

【🎯 選項生成規則】：
- 每次必須生成 **4 到 5 個** 不同的行動選項。
- 選項必須涵蓋多種不同類型（穩健日常、冒險探索、社交互動、智取機敏、出人意料嘗試）。
- 請在每個選項前加上合適的 Emoji 標情符號（如 🗡️, 📜, 🌸, 🧘, 🎒）。

【NPC 與關係系統】：
- 初始 NPC 列表為空。
- 當玩家在劇情中遇到新人物（如同伴、朋友、前輩、師長、敵人或潛在對象）時，才將其加入 `npc_updates`。
- `affinity` 為好感/敬意值（0-100）。`relationship` 應準確反映當前關係，讓關係自然發展。

【輸出格式規則】：
必須嚴格回傳標準 JSON（切勿包含任何多餘文字）：
{
  "story": "詳細劇情演繹（250字以內），文筆生動流暢，注重氛圍感。",
  "options": ["選項1", "選項2", "選項3", "選項4", "選項5"],
  "player_update": {
    "identity": "身份描述",
    "hp": "100/100",
    "mp": "30/30",
    "fullness": "85/100",
    "realm": "當前境界",
    "location": "當前地點",
    "status": "當前狀態",
    "comprehension": 10,
    "fortune": 10,
    "charm": 10,
    "righteousness": 0,
    "evil_aura": 0,
    "fame": 0
  },
  "inventory_update": [
    {"name": "物品名", "count": 1, "desc": "說明"}
  ],
  "npc_updates": [
    {
      "name": "角色名稱",
      "identity": "身份背景",
      "affinity": 10,
      "relationship": "關係狀態",
      "key_memory": "互動印象摘要"
    }
  ]
}
"""

# ---------------------------------------------------------
# 4. 遊戲核心邏輯 (使用 gemini-2.0-flash)
# ---------------------------------------------------------
def process_turn(player_action):
    game_state = st.session_state.game_state
    
    prompt = f"當前主角狀態：{json.dumps(game_state['player'], ensure_ascii=False)}\n"
    prompt += f"當前背包：{json.dumps(game_state['inventory'], ensure_ascii=False)}\n"
    prompt += f"當前已結識人物：{json.dumps(game_state['npcs'], ensure_ascii=False)}\n"
    prompt += f"玩家採取的行動：{player_action}\n"
    prompt += "請回傳 JSON 劇情演繹與數據更新。"

    with st.spinner("🔮 AI 正在演繹仙途劇情，請稍候..."):
        try:
            # 指定 gemini-2.0-flash 模型
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json"
                )
            )
            
            clean_text = response.text.replace("```json", "").replace("
