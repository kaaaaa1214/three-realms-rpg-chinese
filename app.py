import json
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
# 3. 初始化遊戲狀態 (未輸入名字前顯示開局設定)
# ---------------------------------------------------------
if "game_started" not in st.session_state:
    st.session_state.game_started = False

def init_game(player_name):
    st.session_state.game_state = {
        "player": {
            "name": player_name if player_name.strip() else "無名小仙",
            "identity": "仙界·九霄雲宮雜役仙侍（仙界小薯）",
            "bloodline": "未知（體內隱隱有金黑色遠古印記流轉，尚未覺醒）",
            "hp": "100/100",
            "mp": "30/30",
            "fullness": "90/100",
            "realm": "微末小仙 / 煉氣初期",
            "location": "仙界·凌霄外園雜役司",
            "status": "健康（略感疲憊）",
            "comprehension": 9,   # 悟性
            "fortune": 8,         # 福緣
            "charm": 10,          # 魅力 (吸引桃花)
            "righteousness": 10,  # 正氣
            "evil_aura": 0,       # 煞氣
            "fame": 1             # 威名
        },
        "inventory": [
            {"name": "掃靈帚", "count": 1, "desc": "打掃仙園落花用的普通法器。"},
            {"name": "下品仙露", "count": 2, "desc": "仙界最普通的飲品，補充 20 點飽腹度與少量靈力。"},
            {"name": "神秘玉佩", "count": 1, "desc": "從小隨身攜帶的殘破玉佩，散發著微弱的古老氣息。"}
        ],
        "npcs": {
            "清虛仙尊·墨白": {
                "identity": "仙界第一劍尊 / 高冷禁慾",
                "affinity": 15,
                "relationship": "遙不可及的雲端仙尊（對你有一絲微弱的既視感）",
                "key_memory": "曾在仙園遠遠看過你一眼，眼神似乎停頓了片刻。"
            }
        },
        "story_history": [f"你睜開眼睛，發現自己正身處仙界最底層的雜役司，手裡握著掃靈帚。雖然只是個名叫【{player_name}】的仙界小薯，但你心中總覺得自己不該止步於此……"]
    }
    st.session_state.current_options = [
        "拿起掃靈帚開始認命打掃仙園",
        "悄悄拿出殘破玉佩研究上面的古老印記",
        "偷懶溜去仙園深處看能不能碰碰運氣"
    ]
    st.session_state.game_started = True

SYSTEM_INSTRUCTION = """
你是一個高品質的【仙俠 RPG 遊戲主持人（GM）】，擅長豐富的情感細節與細膩的情愛動態。

【玩家背景設定】：
- 玩家表面上是仙界最底層的雜役仙侍（仙界小薯），但身世極其特殊（隱藏著震撼三界的遠古血脈或神秘過往）。
- 請在劇情中適時埋下關於「神秘身世/血脈覺醒」的伏筆與線索。

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
# 5. UI 介面（開局問名 + 手機優化 + 存檔功能）
# ---------------------------------------------------------
st.title("🌸 三界奇譚：仙界小薯逆襲記")

# 若尚未開始遊戲，顯示【輸入姓名】與【讀取存檔】畫面
if not st.session_state.game_started:
    st.subheader("✨ 踏入仙途")
    
    with st.form("start_game_form"):
        input_name = st.text_input("請輸入你在仙界的名字：", value="詩柔")
        submit_btn = st.form_submit_button("開啟仙途 🚀", use_container_width=True)
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
    # 遊戲主要介面 (分頁)
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
        custom_act = st.text_input("💬 自由意念（例：嘗試向清虛仙尊搭話 / 使用下品仙露）：")
        if st.button("發送自訂行動", use_container_width=True):
            if custom_act.strip():
                process_turn(custom_act.strip())
                st.rerun()

    # --- 頁籤 2：主角狀態與身世 ---
    with tab_status:
        p = st.session_state.game_state["player"]
        st.subheader(f"👤 {p['name']}")
        st.write(f"**身份**：{p['identity']}")
        st.write(f"**血脈身世**：{p['bloodline']}")
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
        st.info("💡 只要將「存檔代碼」複製並儲存在手機的備忘錄裡，下次重新開啟遊戲時貼上即可繼續進度！")
        
        # 匯出存檔
        save_data = {
            "game_state": st.session_state.game_state,
            "current_options": st.session_state.current_options
        }
        save_string = json.dumps(save_data, ensure_ascii=False)
        
        st.write("📋 **你的當前存檔代碼（點擊框框全選複製）：**")
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
