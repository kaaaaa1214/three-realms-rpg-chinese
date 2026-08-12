import json
import random
import streamlit as st
from google import genai

# ---------------------------------------------------------
# 1. 頁面設定
# ---------------------------------------------------------
st.set_page_config(
    page_title="三界奇譚：小薯逆襲記",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# 2. 初始化 API Key
# ---------------------------------------------------------
api_key = st.secrets.get("GEMINI_API_KEY", "")

if not api_key:
    st.error("⚠️ 請在 Streamlit Secrets 中設定 GEMINI_API_KEY！")
    st.stop()

client = genai.Client(api_key=api_key)

# ---------------------------------------------------------
# 3. 遊戲開局設定
# ---------------------------------------------------------
if "game_started" not in st.session_state:
    st.session_state.game_started = False

LOCATIONS = [
    {"loc": "凡間·青石鎮落魄流民所", "identity": "街頭乞討的孤苦孤兒", "bg": "父母雙亡，每日為下一頓飯發愁，卻在市井中看盡人情冷暖。"},
    {"loc": "仙界·凌霄外園雜役司", "identity": "九霄雲宮最底層雜役仙侍", "bg": "每天負責打掃仙園落花，是仙界最卑微的小薯。"},
    {"loc": "妖界·萬妖山脈外圍暗谷", "identity": "靈智未開就被放養的半妖奴隸", "bg": "混血身份在妖界備受排擠，只能在強大妖獸的爪下艱難求生。"},
    {"loc": "魔界·黑焰深淵礦區", "identity": "最低賤的魔鐵礦奴工", "bg": "每日承受著魔氣侵蝕與監工皮鞭，過著見不到明天的日子。"},
    {"loc": "靈界·散修坊市散亂破廟", "identity": "擺地攤維生的底層落魄散修", "bg": "靈根低下，功法殘缺，經常被強買強賣的修仙家族欺壓。"}
]

SECRET_BLOODLINES = [
    "鳳凰涅槃血脈（未覺醒：體內隱隱有金黑色涅槃火光流轉）",
    "鴻蒙神魔同體印（未覺醒：左眼偶爾閃過魔氣，右眼透出仙光）",
    "太古星辰帝君遺脈（封印中：眉心隱藏著一枚殘破的星辰印記）",
    "九幽妖皇真靈寄宿（沉睡中：胸口處生有一枚古老的上古妖聖紋）"
]

SPECIAL_ITEMS = [
    {"name": "殘破玉佩", "count": 1, "desc": "從小隨身帶著的殘破玉佩，散發著微弱的古老氣息。"},
    {"name": "無字天書殘頁", "count": 1, "desc": "在廢墟中撿到的古舊紙頁，隱隱有文字流轉。"},
    {"name": "鏽蝕鐵劍", "count": 1, "desc": "看似一把普通廢鐵劍，卻能在深夜發出陣陣異響。"},
    {"name": "神秘獸牙", "count": 1, "desc": "散發著淡淡野性威壓的遠古獸牙佩飾。"}
]

def init_game(player_name):
    loc_info = random.choice(LOCATIONS)
    secret_bloodline = random.choice(SECRET_BLOODLINES)
    special_item = random.choice(SPECIAL_ITEMS)
    
    st.session_state.game_state = {
        "player": {
            "name": player_name if player_name.strip() else "詩柔",
            "identity": f"{loc_info['loc']}·{loc_info['identity']}",
            "secret_bloodline": secret_bloodline,
            "hp": "100/100",
            "mp": "30/30",
            "fullness": "90/100",
            "realm": "凡俗之軀 / 煉氣期一層",
            "location": loc_info['loc'],
            "status": "健康（平靜）",
            "comprehension": random.randint(8, 12),
            "fortune": random.randint(8, 12),
            "charm": random.randint(8, 12),
            "righteousness": 0,
            "evil_aura": 0,
            "fame": 0
        },
        "inventory": [
            {"name": "粗布麻衣", "count": 1, "desc": "極為普通的日常衣物。"},
            {"name": "乾糧清水", "count": 2, "desc": "填飽肚子的普通補給。"},
            special_item
        ],
        "npcs": {},
        "story_history": [
            f"【命運開啟】\n你睜開眼睛，發現自己正身處在**{loc_info['loc']}**。\n"
            f"你是【{player_name}】，目前只是一個平凡的{loc_info['identity']}（{loc_info['bg']}）。\n"
            f"茫茫三界，弱肉強食，屬於你的小薯逆襲之路正式展開……"
        ],
        "story_summary": "遊戲剛開局，主角正處於命運起點。"
    }
    st.session_state.current_options = [
        "1 既沒有立刻搭話，也沒有亂動，而是冷眼旁觀周圍的動靜。",
        f"2 沒有急著回應周遭變故，目光落在那件【{special_item['name']}】上片刻。",
        "3 微微挑眉，語氣平淡卻帶著一絲不容置疑：「與其在這裡盲目耗著……」",
        "4 沒有將心思放在眼前的困境上，反而若有所思地環顧四周。"
    ]
    st.session_state.game_started = True

SYSTEM_INSTRUCTION = """
你是一個高品質且節奏明快的【三界跨界 RPG 遊戲主持人（GM）】。
每次必須生成 4 個不同的行動選項（以 1, 2, 3, 4 開頭）。
必須嚴格回傳標準純 JSON（絕對不要包覆在 markdown ```json 裡面，直接給純字串）：
{
  "story": "詳細精彩的劇情演繹（250字以內）。",
  "story_summary_update": "80字以內的精簡歷史摘要。",
  "options": [
    "1 選項一...",
    "2 選項二...",
    "3 選項三...",
    "4 選項四..."
  ],
  "player_update": {
    "identity": "身份描述", "hp": "100/100", "mp": "30/30", "fullness": "85/100",
    "realm": "境界", "location": "地點", "status": "狀態",
    "comprehension": 10, "fortune": 10, "charm": 10,
    "righteousness": 0, "evil_aura": 0, "fame": 0
  },
  "inventory_update": [{"name": "物品名", "count": 1, "desc": "說明"}],
  "npc_updates": []
}
"""

def process_turn(player_action):
    game_state = st.session_state.game_state
    recent_history = game_state["story_history"][-4:]
    
    prompt = f"{SYSTEM_INSTRUCTION}\n\n"
    prompt += f"【摘要】：{game_state.get('story_summary', '無')}\n"
    prompt += f"【近期劇情】：{json.dumps(recent_history, ensure_ascii=False)}\n"
    prompt += f"【狀態】：{json.dumps(game_state['player'], ensure_ascii=False)}\n"
    prompt += f"【玩家最新行動】：{player_action}\n"
    prompt += "請嚴格回傳純 JSON。"

    # 直接使用 st.status 確保進度條與轉圈圈穩定顯示
    with st.status("🔮 命運齒輪轉動中，AI 正在生成劇情...", expanded=True) as status:
        try:
            st.write("正在呼叫 Gemini-2.0-flash 模型...")
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )
            raw_text = response.text
            st.write("資料解析中...")
            
            clean_text = raw_text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_text)

            game_state["player"].update(data.get("player_update", {}))
            if "inventory_update" in data:
                game_state["inventory"] = [i for i in data["inventory_update"] if i.get("count", 0) > 0]
            if "story_summary_update" in data:
                game_state["story_summary"] = data["story_summary_update"]

            game_state["story_history"].append(f"👉 **你選擇了**：{player_action}")
            game_state["story_history"].append(data["story"])
            st.session_state.current_options = data.get("options", [
                "1 繼續冷靜觀察四周。",
                "2 嘗試開口詢問身旁的人。",
                "3 悄悄檢查身上的隨身物品。",
                "4 找個安全的地方暫避風頭。"
            ])
            status.update(label="✨ 劇情生成完畢！", state="complete", expanded=False)
        except Exception as e:
            status.update(label="❌ 生成失敗", state="error", expanded=True)
            st.error(f"錯誤詳情：\n{str(e)}")

# ---------------------------------------------------------
# 4. 介面呈現
# ---------------------------------------------------------
st.title("🌸 三界奇譚：小薯逆襲記")

if not st.session_state.game_started:
    st.subheader("🎲 踏入命途 (隨機三界背景開局)")
    with st.form("start_game_form"):
        input_name = st.text_input("請輸入你的名字：", value="詩柔")
        submit_btn = st.form_submit_button("🎲 開啟逆襲人生 🚀", use_container_width=True)
        if submit_btn:
            init_game(input_name)
            st.rerun()
else:
    with st.sidebar:
        st.header("📌 狀態與導航")
        p = st.session_state.game_state["player"]
        st.write(f"👤 **{p['name']}**")
        st.write(f"🏷️ 境界：{p['realm']}")
        st.write(f"📍 位置：{p['location']}")
        
        col1, col2 = st.columns(2)
        col1.metric("❤️ HP", p["hp"])
        col2.metric("💙 MP", p["mp"])
        
        if st.button("🎲 重開新局", use_container_width=True):
            st.session_state.game_started = False
            st.rerun()

    st.subheader("📖 主線劇情與冒險")
    for text in st.session_state.game_state["story_history"]:
        if text.startswith("👉"):
            st.info(text)
        else:
            st.write(text)

    st.markdown("---")
    st.write("✨ **請選擇你的行動：**")
    
    # 使用獨立且帶有亂數/序號防衝突的 key
    for idx, opt in enumerate(st.session_state.current_options):
        if st.button(opt, key=f"unique_opt_key_{idx}_{len(st.session_state.game_state['story_history'])}", use_container_width=True):
            process_turn(opt)
            st.rerun()

    st.markdown("---")
    custom_act = st.text_input("💬 自由意念輸入：", key="custom_input_box")
    if st.button("發送自訂行動", use_container_width=True):
        if custom_act.strip():
            process_turn(custom_act.strip())
            st.rerun()
