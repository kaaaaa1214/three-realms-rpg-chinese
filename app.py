````python
import json
import random
import re
import streamlit as st
from groq import Groq


# =========================================================
# 1. 頁面設定
# =========================================================

st.set_page_config(
    page_title="三界奇譚：小薯逆襲記",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================================================
# 2. 初始化 Groq
# =========================================================

api_key = st.secrets.get("GROQ_API_KEY", "")

if not api_key:
    st.error("⚠️ 請在 Streamlit Secrets 中設定 GROQ_API_KEY！")
    st.stop()

client = Groq(api_key=api_key)

# 目前使用較省 quota、速度較快的模型
MODEL_NAME = "llama-3.1-8b-instant"


# =========================================================
# 3. 初始化 Session State
# =========================================================

if "game_started" not in st.session_state:
    st.session_state.game_started = False

if "active_tab" not in st.session_state:
    st.session_state.active_tab = "📖 主線劇情"

if "current_options" not in st.session_state:
    st.session_state.current_options = []


# =========================================================
# 4. 世界 / 開局資料
# =========================================================

LOCATIONS = [
    {
        "loc": "凡間·青石鎮落魄流民所",
        "identity": "街頭乞討的孤苦孤兒",
        "bg": "父母雙亡，每日為下一頓飯發愁，在市井中看盡人情冷暖。"
    },
    {
        "loc": "仙界·凌霄外園雜役司",
        "identity": "九霄雲宮最底層雜役仙侍",
        "bg": "每天負責打掃仙園落花與倒夜香，是仙界最卑微的小薯。"
    },
    {
        "loc": "妖界·萬妖山脈外圍暗谷",
        "identity": "靈智未開就被放養的半妖奴隸",
        "bg": "混血身份在妖界備受排擠，只能在強大妖獸的爪下艱難求生。"
    },
    {
        "loc": "魔界·黑焰深淵礦區",
        "identity": "最低賤的魔鐵礦奴工",
        "bg": "每日承受著魔氣侵蝕與監工皮鞭，過著見不到明天的日子。"
    },
    {
        "loc": "靈界·散修坊市散亂破廟",
        "identity": "擺地攤維生的底層落魄散修",
        "bg": "靈根低下，功法殘缺，經常被強買強賣的修仙家族欺壓。"
    }
]


POTENTIAL_BLOODLINES = [
    "鳳凰涅槃血脈（隱性：體內隱隱有一絲遠古火靈在流轉）",
    "鴻蒙神魔同體印（隱性：靈魂深處封印著一股神魔交織的悸動）",
    "太古星辰帝君遺脈（隱性：眉心似乎隱藏著某種古老的星紋印記）",
    "九幽妖皇真靈寄宿（隱性：血液中隱含著令萬妖驚顫的上古威壓）"
]


# =========================================================
# 5. 初始化遊戲
# =========================================================

def init_game(player_name):

    loc_info = random.choice(LOCATIONS)
    hidden_bloodline = random.choice(POTENTIAL_BLOODLINES)

    comprehension = random.randint(8, 12)
    fortune = random.randint(8, 12)
    charm = random.randint(8, 12)

    final_name = player_name.strip() if player_name.strip() else "詩柔"

    st.session_state.game_state = {

        "player": {
            "name": final_name,
            "identity": f"{loc_info['loc']}·{loc_info['identity']",

            # 注意：
            # 這個欄位會儲存在存檔，但 AI 不可以直接透露
            "secret_bloodline": hidden_bloodline,

            "bloodline_awakened": False,

            "hp": "100/100",
            "mp": "30/30",
            "fullness": "90/100",

            "money": 5,

            "realm": "凡俗之軀 / 煉氣期一層",

            "location": loc_info["loc"],

            "status": "健康（平靜）",

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
                "desc": "極為普通的日常衣物，早已磨損。"
            },
            {
                "name": "乾糧清水",
                "count": 2,
                "desc": "填飽肚子的普通粗糧與清水。"
            }
        ],

        "npcs": {},

        "story_history": [
            (
                f"【命運開啟】\n"
                f"你睜開眼睛，發現自己正身處在"
                f"**{loc_info['loc']}**。\n"
                f"你是【{final_name}】，身上僅剩下微薄的"
                f"**5文錢**，目前只是一個平凡無奇的"
                f"{loc_info['identity']}（{loc_info['bg']}）。\n"
                f"身無長物，萬事開頭難。茫茫三界，弱肉強食，"
                f"屬於你的白手起家逆襲之路正式展開……"
            )
        ],

        "story_summary": (
            "遊戲白手起家開局，主角身懷5文錢，"
            "目前處於命運起點，等待發掘機緣。"
        )
    }

    st.session_state.current_options = [
        "1 既沒有立刻搭話，也沒有亂動，而是冷眼旁觀周圍的動靜，試圖找出對自己最有利的生存破局契機。（靜觀其變）",
        "2 默默觀察周遭環境，尋找被遺棄的有用雜物或可以暫時落腳的地方。（低調求生）",
        "3 試著向周圍的人打聽這裡的規矩與掌權者。（探聽情報）",
        "4 尋找一個偏僻角落，看看是否能避開耳目尋找機緣。（暗中探索）",
        "5 查看當前狀態與身心狀況"
    ]

    st.session_state.game_started = True
    st.session_state.active_tab = "📖 主線劇情"


# =========================================================
# 6. AI 系統指令
# =========================================================

SYSTEM_INSTRUCTION = """
你是一個高品質、富含古典修仙韻味的三界跨界 RPG 遊戲主持人。

【語言】
全程使用流暢、道地的繁體中文。
不得輸出英文字母、英文單字或外文詞彙。

【敘事】
使用第二人稱「你」作為主要敘事視角。
採用半文半白的古典修仙小說筆法。
文字需要有畫面感、臨場感與人物心理。
修仙世界殘酷、現實、人心叵測。
NPC 必須擁有獨立動機，不可無條件幫助玩家。
NPC 可以欺騙、試探、拒絕玩家。

【劇情】
每次推進約300～500字。
劇情必須根據玩家上一輪行動產生合理後果。
不可無故跳躍重大事件。
不可無故給予玩家強大力量、珍稀法寶、大量金錢或高級功法。

【選項】
每輪必須提供5個選項。
前4個選項必須具有不同策略，例如：
正面抗衡、套話試探、靜觀其變、利益交換、探索、撤退。
第5個選項固定為：
「5 查看當前狀態與身心狀況」

每個選項後面必須使用括號說明核心意圖或潛在風險。

【隱藏血脈】
玩家的 secret_bloodline 是絕對隱藏資料。
在 bloodline_awakened=true 之前：
不可直接說出血脈名稱。
不可直接告訴玩家其真實身世。
只能透過異象、夢境、身體反應、奇異感知等方式暗示。

【遊戲狀態】
HP、MP、飽腹度、金錢、物品、境界等資料必須合理變化。

普通行動不可無故大量扣除HP。
玩家沒有受傷時不可無故扣HP。
玩家沒有消費時不可無故扣錢。
玩家沒有取得物品時不可無故增加物品。
玩家沒有修煉或獲得機緣時不可無故提升境界。

HP低於15時必須出現瀕死危機。
飽腹度低於15時必須出現飢餓與負面狀態。

【NPC】
NPC 必須維持自己的身份、性格、關係與記憶。
NPC 不可以知道玩家沒有告訴他們的秘密。

【輸出】
只輸出有效JSON。
不得輸出JSON以外的任何文字。
不得使用Markdown程式碼區塊。

JSON格式：

{
  "story": "300～500字劇情",
  "story_summary_update": "80字以內劇情摘要",
  "options": [
    "1 選項描述（核心意圖或潛在風險）",
    "2 選項描述（核心意圖或潛在風險）",
    "3 選項描述（核心意圖或潛在風險）",
    "4 選項描述（核心意圖或潛在風險）",
    "5 查看當前狀態與身心狀況"
  ],
  "player_update": {},
  "inventory_update": [],
  "npc_updates": []
}
"""


# =========================================================
# 7. 數值工具
# =========================================================

def extract_number(value, default=0):

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return int(value)

    if isinstance(value, str):

        match = re.search(r"-?\d+", value)

        if match:
            return int(match.group())

    return default


def make_bar(value, maximum):

    value = max(0, min(value, maximum))

    return f"{value}/{maximum}"


def clamp_int(value, minimum, maximum):

    try:
        value = int(value)
    except Exception:
        value = minimum

    return max(minimum, min(value, maximum))


# =========================================================
# 8. 保護遊戲數值
# =========================================================

def protect_player_update(old_player, ai_update):

    new_player = old_player.copy()

    # -----------------------------------------------------
    # HP
    # -----------------------------------------------------

    old_hp = extract_number(old_player.get("hp", "100/100"), 100)

    if "hp" in ai_update:
        ai_hp = extract_number(ai_update["hp"], old_hp)

        # 一般單回合最多只允許合理幅度變化
        ai_hp = clamp_int(
            ai_hp,
            max(0, old_hp - 30),
            min(100, old_hp + 10)
        )

        new_player["hp"] = make_bar(ai_hp, 100)

    # -----------------------------------------------------
    # MP
    # -----------------------------------------------------

    old_mp = extract_number(old_player.get("mp", "30/30"), 30)

    if "mp" in ai_update:
        ai_mp = extract_number(ai_update["mp"], old_mp)

        ai_mp = clamp_int(
            ai_mp,
            max(0, old_mp - 20),
            min(30, old_mp + 10)
        )

        new_player["mp"] = make_bar(ai_mp, 30)

    # -----------------------------------------------------
    # 飽腹度
    # -----------------------------------------------------

    old_fullness = extract_number(
        old_player.get("fullness", "90/100"),
        90
    )

    if "fullness" in ai_update:

        ai_fullness = extract_number(
            ai_update["fullness"],
            old_fullness
        )

        # 普通一回合最多下降5
        ai_fullness = clamp_int(
            ai_fullness,
            max(0, old_fullness - 5),
            min(100, old_fullness + 30)
        )

        new_player["fullness"] = make_bar(
            ai_fullness,
            100
        )

    # -----------------------------------------------------
    # 金錢
    # -----------------------------------------------------

    old_money = int(old_player.get("money", 0))

    if "money" in ai_update:

        try:
            ai_money = int(ai_update["money"])
        except Exception:
            ai_money = old_money

        # 防止AI一次亂加大量金錢
        ai_money = clamp_int(
            ai_money,
            max(0, old_money - 20),
            old_money + 20
        )

        new_player["money"] = ai_money

    # -----------------------------------------------------
    # 一般文字狀態
    # -----------------------------------------------------

    allowed_text_fields = [
        "identity",
        "realm",
        "location",
        "status"
    ]

    for field in allowed_text_fields:

        if field in ai_update:

            value = ai_update[field]

            if isinstance(value, str) and value.strip():

                new_player[field] = value.strip()

    # -----------------------------------------------------
    # 數值屬性
    # -----------------------------------------------------

    numeric_fields = [
        "comprehension",
        "fortune",
        "charm",
        "righteousness",
        "evil_aura",
        "fame"
    ]

    for field in numeric_fields:

        if field in ai_update:

            old_value = int(old_player.get(field, 0))

            try:
                new_value = int(ai_update[field])
            except Exception:
                new_value = old_value

            # 單回合最多變化10
            new_value = clamp_int(
                new_value,
                old_value - 10,
                old_value + 10
            )

            new_player[field] = new_value

    # -----------------------------------------------------
    # 血脈覺醒
    # -----------------------------------------------------

    old_awakened = bool(
        old_player.get("bloodline_awakened", False)
    )

    new_awakened = bool(
        ai_update.get(
            "bloodline_awakened",
            old_awakened
        )
    )

    # 一旦覺醒不能倒退
    new_player["bloodline_awakened"] = (
        old_awakened or new_awakened
    )

    return new_player


# =========================================================
# 9. 清理背包
# =========================================================

def clean_inventory(inventory):

    if not isinstance(inventory, list):
        return []

    cleaned = []

    for item in inventory:

        if not isinstance(item, dict):
            continue

        name = item.get("name", "").strip()

        if not name:
            continue

        try:
            count = int(item.get("count", 0))
        except Exception:
            count = 0

        if count <= 0:
            continue

        cleaned.append({
            "name": name,
            "count": count,
            "desc": item.get(
                "desc",
                "普通物品。"
            )
        })

    return cleaned


# =========================================================
# 10. NPC 清理
# =========================================================

def clean_npcs(npc_updates):

    if not isinstance(npc_updates, list):
        return []

    cleaned = []

    for npc in npc_updates:

        if not isinstance(npc, dict):
            continue

        name = npc.get("name", "").strip()

        if not name:
            continue

        cleaned.append({
            "name": name,
            "identity": npc.get(
                "identity",
                "身份不明"
            ),
            "affinity": npc.get(
                "affinity",
                0
            ),
            "relationship": npc.get(
                "relationship",
                "陌生"
            ),
            "key_memory": npc.get(
                "key_memory",
                ""
            )
        })

    return cleaned


# =========================================================
# 11. 呼叫 AI
# =========================================================

def process_turn(player_action):

    game_state = st.session_state.game_state

    # -----------------------------------------------------
    # 最近兩幕
    # -----------------------------------------------------

    recent_history = game_state[
        "story_history"
    ][-2:]

    # -----------------------------------------------------
    # 最近5個NPC
    # -----------------------------------------------------

    all_npcs = game_state.get(
        "npcs",
        {}
    )

    recent_npcs = dict(
        list(all_npcs.items())[-5:]
    )

    # -----------------------------------------------------
    # 玩家資料
    # -----------------------------------------------------

    player_state = game_state["player"]

    # -----------------------------------------------------
    # User Prompt
    #
    # 注意：
    # SYSTEM_INSTRUCTION 不可以再放一次
    # -----------------------------------------------------

    prompt = f"""
【過往冒險精華摘要】
{game_state.get("story_summary", "無")}

【最近兩幕劇情】
{json.dumps(recent_history, ensure_ascii=False)}

【當前主角狀態】
{json.dumps(player_state, ensure_ascii=False)}

【當前背包】
{json.dumps(game_state.get("inventory", []), ensure_ascii=False)}

【最近接觸人物】
{json.dumps(recent_npcs, ensure_ascii=False)}

【玩家最新行動】
{player_action}

請根據玩家最新行動推進劇情。

注意：
- 不要洩露 secret_bloodline。
- 不要無故增加金錢。
- 不要無故增加物品。
- 不要無故提升境界。
- 不要無故扣除大量HP。
- 飽腹度普通行動最多下降5。
- 保持NPC身份與記憶。
- 劇情必須承接最近劇情。
- 必須輸出完整有效JSON。
"""

    with st.status(
        "🔮 正在推演劇情……",
        expanded=True
    ) as status:

        try:

            st.write(
                f"正在使用 {MODEL_NAME} ……"
            )

            response = client.chat.completions.create(

                model=MODEL_NAME,

                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_INSTRUCTION
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],

                temperature=0.85,

                # 防止輸出無限膨脹
                max_tokens=1000,

                response_format={
                    "type": "json_object"
                }
            )

            raw_text = (
                response.choices[0]
                .message
                .content
            )

            # -------------------------------------------------
            # 顯示本次 token 使用量
            # -------------------------------------------------

            if hasattr(response, "usage") and response.usage:

                usage = response.usage

                prompt_tokens = getattr(
                    usage,
                    "prompt_tokens",
                    0
                )

                completion_tokens = getattr(
                    usage,
                    "completion_tokens",
                    0
                )

                total_tokens = getattr(
                    usage,
                    "total_tokens",
                    0
                )

                st.caption(
                    f"本次使用：輸入 {prompt_tokens} tokens｜"
                    f"輸出 {completion_tokens} tokens｜"
                    f"合計 {total_tokens} tokens"
                )

            # -------------------------------------------------
            # JSON 清理
            # -------------------------------------------------

            clean_text = (
                raw_text
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )

            data = json.loads(clean_text)

            # -------------------------------------------------
            # Story
            # -------------------------------------------------

            story = data.get(
                "story",
                "四周一片寂靜，你仍未看清命運真正的方向。"
            )

            # -------------------------------------------------
            # Summary
            # -------------------------------------------------

            summary = data.get(
                "story_summary_update",
                game_state.get(
                    "story_summary",
                    ""
                )
            )

            if not isinstance(summary, str):
                summary = str(summary)

            summary = summary[:500]

            # -------------------------------------------------
            # Player Update
            # -------------------------------------------------

            ai_player_update = data.get(
                "player_update",
                {}
            )

            if not isinstance(
                ai_player_update,
                dict
            ):
                ai_player_update = {}

            protected_player = protect_player_update(
                game_state["player"],
                ai_player_update
            )

            game_state["player"] = protected_player

            # -------------------------------------------------
            # 背包
            # -------------------------------------------------

            if "inventory_update" in data:

                inventory = clean_inventory(
                    data["inventory_update"]
                )

                if inventory:
                    game_state["inventory"] = inventory

            # -------------------------------------------------
            # NPC
            # -------------------------------------------------

            npc_updates = clean_npcs(
                data.get(
                    "npc_updates",
                    []
                )
            )

            for npc in npc_updates:

                game_state["npcs"][
                    npc["name"]
                ] = npc

            # -------------------------------------------------
            # 更新 summary
            # -------------------------------------------------

            game_state[
                "story_summary"
            ] = summary

            # -------------------------------------------------
            # 儲存歷史
            # -------------------------------------------------

            game_state[
                "story_history"
            ].append(
                f"👉 **你選擇了**：{player_action}"
            )

            game_state[
                "story_history"
            ].append(story)

            # -------------------------------------------------
            # 選項
            # -------------------------------------------------

            options = data.get(
                "options",
                []
            )

            if (
                not isinstance(options, list)
                or len(options) < 5
            ):

                options = [
                    "1 繼續冷靜觀察四周局勢，尋找下一步突破口。（靜觀其變）",
                    "2 嘗試與周遭人物交談，探聽更多內幕消息。（試探情報）",
                    "3 找個安靜隱蔽的角落，默默調息體內氣機。（穩定自身）",
                    "4 檢查附近環境與物品，尋找可能存在的機緣。（探索風險）",
                    "5 查看當前狀態與身心狀況"
                ]

            st.session_state.current_options = options[:5]

            status.update(
                label="✨ 劇情生成完畢！",
                state="complete",
                expanded=False
            )

        except json.JSONDecodeError:

            status.update(
                label="❌ AI JSON 解析失敗",
                state="error",
                expanded=True
            )

            st.error(
                "AI 回傳的 JSON 格式不完整。"
                "請再試一次。"
            )

        except Exception as e:

            status.update(
                label="❌ 劇情生成失敗",
                state="error",
                expanded=True
            )

            error_text = str(e)

            if "429" in error_text:

                st.error(
                    "⚠️ Groq 暫時達到 Rate Limit。"
                    "請稍等一陣再試。"
                )

            else:

                st.error(
                    f"錯誤詳情：\n{error_text}"
                )


# =========================================================
# 12. 儲存 / 讀取
# =========================================================

def load_save_data(save_string):

    try:

        loaded_data = json.loads(
            save_string.strip()
        )

        game_state = loaded_data.get(
            "game_state"
        )

        current_options = loaded_data.get(
            "current_options"
        )

        if not isinstance(
            game_state,
            dict
        ):
            raise ValueError(
                "存檔內沒有有效的遊戲資料。"
            )

        st.session_state.game_state = game_state

        st.session_state.current_options = (
            current_options or []
        )

        st.session_state.game_started = True

        return True

    except Exception:

        return False


# =========================================================
# 13. 開始畫面
# =========================================================

st.title("🌸 三界奇譚：小薯逆襲記")


if not st.session_state.game_started:

    st.subheader(
        "🎲 踏入命途｜白手起家隨機開局"
    )

    with st.form("start_game_form"):

        input_name = st.text_input(
            "請輸入你的名字：",
            value="詩柔"
        )

        submit_btn = st.form_submit_button(
            "🎲 開啟逆襲人生 🚀",
            use_container_width=True
        )

        if submit_btn:

            init_game(input_name)

            st.rerun()

    st.markdown("---")

    st.subheader("💾 讀取舊存檔")

    load_code = st.text_area(
        "請貼上你的存檔代碼：",
        key="init_load_code"
    )

    if st.button(
        "讀取存檔進度 📂",
        use_container_width=True
    ):

        if load_code.strip():

            if load_save_data(load_code):

                st.success(
                    "讀取存檔成功！"
                )

                st.rerun()

            else:

                st.error(
                    "存檔代碼無效！"
                )


# =========================================================
# 14. 遊戲主畫面
# =========================================================

else:

    # =====================================================
    # 左側 Sidebar
    # =====================================================

    with st.sidebar:

        st.header(
            "📌 逆襲導航與狀態"
        )

        p = st.session_state.game_state[
            "player"
        ]

        st.write(
            f"👤 **{p['name']}**"
        )

        st.write(
            f"🏷️ 境界：{p['realm']}"
        )

        st.write(
            f"📍 位置：{p['location']}"
        )

        col1, col2 = st.columns(2)

        col1.metric(
            "❤️ HP",
            p["hp"]
        )

        col2.metric(
            "💙 MP",
            p["mp"]
        )

        col3, col4 = st.columns(2)

        col3.metric(
            "🍚 飽腹",
            p["fullness"]
        )

        col4.metric(
            "💰 金錢",
            f"{p.get('money', 0)} 文"
        )

        # -------------------------------------------------
        # 詳細屬性
        # -------------------------------------------------

        with st.expander(
            "📊 詳細屬性數據",
            expanded=True
        ):

            st.write(
                f"🧠 悟性：{p['comprehension']} "
                f"| 🎲 福緣：{p['fortune']} "
                f"| ✨ 魅力：{p['charm']}"
            )

            st.write(
                f"⚖️ 正氣：{p['righteousness']} "
                f"| 🩸 煞氣：{p['evil_aura']} "
                f"| 👑 威名：{p['fame']}"
            )

            if p.get(
                "bloodline_awakened",
                False
            ):

                st.success(
                    f"🔥 **身世已覺醒**："
                    f"{p['secret_bloodline']}"
                )

            else:

                st.info(
                    "🔒 **身世之謎**："
                    "尚未覺醒（等待機緣發掘）"
                )

        # -------------------------------------------------
        # 導航
        # -------------------------------------------------

        st.markdown("---")

        st.subheader(
            "🗂️ 畫面檢視切換"
        )

        if st.button(
            "📖 主線劇情與冒險",
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
            "👥 三界人物關係",
            use_container_width=True
        ):

            st.session_state.active_tab = (
                "👥 三界人物關係"
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

        # -------------------------------------------------
        # 重開
        # -------------------------------------------------

        st.markdown("---")

        if st.button(
            "🎲 重開新局",
            use_container_width=True
        ):

            st.session_state.game_started = False

            st.session_state.active_tab = (
                "📖 主線劇情"
            )

            st.session_state.current_options = []

            st.rerun()


    # =====================================================
    # 中央畫面
    # =====================================================

    current_view = st.session_state.get(
        "active_tab",
        "📖 主線劇情"
    )


    # =====================================================
    # 主線劇情
    # =====================================================

    if current_view == "📖 主線劇情":

        st.subheader(
            "📖 主線劇情與冒險"
        )

        for text in st.session_state.game_state[
            "story_history"
        ]:

            if text.startswith("👉"):

                st.info(text)

            else:

                st.write(text)

        st.markdown("---")

        st.write(
            "✨ **請選擇你的行動：**"
        )

        # -------------------------------------------------
        # 固定選項
        # -------------------------------------------------

        for idx, opt in enumerate(
            st.session_state.current_options
        ):

            if st.button(
                opt,
                key=(
                    f"opt_{idx}_"
                    f"{len(st.session_state.game_state['story_history'])}"
                ),
                use_container_width=True
            ):

                # 查看狀態
                if opt.startswith("5"):

                    st.info(
                        f"""
                        ❤️ HP：{p['hp']}
                        
                        💙 MP：{p['mp']}
                        
                        🍚 飽腹：{p['fullness']}
                        
                        💰 金錢：{p.get('money', 0)} 文
                        
                        🏷️ 境界：{p['realm']}
                        
                        📍 位置：{p['location']}
                        
                        🧠 悟性：{p['comprehension']}
                        
                        🎲 福緣：{p['fortune']}
                        
                        ✨ 魅力：{p['charm']}
                        """
                    )

                else:

                    process_turn(opt)

                    st.rerun()

        # -------------------------------------------------
        # 自由輸入
        # -------------------------------------------------

        st.markdown("---")

        def handle_custom_action():

            val = (
                st.session_state
                .custom_input
                .strip()
            )

            if val:

                process_turn(val)

                st.session_state.custom_input = ""


        st.text_input(
            "💬 自由意念輸入：",
            key="custom_input",
            placeholder="例如：我走到那名老人面前，先觀察他的神色。"
        )

        st.button(
            "發送自訂行動",
            use_container_width=True,
            on_click=handle_custom_action
        )


    # =====================================================
    # 背包
    # =====================================================

    elif current_view == "🎒 我的背包":

        st.subheader(
            "🎒 我的背包物品欄"
        )

        inv = st.session_state.game_state[
            "inventory"
        ]

        if not inv:

            st.info(
                "背包空空如也，快去劇中尋找機緣吧！"
            )

        else:

            for item in inv:

                st.success(
                    f"**【{item['name']}】 "
                    f"x {item['count']}**\n\n"
                    f"說明：{item['desc']}"
                )


    # =====================================================
    # NPC
    # =====================================================

    elif current_view == "👥 三界人物關係":

        st.subheader(
            "👥 三界人物誌與好感度"
        )

        npcs = st.session_state.game_state[
            "npcs"
        ]

        if not npcs:

            st.info(
                "目前尚未結識任何三界角色。"
                "漫漫征途，等待你的探索！"
            )

        else:

            for name, info in npcs.items():

                with st.expander(
                    f"🌸 {name}（好感/敬意："
                    f"{info.get('affinity', 0)}）",
                    expanded=True
                ):

                    st.write(
                        f"**身份**："
                        f"{info.get('identity', '未知')}"
                    )

                    st.write(
                        f"**關係**："
                        f"🤝 {info.get('relationship', '陌生')}"
                    )

                    st.write(
                        f"**印象關鍵**："
                        f"{info.get('key_memory', '')}"
                    )


    # =====================================================
    # 存檔
    # =====================================================

    elif current_view == "💾 存檔與讀檔":

        st.subheader(
            "💾 遊戲存檔與讀檔管理"
        )

        if st.button(
            "⬅️ 返回主線劇情",
            use_container_width=True
        ):

            st.session_state.active_tab = (
                "📖 主線劇情"
            )

            st.rerun()

        st.markdown("---")

        save_data = {
            "game_state":
                st.session_state.game_state,

            "current_options":
                st.session_state.current_options
        }

        save_string = json.dumps(
            save_data,
            ensure_ascii=False
        )

        st.text_area(
            "📋 當前存檔代碼（全選複製保存）：",
            value=save_string,
            height=180,
            key="main_save_box"
        )

        st.markdown("---")

        in_load_code = st.text_area(
            "📥 請在此貼上存檔代碼以讀取進度：",
            key="main_load_box"
        )

        if st.button(
            "確認載入存檔 🔄",
            use_container_width=True
        ):

            if in_load_code.strip():

                if load_save_data(
                    in_load_code
                ):

                    st.success(
                        "存檔載入成功！"
                    )

                    st.rerun()

                else:

                    st.error(
                        "存檔代碼格式錯誤，"
                        "請檢查是否複製完整！"
                    )

            else:

                st.warning(
                    "請先貼上存檔代碼！"
                )
````
