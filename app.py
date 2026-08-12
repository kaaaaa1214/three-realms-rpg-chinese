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
# 4. 遊戲核心邏輯
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
            # 這裡已修正為正確的模型名稱 gemini-2.5-flash
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json"
                )
            )
            
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_text)

            # 更新玩家狀態
            game_state["player"].update(data.get("player_update", {}))
            
            # 更新背包
            if "inventory_update" in data:
                game_state["inventory"] = [i for i in data["inventory_update"] if i.get("count", 0) > 0]

            # 更新或新增 NPC
            for npc in data.get("npc_updates", []):
                game_state["npcs"][npc["name"]] = npc

            # 紀錄歷史
            game_state["story_history"].append(f"👉 **你選擇了**：{player_action}")
            game_state["story_history"].append(data["story"])
            st.session_state.current_options = data.get("options", [])

        except Exception as e:
            st.error(f"劇情生成失敗，請再按一次選項試試看！錯誤原因：{str(e)}")

# ---------------------------------------------------------
# 5. UI 介面
# ---------------------------------------------------------
st.title("🌸 三界奇譚：仙界小薯逆襲記")

if not st.session_state.game_started:
    st.subheader("🎲 踏入仙途 (隨機命格開局)")
    
    with st.form("start_game_form"):
        input_name = st.text_input("請輸入你在仙界的名字：", value="詩柔")
        submit_btn = st.form_submit_button("🎲 開啟新人生 🚀", use_container_width=True)
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
    col_title, col_reset = st.columns([3, 1])
    with col_reset:
        if st.button("🎲 重開新局", use_container_width=True):
            st.session_state.game_started = False
            st.rerun()

    tab_story, tab_status, tab_inv, tab_romance, tab_save = st.tabs(["📖 劇情", "👤 狀態", "🎒 背包", "👥 三界人物", "💾 存檔/讀檔"])

    # --- 頁籤 1：主線劇情 ---
    with tab_story:
        for text in st.session_state.game_state["story_history"]:
            if text.startswith("👉"):
                st.info(text)
            else:
                st.write(text)

        st.markdown("---")
        st.write("✨ **請選擇你的行動：**")
        
        for idx, opt in enumerate(st.session_state.current_options):
            if st.button(opt, key=f"opt_{idx}", use_container_width=True):
                process_turn(opt)
                st.rerun()

        st.markdown("---")
        custom_act = st.text_input("💬 自由意念（例：嘗試觀察四周 / 打開背包檢查物品）：", key="custom_input")
        if st.button("發送自訂行動", use_container_width=True):
            if custom_act.strip():
                process_turn(custom_act.strip())
                st.rerun()

    # --- 頁籤 2：主角狀態 ---
    with tab_status:
        p = st.session_state.game_state["player"]
        st.subheader(f"👤 {p['name']}")
        st.write(f"**身份**：{p['identity']}")
        st.write(f"**當前境界**：{p['realm']}")
        st.write(f"**當前位置**：📍 {p['location']}")
        st.write(f"**狀態**：{p['status']}")
        
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

    # --- 頁籤 4：三界人物誌 ---
    with tab_romance:
        st.subheader("👥 三界人物誌")
        npcs = st.session_state.game_state["npcs"]
        if not npcs:
            st.info("目前尚未結識任何仙魔角色、師長或同伴。漫漫仙途，等待你的探索！")
        else:
            for name, info in npcs.items():
                with st.expander(f"🌸 {name}（好感/敬意：{info['affinity']}）", expanded=True):
                    st.write(f"**身份**：{info['identity']}")
                    st.write(f"**關係**：🤝 {info['relationship']}")
                    st.write(f"**印象關鍵**：{info['key_memory']}")

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
