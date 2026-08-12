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

client = genai.Client(api_key=api_key)

# ---------------------------------------------------------
# 3. 隨機開局庫與初始化遊戲狀態
# ---------------------------------------------------------
if "game_started" not in st.session_state:
    st.session_state.game_started = False

# 隨機池設定
LOCATIONS = [
    {"loc": "仙界·凌霄外園雜役司", "identity": "九霄雲宮雜役仙侍", "bg": "每天負責打掃仙園落花，是仙界最底層的小薯。"},
    {"loc": "仙界·洗髓池畔殘垣", "identity": "無依無靠的洗髓池棄兒", "bg": "從小被拋棄在仙界洗髓池邊，靠撿拾廢棄仙草長大。"},
    {"loc": "仙界·荒古藥園角落", "identity": "藥王谷看守藥童", "bg": "每天負責照料珍稀仙草，經常被仙官差遣打雜。"},
    {"loc": "仙界·神兵鍛造坊後山", "identity": "打鐵小工奴侍", "bg": "在仙界鍛造坊幹粗活，整天與仙火碎石打交道。"}
]

BLOODLINES = [
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
    bloodline = random.choice(BLOODLINES)
    special_item = random.choice(SPECIAL_ITEMS)
    
    # 隨機微調初始屬性
    comprehension = random.randint(8, 12)
    fortune = random.randint(8, 12)
    charm = random.randint(8, 12)

    st.session_state.game_state = {
        "player": {
            "name": player_name if player_name.strip() else "詩柔",
            "identity": f"{loc_info['loc']}·{loc_info['identity']}",
            "bloodline": bloodline,
            "hp": "100/100",
            "mp": "30/30",
            "fullness": "90/100",
            "realm": "微末小仙 / 煉氣初期",
            "location": loc_info['loc'],
            "status": "健康（略感疲憊）",
            "comprehension": comprehension, # 悟性
            "fortune": fortune,             # 福緣
            "charm": charm,                 # 魅力
            "righteousness": 10,            # 正氣
            "evil_aura": 0,                 # 煞氣
            "fame": 1                       # 威名
        },
        "inventory": [
            {"name": "掃靈帚", "count": 1, "desc": "打掃或幹雜活用的普通工具。"},
            {"name": "下品仙露", "count": 2, "desc": "仙界最普通的飲品，補充 20 點飽腹度與少量靈力。"},
            special_item
        ],
        "npcs": {
            "清虛仙尊·墨白": {
                "identity": "仙界第一劍尊 / 高冷禁慾",
                "affinity": 15,
                "relationship": "遙不可及的雲端仙尊（對你有一絲微弱的既視感）",
                "key_memory": "曾在遠處遠遠看過你一眼，眼神似乎停頓了片刻。"
            }
        },
        "story_history": [
            f"【開局隨機生成成功！】\n你睜開眼睛，發現自己正身處在**{loc_info['loc']}**。\n"
            f"雖然你只是個名叫【{player_name}】的仙界小薯（{loc_info['bg']}），"
            f"但你不知道的是，你的體內竟隱藏著【{bloodline}】！命運的齒輪已開始轉動……"
        ]
    }
    st.session_state.current_options = [
        "認命開始做今天的雜務工作",
        f"悄悄研究背包裡的【{special_item['name']}】",
        "環顧四周，看看有沒有什麼奇遇或可疑的人"
    ]
    st.session_state.game_started = True

SYSTEM_INSTRUCTION = """
你是一個高品質的【仙俠 RPG 遊戲主持人（GM）】，擅長豐富的情感細節與細膩的情愛動態。

【玩家背景設定】：
- 玩家表面上是仙界最底層的仙界小薯，但每次開局都有獨特的隨機地點與隱藏身世/血脈。
- 請根據玩家目前的 `location`（地點）與 `bloodline`（血脈）演繹專屬劇情，並適時埋下關於「身世覺醒」的伏筆與線索。

【💖 感情與好感度系統】：
- 玩家會遇到各種不同魅力的角色（如高冷仙尊、腹黑魔君、傲嬌妖皇、溫柔師兄等）。
- 每次互動若涉及情感動向，請在 `npc_updates` 中更新好感度（affinity, 0-100+）與關係描述（relationship，如：萍水相逢、暗生情愫、曖昧期、情根深種、生死相許）。
- 劇情文字要寫得出情感拉扯、甜虐細節與沉浸感！

【輸出格式規則】：
必須嚴格回傳標準 JSON（切勿包含任何多餘文字）：
{
  "story": "詳細劇情演繹（250字以內），文筆唯美有沉浸感，包含心動或冒險細節。",
  "options": ["選項1", "選項2", "選項3"],
  "player_update": {
    "identity": "身份描述",
    "bloodline": "身世/血脈狀態",
    "hp": "100/100",
    "mp": "30/30",
    "fullness": "85/100",
    "realm": "當前境界",
    "location": "當前地點",
    "status": "當前狀態",
    "comprehension": 9,
    "fortune": 8,
    "charm": 10,
    "righteousness": 10,
    "evil_aura": 0,
    "fame": 1
  },
  "inventory_update": [
    {"name": "物品名", "count": 1, "desc": "說明"}
  ],
  "npc_updates": [
    {
      "name": "角色名稱",
      "identity": "身份背景",
      "affinity": 25,
      "relationship": "情感關係狀態",
      "key_memory": "重要情感記憶/互動摘要"
    }
  ]
}
"""

# ---------------------------------------------------------
# 4. 遊戲核心邏輯
# ---------------------------------------------------------
def process_turn(player_action):
    game_state = st.session_state.game_state
    
    prompt = f"當前主角狀態：{json.dumps(game_state['player'], ensure_ascii=False)}\n"
    prompt += f"當前背包：{json.dumps(game_state['inventory'], ensure_ascii=False)}\n"
    prompt += f"當前人物好感與關係：{json.dumps(game_state['npcs'], ensure_ascii=False)}\n"
    prompt += f"玩家採取的行動：{player_action}\n"
    prompt += "請回傳 JSON 劇情演繹與數據更新。"

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json"
            )
        )
        data = json.loads(response.text)

        # 更新狀態
        game_state["player"].update(data.get("player_update", {}))
        
        if "inventory_update" in data:
            game_state["inventory"] = [i for i in data["inventory_update"] if i.get("count", 0) > 0]

        for npc in data.get("npc_updates", []):
            game_state["npcs"][npc["name"]] = npc

        # 紀錄歷史
        game_state["story_history"].append(f"👉 **你選擇了**：{player_action}")
        game_state["story_history"].append(data["story"])
        st.session_state.current_options = data.get("options", [])

    except Exception as e:
        st.error(f"劇情生成失敗：{str(e)}")

# ---------------------------------------------------------
# 5. UI 介面（隨機開局 + 手機優化 + 存檔功能）
# ---------------------------------------------------------
st.title("🌸 三界奇譚：仙界小薯逆襲記")

if not st.session_state.game_started:
    st.subheader("🎲 踏入仙途 (隨機命格開局)")
    
    with st.form("start_game_form"):
        input_name = st.text_input("請輸入你在仙界的名字：", value="詩柔")
        submit_btn = st.form_submit_button("🎲 抽取命格，開啟新人生 🚀", use_container_width=True)
        if submit_btn:
            init_game(input_name)
            st.rerun()

    st.markdown("---")
    st.subheader("💾 讀取舊存檔")
    load_code = st.text_area("請貼上你的存檔代碼：", key="init_load_code")
    if st.button("讀取存檔進度 📂", use_container_width=True):
        if load_code.strip():
            try:
                loaded_data = json.loads(load_code.strip())
                st.session_state.game_state = loaded_data.get("game_state", {})
                st.session_state.current_options = loaded_data.get("current_options", [])
                st.session_state.game_started = True
                st.success("讀取存檔成功！")
                st.rerun()
            except Exception as err:
                st.error("存檔代碼無效，請檢查是否複製完整！")
        else:
            st.warning("請先輸入存檔代碼！")

else:
    # 頂部快捷選單：重開新遊戲
    col_title, col_reset = st.columns([3, 1])
    with col_reset:
        if st.button("🎲 重開新局", use_container_width=True):
            st.session_state.game_started = False
            st.rerun()

    tab_story, tab_status, tab_inv, tab_romance, tab_save = st.tabs(["📖 劇情", "👤 狀態", "🎒 背包", "💖 姻緣好感", "💾 存檔/讀檔"])

    # --- 頁籤 1：主線劇情 ---
    with tab_story:
        for text in st.session_state.game_state["story_history"]:
            if text.startswith("👉"):
                st.info(text)
            else:
                st.write(text)

        st.markdown("---")
        st.write("✨ **請選擇你的行動：**")
        for opt in st.session_state.current_options:
            if st.button(opt, key=opt, use_container_width=True):
                process_turn(opt)
                st.rerun()

        st.markdown("---")
        custom_act = st.text_input("💬 自由意念（例：嘗試觀察四周 / 打開背包檢查物品）：")
        if st.button("發送自訂行動", use_container_width=True):
            if custom_act.strip():
                process_turn(custom_act.strip())
                st.rerun()

    # --- 頁籤 2：主角狀態與身世 ---
    with tab_status:
        p = st.session_state.game_state["player"]
        st.subheader(f"👤 {p['name']}")
        st.write(f"**身份**：{p['identity']}")
        st.write(f"**隱藏血脈**：{p['bloodline']}")
        st.write(f"**當前境界**：{p['realm']}")
        st.write(f"**當前位置**：📍 {p['location']}")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("❤️ HP", p["hp"])
        col2.metric("💙 MP", p["mp"])
        col3.metric("🍚 飽腹", p["fullness"])

        st.markdown("---")
        st.write(f"🧠 **悟性**：{p['comprehension']} | 🎲 **福緣**：{p['fortune']} | ✨ **魅力**：{p['charm']}")
        st.write(f"⚖️ **正氣**：{p['righteousness']} | 🩸 **煞氣**：{p['evil_aura']} | 👑 **威名**：{p['fame']}")

    # --- 頁籤 3：背包物品 ---
    with tab_inv:
        st.subheader("🎒 我的背包")
        inv = st.session_state.game_state["inventory"]
        if not inv:
            st.write("背包空空如也。")
        else:
            for item in inv:
                st.success(f"**【{item['name']}】 x {item['count']}**\n\n說明：{item['desc']}")

    # --- 頁籤 4：姻緣與好感度 ---
    with tab_romance:
        st.subheader("💖 三界人物誌與好感度")
        npcs = st.session_state.game_state["npcs"]
        if not npcs:
            st.write("目前尚未結交任何仙魔角色。")
        else:
            for name, info in npcs.items():
                with st.expander(f"🌸 {name}（好感度：{info['affinity']}）", expanded=True):
                    st.write(f"**身份**：{info['identity']}")
                    st.write(f"**情感狀態**：💕 {info['relationship']}")
                    st.write(f"**心動記憶**：{info['key_memory']}")

    # --- 頁籤 5：存檔與讀檔 ---
    with tab_save:
        st.subheader("💾 遊戲存檔與讀檔")
        st.info("💡 只要將「存檔代碼」複製並儲存在手機備忘錄裡，下次重新開啟遊戲時貼上即可繼續進度！")
        
        save_data = {
            "game_state": st.session_state.game_state,
            "current_options": st.session_state.current_options
        }
        save_string = json.dumps(save_data, ensure_ascii=False)
        
        st.write("📋 **你的當前存檔代碼：**")
        st.code(save_string, language="text")
        
        st.markdown("---")
        st.write("📥 **讀取新存檔：**")
        in_load_code = st.text_area("請貼上存檔代碼：", key="in_game_load_code")
        if st.button("載入此存檔 🔄", use_container_width=True):
            if in_load_code.strip():
                try:
                    loaded = json.loads(in_load_code.strip())
                    st.session_state.game_state = loaded.get("game_state", {})
                    st.session_state.current_options = loaded.get("current_options", [])
                    st.success("存檔載入成功！")
                    st.rerun()
                except Exception as err:
                    st.error("存檔代碼無效，請確認格式是否正確！")
            else:
                st.warning("請先輸入存檔代碼！")
