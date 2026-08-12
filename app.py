import json
import random
import streamlit as st
from groq import Groq

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
# 2. 初始化 Groq API Client (從 Streamlit Secrets 讀取)
# ---------------------------------------------------------
api_key = st.secrets.get("GROQ_API_KEY", "")

if not api_key:
    st.error("⚠️ 請在 Streamlit Secrets 中設定 GROQ_API_KEY！")
    st.stop()

client = Groq(api_key=api_key)

# ---------------------------------------------------------
# 3. 三界多元開局庫 (白手起家 + 生存危機機制)
# ---------------------------------------------------------
if "game_started" not in st.session_state:
    st.session_state.game_started = False

LOCATIONS = [
    {"loc": "凡間·青石鎮落魄流民所", "identity": "街頭乞討的孤苦孤兒", "bg": "父母雙亡，每日為下一頓飯發愁，在市井中看盡人情冷暖。"},
    {"loc": "仙界·凌霄外園雜役司", "identity": "九霄雲宮最底層雜役仙侍", "bg": "每天負責打掃仙園落花與倒夜香，是仙界最卑微的小薯。"},
    {"loc": "妖界·萬妖山脈外圍暗谷", "identity": "靈智未開就被放養的半妖奴隸", "bg": "混血身份在妖界備受排擠，只能在強大妖獸的爪下艱難求生。"},
    {"loc": "魔界·黑焰深淵礦區", "identity": "最低賤的魔鐵礦奴工", "bg": "每日承受著魔氣侵蝕與監工皮鞭，過著見不到明天的日子。"},
    {"loc": "靈界·散修坊市散亂破廟", "identity": "擺地攤維生的底層落魄散修", "bg": "靈根低下，功法殘缺，經常被強買強賣的修仙家族欺壓。"}
]

POTENTIAL_BLOODLINES = [
    "鳳凰涅槃血脈（隱性：體內隱隱有一絲遠古火靈在流轉）",
    "鴻蒙神魔同體印（隱性：靈魂深處封印著一股神魔交織的悸動）",
    "太古星辰帝君遺脈（隱性：眉心似乎隱藏著某種古老的星紋印記）",
    "九幽妖皇真靈寄宿（隱性：血液中隱含著令萬妖驚顫的上古威壓）"
]

def init_game(player_name):
    loc_info = random.choice(LOCATIONS)
    hidden_bloodline = random.choice(POTENTIAL_BLOODLINES)
    
    comprehension = random.randint(8, 12)
    fortune = random.randint(8, 12)
    charm = random.randint(8, 12)

    st.session_state.game_state = {
        "player": {
            "name": player_name if player_name.strip() else "詩柔",
            "identity": f"{loc_info['loc']}·{loc_info['identity']}",
            "secret_bloodline": hidden_bloodline,
            "bloodline_awakened": False,
            "hp": "100/100",
            "mp": "30/30",
            "fullness": "90/100",
            "money": 5,
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
            {"name": "粗布麻衣", "count": 1, "desc": "極為普通的日常衣物，早已磨損。"},
            {"name": "乾糧清水", "count": 2, "desc": "填飽肚子的普通粗糧與清水。"}
        ],
        "npcs": {},
        "story_history": [
            f"【命運開啟】\n你睜開眼睛，發現自己正身處在**{loc_info['loc']}**。\n"
            f"你是【{player_name}】，身上僅剩下微薄的 **5文錢**，目前只是一個平凡無奇的{loc_info['identity']}（{loc_info['bg']}）。\n"
            f"身無長物，萬事開頭難。茫茫三界，弱肉強食，屬於你的白手起家逆襲之路正式展開……"
        ],
        "story_summary": "遊戲白手起家開局, 主角身懷5文錢, 正處於命運起點, 等待發掘機緣。"
    }
    st.session_state.current_options = [
        "1 既沒有立刻搭話，也沒有亂動，而是冷眼旁觀周圍的動靜，試圖從中找出對自己最有利的生存破局契機。",
        "2 沒有急著怨天尤人，而是默默觀察周遭環境，看看有沒有被遺棄的有用雜物或能落腳的地方。",
        "3 微微挑眉，語氣平淡卻帶著一絲冷靜：「與其在這裡盲目瞎忙，不如先弄清楚這裡的規矩與幕後掌權者。」",
        "4 沒有將心思放在眼前的困境上，反而若有所思地觀察四周，尋找一個可以避開耳目偷偷修煉或尋找機緣的角落。"
    ]
    st.session_state.game_started = True

SYSTEM_INSTRUCTION = """
你是一個高品質、富含戲劇性且節奏明快的【三界跨界 RPG 遊戲主持人（GM）】。

【核心原則：生存危機與動態判定（極度重要）】：
- **生命值 (HP) 危機機制**：
  - 當玩家當前 HP 小於 15 時，劇情與選項必須強烈突顯重傷或瀕死危機，並**頻繁追問/提供「尋找地方休息、療傷或尋求庇護」**的緊急選項。
  - 當玩家 HP 歸零（0/100）時，判定為死亡，遊戲直接迎來悲劇結局（GameOver）。
- **飽腹/饑餓度危機機制**：
  - 當玩家當前飽腹度小於 15 時，劇情必須突顯飢腸轆轆、頭暈眼花，並**頻繁追問/提供「尋找食物、野食、覓食或討飯」**的選項。
  - 當玩家飽腹度歸零（0/100）時，代表嚴重飢餓，**此後每一個行動強制額外扣除 -5 HP**，直到補充食物為止。
- 絕對禁止重複使用相似的劇情套路。每一幕都要有全新的環境轉折與危機。
- 玩家身上有一個隱藏的 `secret_bloodline`，在 `bloodline_awakened` 為 false 時絕對不能明講。

【🎯 選項生成核心規則（防單調）】：
- 每次必須生成 4 個**截然不同走向**的行動選項（如正面突圍、智取佈局、保守避難/休息/覓食、兵行險招）。
- 每個選項開頭必須是數字編號（如 `1`, `2`, `3`, `4`）。

【結算提示格式要求】：
- 在 `story` 欄位的最結尾處，必須加上一行明確的數值結算提示，格式固定為：
  `\n\n【結算：HP-X、MP-X、饑餓-X、錢-X】`
  （請根據玩家本次行動所造成的實際數值消耗或獲得來填寫數值）。

【輸出格式規則】：
必須嚴格回傳標準 JSON（切勿包含任何額外文字或 markdown 程式碼區塊標記，直接回傳純 JSON 字串）：
{
  "story": "詳細精彩的劇情演繹（250字以內），文筆生動，推進劇情。\n\n【結算：HP-0、MP-0、饑餓-5、錢+0】",
  "story_summary_update": "請把『過往劇情摘要』與『本次最新發生的關鍵劇情』融合，更新成一段 80 字以內的精簡歷史摘要。",
  "options": [
    "1 具體且充滿張力的選項描述...",
    "2 具體且充滿張力的選項描述...",
    "3 具體且充滿張力的選項描述...",
    "4 具體且充滿張力的選項描述..."
  ],
  "player_update": {
    "identity": "身份描述", "bloodline_awakened": false, "hp": "100/100", "mp": "30/30", "fullness": "85/100", "money": 5,
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

    with st.status("🔮 Groq 引擎急速運轉中，正在生成劇情與結算...", expanded=True) as status:
        try:
            st.write("正在呼叫 Groq 模型 (llama-3.3-70b-versatile)...")
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_INSTRUCTION},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.9,
                response_format={"type": "json_object"}
            )
            raw_text = response.choices[0].message.content
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
                "1 繼續冷靜觀察四周局勢，尋找下一步的突破口。",
                "2 嘗試與周遭的人物接觸，探聽更多不為人知的內幕消息。",
                "3 找個安靜隱蔽的角落，默默調息體內的氣機。",
                "4 檢查隨身攜帶的物品與周遭環境，看看有沒有遺漏的線索。"
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
    st.subheader("🎲 踏入命途 (白手起家隨機開局)")
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
    # 📌 【左側邊欄】完整狀態與導航（含錢包）
    with st.sidebar:
        st.header("📌 逆襲導航與狀態")
        p = st.session_state.game_state["player"]
        st.write(f"👤 **{p['name']}**")
        st.write(f"🏷️ 境界：{p['realm']}")
        st.write(f"📍 位置：{p['location']}")
        
        col1, col2 = st.columns(2)
        col1.metric("❤️ HP", p["hp"])
        col2.metric("💙 MP", p["mp"])
        
        col3, col4 = st.columns(2)
        col3.metric("🍚 飽腹", p["fullness"])
        col4.metric("💰 金錢", f"{p.get('money', 0)} 文")

        with st.expander("📊 詳細屬性數據", expanded=True):
            st.write(f"🧠 悟性：{p['comprehension']} | 🎲 福緣：{p['fortune']} | ✨ 魅力：{p['charm']}")
            st.write(f"⚖️ 正氣：{p['righteousness']} | 🩸 煞氣：{p['evil_aura']} | 👑 威名：{p['fame']}")
            if p.get("bloodline_awakened", False):
                st.success(f"🔥 **身世已覺醒**：{p['secret_bloodline']}")
            else:
                st.info("🔒 **身世之謎**：尚未覺醒（等待機緣發掘）")

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
        
        def handle_custom_action():
            val = st.session_state.custom_input.strip()
            if val:
                process_turn(val)
                st.session_state.custom_input = ""

        st.text_input("💬 自由意念輸入：", key="custom_input")
        st.button("發送自訂行動", use_container_width=True, on_click=handle_custom_action)

    elif current_view == "🎒 我的背包":
        st.subheader("🎒 我的背包物品欄")
        inv = st.session_state.game_state["inventory"]
        if not inv:
            st.info("背包空空如也，快去劇中尋找機緣吧！")
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
