import json
import random
import streamlit as st
from google import genai

# ---------------------------------------------------------
# 1. 頁面設定 (支援手機與寬螢幕佈局)
# ---------------------------------------------------------
st.set_page_config(
    page_title="三界奇譚：小薯逆襲記",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="expanded"
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
# 3. 三界多元開局庫
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
    {"name": "殘破玉佩", "count": 1, "desc": "從小隨身攜帶的殘破玉佩，散發著微弱的古老氣息。"},
    {"name": "無字天書殘頁", "count": 1, "desc": "在廢墟中撿到的古舊紙頁，隱隱有文字流轉。"},
    {"name": "鏽蝕鐵劍", "count": 1, "desc": "看似一把普通廢鐵劍，卻能在深夜發出陣陣異響。"},
    {"name": "神秘獸牙", "count": 1, "desc": "散發著淡淡野性威壓的遠古獸牙佩飾。"}
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
            "realm": "凡俗之軀 / 煉氣期一層",
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
            {"name": "粗布麻衣", "count": 1, "desc": "極為普通的日常衣物。"},
            {"name": "乾糧清水", "count": 2, "desc": "填飽肚子的普通補給，補充少量飽腹度。"},
            special_item
        ],
        "npcs": {},
        "story_history": [
            f"【命運開啟】\n你睜開眼睛，發現自己正身處在**{loc_info['loc']}**。\n"
            f"你是【{player_name}】，目前只是一個平凡的{loc_info['identity']}（{loc_info['bg']}）。\n"
            f"茫茫三界，弱肉強食，屬於你的小薯逆襲之路正式展開……"
        ],
        "story_summary": "遊戲剛開局，主角正處於命運起點，尚未經歷重大事件。"
    }
    st.session_state.current_options = [
        "1 既沒有立刻搭話，也沒有亂動，而是冷眼旁觀周圍的動靜，試圖從中找出對自己最有利的破局契機。",
        f"2 沒有急著回應周遭的變故，目光落在那件【{special_item['name']}】上片刻，忽然開口試探：「這東西……究竟藏著什麼秘密？」",
        "3 微微挑眉，語氣平淡卻帶著一絲不容置疑：「與其在這裡盲目耗著，不如先弄清楚這裡究竟是什麼地方，誰才是真正話事的人。」",
        "4 沒有將心思放在眼前的困境上，反而若有所思地環顧四周：「這地方看似平靜，恐怕暗地裡早已經危機四伏了，我們得先換個應對策略。」"
    ]
    st.session_state.game_started = True

SYSTEM_INSTRUCTION = """
你是一個高品質且節奏明快的【三界跨界 RPG 遊戲主持人（GM）】。

【玩家背景與隱藏設定】：
- 玩家開局是一個普通底層小薯。
- 玩家有一個隱藏身世/血脈記錄在 `secret_bloodline` 中（切勿過早直接公開，需透過劇情漸進覺醒）。

【🎯 選項生成核心規則（極度重要）】：
- 每次必須生成 4 個不同的行動選項。
- **選項風格必須模仿高級武俠/仙俠小說的沉浸式對白與心態描寫**。
- 每個選項開頭必須是數字編號（如 `1`, `2`, `3`, `4`）。

【輸出格式規則】：
必須嚴格回傳標準 JSON（切勿包含任何額外文字或 markdown 程式碼區塊標記，直接回傳純 JSON 字串）：
{
  "story": "詳細精彩的劇情演繹（250字以內），文筆生動，推進劇情。",
  "story_summary_update": "請把『過往劇情摘要』與『本次最新發生的關鍵劇情』融合，更新成一段 80 字以內的精簡歷史摘要。",
  "options": [
    "1 具體且充滿張力的選項描述...",
    "2 具體且充滿張力的選項描述...",
    "3 具體且充滿張力的選項描述...",
    "4 具體且充滿張力的選項描述..."
  ],
  "player_update": {
    "identity": "身份描述", "hp": "100/100", "mp": "30/30", "fullness": "85/100",
    "realm": "當前境界", "location": "當前地點", "status": "當前狀態",
    "comprehension": 10, "fortune": 10, "charm": 10,
    "righteousness": 0, "evil_aura": 0, "fame": 0
  },
  "inventory_update": [
    {"name": "物品名", "count": 1, "desc": "說明"}
  ],
  "npc_updates": [
    {
      "name": "角色名稱", "identity": "身份背景", "affinity": 10,
      "relationship": "關係狀態", "key_memory": "互動印象摘要"
    }
  ]
}
"""

def process_turn(player_action):
    game_state = st.session_state.game_state
    recent_history = game_state["story_history"][-4:]
    
    prompt = f"{SYSTEM_INSTRUCTION}\n\n"
    prompt += f"【過往冒險精華摘要】：{game_state.get('story_summary', '無')}\n"
    prompt += f"【最近幾幕劇情】：{json.dumps(recent_history, ensure_ascii=False)}\n"
    prompt += f"當前主角狀態：{json.dumps(game_state['player'], ensure_ascii=False)}\n"
    prompt += f"當前背包：{json.dumps(game_state['inventory'], ensure_ascii=False)}\n"
    prompt += f"當前已結識人物：{json.dumps(game_state['npcs'], ensure_ascii=False)}\n"
    prompt += f"玩家採取的最新行動：{player_action}\n"
    prompt += "請嚴格回傳純 JSON 格式數據。"

    with st.status("🔮 命運齒輪轉動中，AI 正在生成劇情...", expanded=True) as status:
        try:
            st.write("正在呼叫 Gemini 模型...")
            # 💡 更新為目前穩定支援的 gemini-3.5-flash 模型
            response = client.models.generate_content(
                model='gemini-3.5-flash',
                contents=prompt
            )
            raw_text = response.text
            st.write("資料解析中...")
            
            clean_text = raw_text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_text)

            game_state["player"].update(data.get("player_update", {}))
            
            if "inventory_update" in data:
                game_state["inventory"] = [i for i in data["inventory_update"] if i.get("count", 0) > 0]

            for npc in data.get("npc_updates", []):
                game_state["npcs"][npc["name"]] = npc

            if "story_summary_update" in data:
                game_state["story_summary"] = data["story_summary_update"]

            game_state["story_history"].append(f"👉 **你選擇了**：{player_action}")
            game_state["story_history"].append(data["story"])
            st.session_state.current_options = data.get("options", [
                "1 繼續冷靜觀察四周，尋找下一個突破口。",
                "2 嘗試開口詢問身旁的人，探聽更多內幕消息。",
                "3 悄悄檢查身上的隨身物品，看看有沒有隱藏的線索。",
                "4 找個安全的地方暫避風頭，默默運氣調息。"
            ])
            status.update(label="✨ 劇情生成完畢！", state="complete", expanded=False)
        except Exception as e:
            status.update(label="❌ 劇情生成失敗", state="error", expanded=True)
            st.error(f"錯誤詳情：\n{str(e)}")

# ---------------------------------------------------------
# 4. UI 介面配置
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
                st.error("存檔代碼無效！")
else:
    # 📌 【左側邊欄】完整狀態與導航
    with st.sidebar:
        st.header("📌 逆襲導航與狀態")
        p = st.session_state.game_state["player"]
        st.write(f"👤 **{p['name']}**")
        st.write(f"🏷️ 境界：{p['realm']}")
        st.write(f"📍 位置：{p['location']}")
        
        col1, col2 = st.columns(2)
        col1.metric("❤️ HP", p["hp"])
        col2.metric("💙 MP", p["mp"])
        st.metric("🍚 飽腹", p["fullness"])

        with st.expander("📊 詳細屬性數據", expanded=True):
            st.write(f"🧠 悟性：{p['comprehension']} | 🎲 福緣：{p['fortune']} | ✨ 魅力：{p['charm']}")
            st.write(f"⚖️ 正氣：{p['righteousness']} | 🩸 煞氣：{p['evil_aura']} | 👑 威名：{p['fame']}")

        st.markdown("---")
        st.subheader("🗂️ 畫面檢視切換")
        
        if "active_tab" not in st.session_state:
            st.session_state.active_tab = "📖 主線劇情"

        if st.button("📖 主線劇情與冒險", use_container_width=True):
            st.session_state.active_tab = "📖 主線劇情"
            st.rerun()
        if st.button("🎒 我的背包", use_container_width=True):
            st.session_state.active_tab = "🎒 我的背包"
            st.rerun()
        if st.button("👥 三界人物關係", use_container_width=True):
            st.session_state.active_tab = "👥 三界人物關係"
            st.rerun()
        if st.button("💾 存檔與讀檔", use_container_width=True):
            st.session_state.active_tab = "💾 存檔與讀檔"
            st.rerun()

        st.markdown("---")
        if st.button("🎲 重開新局", use_container_width=True):
            st.session_state.game_started = False
            st.session_state.active_tab = "📖 主線劇情"
            st.rerun()

    # 🖥️ 【中央主畫面】
    current_view = st.session_state.get("active_tab", "📖 主線劇情")

    if current_view == "📖 主線劇情":
        st.subheader("📖 主線劇情與冒險")
        for text in st.session_state.game_state["story_history"]:
            if text.startswith("👉"):
                st.info(text)
            else:
                st.write(text)

        st.markdown("---")
        st.write("✨ **請選擇你的行動：**")
        
        for idx, opt in enumerate(st.session_state.current_options):
            if st.button(opt, key=f"opt_{idx}_{len(st.session_state.game_state['story_history'])}", use_container_width=True):
                process_turn(opt)
                st.rerun()

        st.markdown("---")
        custom_act = st.text_input("💬 自由意念輸入：", key="custom_input")
        if st.button("發送自訂行動", use_container_width=True):
            if custom_act.strip():
                process_turn(custom_act.strip())
                st.rerun()

    elif current_view == "🎒 我的背包":
        st.subheader("🎒 我的背包物品欄")
        inv = st.session_state.game_state["inventory"]
        if not inv:
            st.info("背包空空如也。")
        else:
            for item in inv:
                st.success(f"**【{item['name']}】 x {item['count']}**\n\n說明：{item['desc']}")

    elif current_view == "👥 三界人物關係":
        st.subheader("👥 三界人物誌與好感度")
        npcs = st.session_state.game_state["npcs"]
        if not npcs:
            st.info("目前尚未結識任何三界角色。漫漫征途，等待你的探索！")
        else:
            for name, info in npcs.items():
                with st.expander(f"🌸 {name}（好感/敬意：{info['affinity']}）", expanded=True):
                    st.write(f"**身份**：{info['identity']}")
                    st.write(f"**關係**：🤝 {info['relationship']}")
                    st.write(f"**印象關鍵**：{info['key_memory']}")

    elif current_view == "💾 存檔與讀檔":
        st.subheader("💾 遊戲存檔與讀檔管理")
        
        if st.button("⬅️ 返回主線劇情", use_container_width=True):
            st.session_state.active_tab = "📖 主線劇情"
            st.rerun()
            
        st.markdown("---")
        save_data = {
            "game_state": st.session_state.game_state,
            "current_options": st.session_state.current_options
        }
        save_string = json.dumps(save_data, ensure_ascii=False)
        st.text_area("📋 當前存檔代碼（全選複製保存）：", value=save_string, height=150, key="main_save_box")
        
        st.markdown("---")
        in_load_code = st.text_area("📥 請在此貼上存檔代碼以讀取進度：", key="main_load_box")
        if st.button("確認載入存檔 🔄", use_container_width=True):
            if in_load_code.strip():
                try:
                    loaded = json.loads(in_load_code.strip())
                    st.session_state.game_state = loaded.get("game_state", {})
                    st.session_state.current_options = loaded.get("current_options", [])
                    st.success("存檔載入成功！")
                    st.rerun()
                except Exception as err:
                    st.error("存檔代碼格式錯誤，請檢查是否複製完整！")
            else:
                st.warning("請先貼上存檔代碼！")
