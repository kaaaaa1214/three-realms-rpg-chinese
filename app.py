import json
import random
import re
import streamlit as st
from groq import Groq


# =========================================================
# 1. PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="三界奇譚：小薯逆襲記",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================================================
# 2. GROQ CONFIG
# =========================================================

api_key = st.secrets.get("GROQ_API_KEY", "")

if not api_key:
    st.error("⚠️ 請先在 Streamlit Secrets 設定 GROQ_API_KEY。")
    st.stop()

client = Groq(api_key=api_key)

# =========================================================
# 模型設定
#
# 8B：
# 快、便宜、適合測試
#
# 如果你覺得劇情質素唔夠：
# 改成：
# MODEL = "llama-3.3-70b-versatile"
# =========================================================

MODEL = "llama-3.1-8b-instant"


# =========================================================
# 3. 世界資料
# =========================================================

LOCATIONS = [
    {
        "loc": "凡間·青石鎮",
        "identity": "街頭乞討的孤苦孤兒",
        "bg": "父母雙亡，靠替人跑腿與偶爾乞食度日。青石鎮看似平凡，暗地裡卻有修士出沒。"
    },
    {
        "loc": "仙界·凌霄外園",
        "identity": "九霄雲宮最底層雜役仙侍",
        "bg": "每日負責清掃仙園、搬運雜物，是仙界最卑微的小人物。"
    },
    {
        "loc": "妖界·萬妖山脈",
        "identity": "被遺棄的半妖奴隸",
        "bg": "血脈駁雜，在妖界毫無地位，只能依靠自己尋找活路。"
    },
    {
        "loc": "魔界·黑焰深淵",
        "identity": "最低賤的魔鐵礦奴",
        "bg": "每日挖掘魔鐵，稍有偷懶便會遭到監工毒打。"
    },
    {
        "loc": "靈界·散修坊市",
        "identity": "擺地攤維生的落魄散修",
        "bg": "靈根低微、功法殘缺，靠替人跑腿與出售雜物勉強維生。"
    }
]


POTENTIAL_BLOODLINES = [
    "鳳凰涅槃血脈",
    "鴻蒙神魔同體",
    "太古星辰帝君遺脈",
    "九幽妖皇真靈",
    "混沌青蓮道體"
]


START_ITEMS = [
    {
        "name": "粗布麻衣",
        "count": 1,
        "desc": "磨損嚴重的普通衣物。"
    },
    {
        "name": "乾糧",
        "count": 2,
        "desc": "粗糙乾糧，可以恢復少量飽腹度。"
    },
    {
        "name": "清水",
        "count": 1,
        "desc": "普通清水。"
    }
]


# =========================================================
# 4. SESSION STATE
# =========================================================

if "game_started" not in st.session_state:
    st.session_state.game_started = False

if "active_tab" not in st.session_state:
    st.session_state.active_tab = "📖 主線劇情"

if "current_options" not in st.session_state:
    st.session_state.current_options = []

if "game_state" not in st.session_state:
    st.session_state.game_state = {}


# =========================================================
# 5. 工具函數
# =========================================================

def number_from_status(value, default=0):
    """
    從：
    100/100
    85/100
    30/30
    中取得前面的數字。
    """
    try:
        if isinstance(value, int):
            return value

        text = str(value)

        match = re.search(r"-?\d+", text)

        if match:
            return int(match.group())

    except Exception:
        pass

    return default


def make_bar(value, maximum=100):
    value = max(0, min(value, maximum))
    blocks = int(value / maximum * 10)
    return "█" * blocks + "░" * (10 - blocks)


def get_item_count(inventory, item_name):
    for item in inventory:
        if item.get("name") == item_name:
            return item.get("count", 0)

    return 0


def add_item(inventory, name, count, desc=""):
    for item in inventory:
        if item.get("name") == name:
            item["count"] += count
            return

    inventory.append({
        "name": name,
        "count": count,
        "desc": desc
    })


def remove_item(inventory, name, count):
    for item in inventory:
        if item.get("name") == name:
            item["count"] -= count

            if item["count"] <= 0:
                inventory.remove(item)

            return True

    return False


# =========================================================
# 6. 建立新遊戲
# =========================================================

def init_game(player_name):

    loc = random.choice(LOCATIONS)
    bloodline = random.choice(POTENTIAL_BLOODLINES)

    name = player_name.strip()

    if not name:
        name = "詩柔"

    comprehension = random.randint(8, 12)
    fortune = random.randint(8, 12)
    charm = random.randint(8, 12)

    player = {
        "name": name,

        "identity": f"{loc['loc']}·{loc['identity']}",

        "secret_bloodline": bloodline,

        "bloodline_awakened": False,

        "hp": "100/100",
        "mp": "30/30",
        "fullness": "90/100",

        "money": 5,

        "realm": "凡俗之軀",

        "location": loc["loc"],

        "status": "健康",

        "comprehension": comprehension,
        "fortune": fortune,
        "charm": charm,

        "righteousness": 0,
        "evil_aura": 0,
        "fame": 0
    }

    # -----------------------------------------------------
    # 每個地點不同的開局劇情
    # -----------------------------------------------------

    opening_events = {

        "凡間·青石鎮":
            f"""晨霧尚未散盡。

你蜷縮在青石鎮西街一處破舊屋簷下，冷風從衣襟縫隙灌入，將最後一點暖意吹得乾乾淨淨。

你摸了摸腰間。

只有五文錢。

前方不遠處，一名賣包子的老漢正收拾蒸籠。旁邊卻有一個衣著華貴的年輕人匆匆經過，袖口不經意間掉落一枚淡青色玉佩。

年輕人似乎完全沒有察覺。

就在你準備起身時，一名穿灰衣的陌生老者忽然停在街角。

他看了你一眼。

只一眼。

隨後便移開視線。

你不知道那枚玉佩究竟是機緣，還是一個陷阱。""",

        "仙界·凌霄外園":
            f"""天光自九霄垂落。

你提著破舊掃帚，站在凌霄外園的青玉石階旁。

這裡是仙界。

可仙界也有三六九等。

對那些高高在上的仙君而言，你不過是連名字都不值得記住的雜役。

今日輪到你清掃偏園。

然而就在你掃過一株枯死的白玉花時，腳下忽然傳來極輕的一聲脆響。

你低頭。

泥土之中，露出半截黑色碎片。

那東西沒有任何仙光。

看起來甚至毫不起眼。

可你靠近時，心口卻莫名一跳。

與此同時，遠處傳來腳步聲。

有人正在朝這裡走來。""",

        "妖界·萬妖山脈":
            f"""夜雨剛停。

你獨自站在萬妖山脈外圍，身上的衣服早已被荊棘劃得破爛。

你知道自己弱小。

在這片土地上，弱小便意味著可以被隨時獵殺。

就在你準備離開時，灌木深處突然傳來低沉喘息。

你屏住呼吸。

一頭受傷的小妖獸倒在泥地裡。

牠腹部有一道深可見骨的傷口。

而在牠旁邊，散落著幾枚染血的黑色鱗片。

遠處森林裡。

傳來腳步聲。

不是一個人。

至少三個。""",

        "魔界·黑焰深淵":
            f"""黑焰從礦坑深處翻湧而出。

你手中的破舊礦鎬已經裂了一道縫。

今日的任務還沒有完成。

監工就在身後。

任何一個奴工若敢停下，迎來的便可能是一鞭。

你低頭繼續挖掘。

鐺。

第二聲。

鐺。

第三聲。

突然。

礦鎬撞到了一個完全不同的東西。

不是魔鐵。

你撥開碎石。

一顆灰白色的骨珠靜靜躺在礦洞深處。

就在你的手指碰到骨珠的一瞬間，耳邊忽然響起一道極輕的聲音。

「別讓他們看見。」

你猛然抬頭。

身後卻只有漆黑的礦道。""",

        "靈界·散修坊市":
            f"""午後的坊市人聲鼎沸。

你坐在一張破舊木板後，面前只擺著幾件廉價雜物。

沒有好功法。

沒有靈石。

更沒有背景。

就在你快要收攤時，一名戴著斗笠的女子停在你的攤位前。

她沒有看你的商品。

只是低聲問：

「你想不想賺一筆快錢？」

你沒有回答。

她從袖中取出一枚普通到不能再普通的黑色石片。

「替我把它送到城北。」

她頓了頓。

「不要問是什麼。」

就在這時，你注意到坊市入口處有兩名修士正在朝這邊搜尋。"""
    }

    opening = opening_events[loc["loc"]]

    state = {

        "player": player,

        "inventory": [dict(x) for x in START_ITEMS],

        "npcs": {},

        "story_history": [
            f"【命運開啟】\n{opening}"
        ],

        "story_summary":
            "你剛踏入三界人生，身無長物，只有五文錢。"
            "命運已經悄然埋下第一個伏筆。",

        "turn": 0,

        "last_event": "開局",

        "flags": {},

        "history_short": []
    }

    st.session_state.game_state = state

    # -----------------------------------------------------
    # 初始選項
    # -----------------------------------------------------

    st.session_state.current_options = [

        "1 小心靠近眼前的異常之物，先觀察細節再決定是否觸碰。（謹慎探索，可能發現線索）",

        "2 先離開原地，觀察周圍人物的動向。（降低暴露風險，但可能錯失機緣）",

        "3 主動接近附近的人，試探性地打聽消息。（獲取情報，但可能引起注意）",

        "4 不急著行動，暗中觀察整個局勢。（最穩妥，但可能讓其他人先取得機緣）",

        "5 查看當前狀態與身心狀況"
    ]

    st.session_state.game_started = True


# =========================================================
# 7. AI SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
你是「三界奇譚」的修仙文字RPG主持人。

你不是普通聊天機器人。
你的工作是主持一個真正會推進的互動修仙故事。

【語言】

全程使用繁體中文。
不要使用英文。
不要輸出Markdown。
不要輸出程式碼。
不要在JSON以外增加任何文字。

【敘事】

使用第二人稱「你」。

文風：
古典修仙小說。
半文半白。
有畫面感。
有人物心理。
有人物試探。
有危機。
有伏筆。

不要每次都只是描寫環境。

【最重要規則：每回合必須發生事件】

玩家做出選擇後：

1. 必須真的產生結果。
2. 必須出現具體事件。
3. 必須有人物反應、環境變化、發現、危機、利益或情報其中至少一項。
4. 不可以只寫：
「你觀察四周。」
「四周一片寂靜。」
「你暗中探索。」
「命運齒輪開始轉動。」
然後沒有任何事情發生。

這些句子可以出現，但絕對不能作為主要劇情。

【禁止重複】

上一回合玩家做了什麼，
下一回合不能把同一句意思重新寫一次。

例如：

玩家：
「觀察四周。」

下一回合不能：
「你繼續觀察四周。」

而應該：
「你注意到東南角的腳印與其他人的腳印不同，腳印旁還殘留著尚未乾涸的黑色血跡。」

【NPC】

NPC 必須有自己的目的。

NPC 不會無條件幫助玩家。

NPC 可以：
欺騙玩家
試探玩家
利用玩家
交易
威脅
幫助
背叛
隱瞞情報

【世界】

三界不是安全遊樂場。

玩家初期非常弱。

不要讓主角突然變成無敵。

不要隨便突破境界。

不要隨便覺醒血脈。

【隱藏血脈】

玩家的隱藏血脈絕對不能直接告訴玩家。

除非遊戲狀態明確允許覺醒。

可以使用：
心口異樣
血液發熱
夢境
古物共鳴
妖獸畏懼
火焰異常
星光異常

但不能直接說：
「你的血脈是鳳凰。」

【劇情長度】

每回合約250至450字。

不要故意拖長。

【選項】

每回合提供4個真正不同策略的選項。

另外固定提供：

5 查看當前狀態與身心狀況

四個選項應該涵蓋：

謹慎
冒險
交涉
利益交換
逃跑
戰鬥
欺騙
探索

視劇情選擇適合的組合。

【JSON】

必須只輸出合法JSON。

格式：

{
  "story": "劇情",
  "summary": "80字內摘要",
  "options": [
    "1 ...",
    "2 ...",
    "3 ...",
    "4 ...",
    "5 查看當前狀態與身心狀況"
  ]
}

不要輸出其他欄位。

不要使用Markdown。
不要使用```。

【重要】

不要修改玩家數值。

不要修改HP。
不要修改MP。
不要修改金錢。
不要修改物品。

這些全部由遊戲程式控制。

你的工作只有：

劇情
NPC行為
世界事件
選項
伏筆
"""
    

# =========================================================
# 8. 建立給 AI 的遊戲資料
# =========================================================

def build_ai_prompt(player_action):

    state = st.session_state.game_state
    player = state["player"]

    # -----------------------------------------------------
    # 只取最近幾幕
    # 不再把全部歷史送給 AI
    # -----------------------------------------------------

    recent = state["story_history"][-3:]

    # -----------------------------------------------------
    # NPC 只保留簡短資料
    # -----------------------------------------------------

    npc_data = []

    for name, npc in state.get("npcs", {}).items():

        npc_data.append({
            "name": name,
            "identity": npc.get("identity", ""),
            "relationship": npc.get("relationship", ""),
            "affinity": npc.get("affinity", 0),
            "memory": npc.get("memory", "")
        })

    prompt = f"""
【目前遊戲狀態】

回合：
{state.get("turn", 0)}

位置：
{player.get("location", "")}

身份：
{player.get("identity", "")}

境界：
{player.get("realm", "")}

狀態：
{player.get("status", "")}

悟性：
{player.get("comprehension", 10)}

福緣：
{player.get("fortune", 10)}

魅力：
{player.get("charm", 10)}

正氣：
{player.get("righteousness", 0)}

煞氣：
{player.get("evil_aura", 0)}

威名：
{player.get("fame", 0)}

【背包】

{json.dumps(state.get("inventory", []), ensure_ascii=False)}

【人物】

{json.dumps(npc_data, ensure_ascii=False)}

【過往劇情摘要】

{state.get("story_summary", "")}

【最近三幕】

{json.dumps(recent, ensure_ascii=False)}

【玩家這次的行動】

{player_action}

現在請主持下一幕。

一定要讓事情真正發生。

一定要讓玩家的行動造成後果。

只輸出合法JSON。
"""

    return prompt


# =========================================================
# 9. 安全解析 JSON
# =========================================================

def parse_ai_json(raw_text):

    text = raw_text.strip()

    # -----------------------------------------------------
    # 清除 Markdown code block
    # -----------------------------------------------------

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text)
        text = re.sub(r"```$", "", text)

    text = text.strip()

    # -----------------------------------------------------
    # 第一層：直接 JSON
    # -----------------------------------------------------

    try:
        return json.loads(text)
    except Exception:
        pass

    # -----------------------------------------------------
    # 第二層：尋找第一個 { 到最後一個 }
    # -----------------------------------------------------

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:

        candidate = text[start:end + 1]

        try:
            return json.loads(candidate)
        except Exception:
            pass

    return None


# =========================================================
# 10. AI 生成劇情
# =========================================================

def generate_story(player_action):

    state = st.session_state.game_state
    player = state["player"]

    prompt = build_ai_prompt(player_action)

    with st.status(
        "🔮 命運正在推演……",
        expanded=False
    ) as status:

        try:

            response = client.chat.completions.create(

                model=MODEL,

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

                temperature=0.85,

                max_tokens=900,

                response_format={
                    "type": "json_object"
                }
            )

            raw = response.choices[0].message.content

            data = parse_ai_json(raw)

            if not data:

                status.update(
                    label="❌ 劇情資料解析失敗",
                    state="error"
                )

                st.error(
                    "AI 回傳的內容不是有效 JSON。"
                    "可以再按一次選項重試。"
                )

                return False

            # -------------------------------------------------
            # 安全取得資料
            # -------------------------------------------------

            story = str(
                data.get("story", "")
            ).strip()

            summary = str(
                data.get("summary", "")
            ).strip()

            options = data.get("options", [])

            # -------------------------------------------------
            # 防止 AI 回傳空內容
            # -------------------------------------------------

            if not story:

                st.error("AI 沒有生成有效劇情。請重試。")

                return False

            # -------------------------------------------------
            # 選項整理
            # -------------------------------------------------

            clean_options = []

            if isinstance(options, list):

                for option in options:

                    if not isinstance(option, str):
                        continue

                    option = option.strip()

                    if option:
                        clean_options.append(option)

            # -------------------------------------------------
            # 如果 AI 選項不足
            # -------------------------------------------------

            default_options = [
                "1 小心觀察眼前異常，尋找更多線索。（謹慎探索）",
                "2 主動接觸事件中的人物，試探對方意圖。（交涉風險）",
                "3 暫時抽身，尋找安全位置觀察局勢。（保守策略）",
                "4 冒險追查剛才發現的線索。（高風險高回報）",
                "5 查看當前狀態與身心狀況"
            ]

            if len(clean_options) < 4:

                clean_options = default_options

            else:

                clean_options = clean_options[:4]

                clean_options.append(
                    "5 查看當前狀態與身心狀況"
                )

            # -------------------------------------------------
            # 更新遊戲
            # -------------------------------------------------

            state["turn"] += 1

            state["story_history"].append(
                f"【第 {state['turn']} 回合】\n"
                f"你選擇：{player_action}"
            )

            state["story_history"].append(
                story
            )

            state["story_summary"] = (
                summary[:120]
                if summary
                else story[:120]
            )

            state["last_event"] = story[:100]

            # -------------------------------------------------
            # 飽腹度
            #
            # 每次真正行動 -5
            # 但查看狀態不扣
            # -------------------------------------------------

            if not player_action.startswith("5"):

                fullness = number_from_status(
                    player.get("fullness", "90/100"),
                    90
                )

                fullness -= 5

                fullness = max(
                    0,
                    min(100, fullness)
                )

                player["fullness"] = f"{fullness}/100"

                # -------------------------------------------------
                # 飢餓懲罰
                # -------------------------------------------------

                if fullness < 15:

                    hp = number_from_status(
                        player.get("hp", "100/100"),
                        100
                    )

                    hp -= 5

                    hp = max(0, hp)

                    player["hp"] = f"{hp}/100"

                    player["status"] = "極度飢餓"

                elif fullness < 30:

                    player["status"] = "飢餓"

            # -------------------------------------------------
            # 極低 HP
            # -------------------------------------------------

            hp = number_from_status(
                player.get("hp", "100/100"),
                100
            )

            if hp <= 0:

                player["status"] = "瀕死"

            elif hp < 15:

                player["status"] = "重傷瀕死"

            # -------------------------------------------------
            # 儲存選項
            # -------------------------------------------------

            st.session_state.current_options = clean_options

            status.update(
                label="✨ 命運已經推進",
                state="complete"
            )

            return True

        except Exception as e:

            status.update(
                label="❌ AI 呼叫失敗",
                state="error"
            )

            error_text = str(e)

            # -------------------------------------------------
            # 專門處理 Rate Limit
            # -------------------------------------------------

            if (
                "rate_limit" in error_text.lower()
                or "429" in error_text
                or "quota" in error_text.lower()
            ):

                st.error(
                    "⚠️ Groq API 暫時達到使用限制。\n\n"
                    "唔係你個遊戲程式壞咗。"
                    "可以稍後再試，或者換另一個 API。"
                )

            else:

                st.error(
                    f"⚠️ AI 呼叫失敗：\n{error_text}"
                )

            return False


# =========================================================
# 11. 處理玩家行動
# =========================================================

def process_turn(action):

    action = action.strip()

    if not action:
        return

    # -----------------------------------------------------
    # 查看狀態
    # 不呼叫 AI
    # -----------------------------------------------------

    if action.startswith("5"):

        st.session_state.active_tab = "📊 狀態"

        return

    # -----------------------------------------------------
    # 防止 HP = 0 繼續遊戲
    # -----------------------------------------------------

    player = st.session_state.game_state["player"]

    hp = number_from_status(
        player.get("hp", "100/100"),
        100
    )

    if hp <= 0:

        st.error(
            "你已經失去意識，無法繼續行動。"
            "請重新開始人生。"
        )

        return

    # -----------------------------------------------------
    # AI
    # -----------------------------------------------------

    success = generate_story(action)

    if success:

        st.session_state.active_tab = "📖 主線劇情"


# =========================================================
# 12. 使用物品
# =========================================================

def use_food():

    inventory = st.session_state.game_state["inventory"]

    if get_item_count(inventory, "乾糧") <= 0:

        st.warning("你沒有乾糧。")

        return

    remove_item(
        inventory,
        "乾糧",
        1
    )

    player = st.session_state.game_state["player"]

    fullness = number_from_status(
        player.get("fullness", "90/100"),
        90
    )

    fullness += 25

    fullness = min(
        100,
        fullness
    )

    player["fullness"] = f"{fullness}/100"

    if fullness >= 30:

        if player.get("status") in [
            "飢餓",
            "極度飢餓"
        ]:

            player["status"] = "健康"

    st.success("你吃下一份乾糧，腹中終於有了些暖意。")

    st.rerun()


# =========================================================
# 13. 開始畫面
# =========================================================

st.title("🌸 三界奇譚：小薯逆襲記")

st.caption(
    "白手起家 · 隨機世界 · 隱藏血脈 · 人心叵測 · 命運由你選擇"
)


if not st.session_state.game_started:

    st.subheader("🎲 踏入命途")

    st.write(
        "你將隨機降臨三界之一。"
        "沒有神裝，沒有強大背景，只有五文錢與一個尚未被發現的秘密。"
    )

    st.markdown("---")

    with st.form("start_game_form"):

        player_name = st.text_input(
            "請輸入你的名字",
            value="詩柔"
        )

        start = st.form_submit_button(
            "🌸 開啟逆襲人生",
            use_container_width=True
        )

        if start:

            init_game(player_name)

            st.rerun()

    st.markdown("---")

    st.subheader("💾 讀取舊存檔")

    load_code = st.text_area(
        "貼上你的存檔代碼",
        height=180,
        key="start_load"
    )

    if st.button(
        "📂 讀取存檔",
        use_container_width=True
    ):

        if load_code.strip():

            try:

                loaded = json.loads(
                    load_code.strip()
                )

                st.session_state.game_state = loaded.get(
                    "game_state",
                    {}
                )

                st.session_state.current_options = loaded.get(
                    "current_options",
                    []
                )

                st.session_state.game_started = True

                st.success(
                    "✨ 存檔讀取成功。"
                )

                st.rerun()

            except Exception:

                st.error(
                    "❌ 存檔格式錯誤，請確認有完整複製。"
                )

    st.stop()


# =========================================================
# 14. 取得目前遊戲資料
# =========================================================

state = st.session_state.game_state
player = state["player"]


# =========================================================
# 15. SIDEBAR
# =========================================================

with st.sidebar:

    st.header("📌 逆襲導航")

    st.write(
        f"👤 **{player['name']}**"
    )

    st.write(
        f"🏷️ {player['realm']}"
    )

    st.write(
        f"📍 {player['location']}"
    )

    st.markdown("---")

    # -----------------------------------------------------
    # HP
    # -----------------------------------------------------

    hp = number_from_status(
        player["hp"],
        100
    )

    mp = number_from_status(
        player["mp"],
        30
    )

    fullness = number_from_status(
        player["fullness"],
        90
    )

    st.write(
        f"❤️ HP：**{player['hp']}**"
    )

    st.progress(
        max(0, min(1, hp / 100))
    )

    st.write(
        f"💙 MP：**{player['mp']}**"
    )

    st.progress(
        max(0, min(1, mp / 30))
    )

    st.write(
        f"🍚 飽腹：**{player['fullness']}**"
    )

    st.progress(
        max(0, min(1, fullness / 100))
    )

    st.write(
        f"💰 金錢：**{player.get('money', 0)} 文**"
    )

    st.markdown("---")

    with st.expander(
        "📊 詳細屬性",
        expanded=True
    ):

        st.write(
            f"🧠 悟性：{player['comprehension']}"
        )

        st.write(
            f"🎲 福緣：{player['fortune']}"
        )

        st.write(
            f"✨ 魅力：{player['charm']}"
        )

        st.write(
            f"⚖️ 正氣：{player['righteousness']}"
        )

        st.write(
            f"🩸 煞氣：{player['evil_aura']}"
        )

        st.write(
            f"👑 威名：{player['fame']}"
        )

        st.write(
            f"💭 狀態：{player['status']}"
        )

    # -----------------------------------------------------
    # 血脈
    # -----------------------------------------------------

    with st.expander(
        "🔒 身世之謎"
    ):

        if player.get(
            "bloodline_awakened",
            False
        ):

            st.success(
                f"🔥 血脈已覺醒："
                f"{player.get('secret_bloodline', '未知')}"
            )

        else:

            st.info(
                "目前沒有任何明確線索。"
            )

    st.markdown("---")

    # -----------------------------------------------------
    # Navigation
    # -----------------------------------------------------

    if st.button(
        "📖 主線劇情",
        use_container_width=True
    ):

        st.session_state.active_tab = "📖 主線劇情"

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
        "📊 狀態",
        use_container_width=True
    ):

        st.session_state.active_tab = "📊 狀態"

        st.rerun()

    if st.button(
        "💾 存檔 / 讀檔",
        use_container_width=True
    ):

        st.session_state.active_tab = "💾 存檔 / 讀檔"

        st.rerun()

    st.markdown("---")

    if st.button(
        "🎲 重開新局",
        use_container_width=True
    ):

        st.session_state.game_started = False

        st.session_state.game_state = {}

        st.session_state.current_options = []

        st.session_state.active_tab = "📖 主線劇情"

        st.rerun()


# =========================================================
# 16. MAIN VIEW
# =========================================================

current_view = st.session_state.active_tab


# =========================================================
# 主線劇情
# =========================================================

if current_view == "📖 主線劇情":

    st.subheader("📖 主線劇情")

    # -----------------------------------------------------
    # 劇情顯示
    # -----------------------------------------------------

    for text in state["story_history"]:

        if text.startswith("你選擇："):

            st.info(
                f"👉 {text}"
            )

        elif text.startswith("【第"):

            st.markdown(
                f"**{text}**"
            )

        else:

            st.write(text)

    st.markdown("---")

    st.subheader("✨ 你準備怎麼做？")

    # -----------------------------------------------------
    # 選項
    # -----------------------------------------------------

    for index, option in enumerate(
        st.session_state.current_options
    ):

        if st.button(
            option,
            key=f"option_{index}_{state.get('turn', 0)}",
            use_container_width=True
        ):

            process_turn(option)

            st.rerun()

    st.markdown("---")

    # -----------------------------------------------------
    # 自由行動
    # -----------------------------------------------------

    st.write(
        "💬 **你也可以自己決定行動：**"
    )

    custom_action = st.text_input(
        "例如：我假裝沒有發現玉佩，先去跟賣包子的老人聊天。",
        key="custom_action"
    )

    if st.button(
        "⚔️ 執行我的決定",
        use_container_width=True
    ):

        if custom_action.strip():

            process_turn(
                custom_action.strip()
            )

            st.rerun()


# =========================================================
# 背包
# =========================================================

elif current_view == "🎒 我的背包":

    st.subheader("🎒 我的背包")

    inventory = state["inventory"]

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
                    f"### {item['name']} × {item['count']}"
                )

                st.write(
                    item.get(
                        "desc",
                        "沒有描述"
                    )
                )

                if item["name"] == "乾糧":

                    if st.button(
                        "🍚 食用",
                        key=f"use_{item['name']}"
                    ):

                        use_food()

    st.markdown("---")

    if st.button(
        "⬅️ 返回主線",
        use_container_width=True
    ):

        st.session_state.active_tab = "📖 主線劇情"

        st.rerun()


# =========================================================
# 人物關係
# =========================================================

elif current_view == "👥 人物關係":

    st.subheader("👥 三界人物關係")

    npcs = state.get(
        "npcs",
        {}
    )

    if not npcs:

        st.info(
            "目前尚未正式結識任何人物。"
        )

    else:

        for name, npc in npcs.items():

            with st.expander(
                f"🌸 {name}",
                expanded=True
            ):

                st.write(
                    f"**身份：** "
                    f"{npc.get('identity', '未知')}"
                )

                st.write(
                    f"**關係：** "
                    f"{npc.get('relationship', '未知')}"
                )

                st.write(
                    f"**好感：** "
                    f"{npc.get('affinity', 0)}"
                )

                st.write(
                    f"**記憶：** "
                    f"{npc.get('memory', '暫無')}"
                )


# =========================================================
# 狀態
# =========================================================

elif current_view == "📊 狀態":

    st.subheader("📊 當前狀態")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "❤️ 生命",
        player["hp"]
    )

    col2.metric(
        "💙 靈力",
        player["mp"]
    )

    col3.metric(
        "🍚 飽腹",
        player["fullness"]
    )

    st.markdown("---")

    st.write(
        f"👤 **姓名：** {player['name']}"
    )

    st.write(
        f"🏷️ **身份：** {player['identity']}"
    )

    st.write(
        f"📍 **位置：** {player['location']}"
    )

    st.write(
        f"⚔️ **境界：** {player['realm']}"
    )

    st.write(
        f"💭 **狀態：** {player['status']}"
    )

    st.markdown("---")

    st.subheader("📊 屬性")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "悟性",
        player["comprehension"]
    )

    c2.metric(
        "福緣",
        player["fortune"]
    )

    c3.metric(
        "魅力",
        player["charm"]
    )

    c1.metric(
        "正氣",
        player["righteousness"]
    )

    c2.metric(
        "煞氣",
        player["evil_aura"]
    )

    c3.metric(
        "威名",
        player["fame"]
    )

    st.markdown("---")

    if player.get(
        "bloodline_awakened",
        False
    ):

        st.success(
            "🔥 身世之謎已經揭開。"
        )

    else:

        st.info(
            "🔒 你的身世仍然隱藏在命運深處。"
        )


# =========================================================
# 存檔
# =========================================================

elif current_view == "💾 存檔 / 讀檔":

    st.subheader("💾 存檔與讀檔")

    # -----------------------------------------------------
    # 產生存檔
    # -----------------------------------------------------

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

    st.write(
        "### 📋 當前存檔"
    )

    st.text_area(
        "全選並複製以下內容保存",
        value=save_string,
        height=250,
        key="save_box"
    )

    st.markdown("---")

    # -----------------------------------------------------
    # 讀檔
    # -----------------------------------------------------

    st.write(
        "### 📥 讀取存檔"
    )

    load_data = st.text_area(
        "貼上以前保存的存檔",
        height=250,
        key="load_box"
    )

    if st.button(
        "🔄 載入這份存檔",
        use_container_width=True
    ):

        if load_data.strip():

            try:

                loaded = json.loads(
                    load_data.strip()
                )

                st.session_state.game_state = loaded.get(
                    "game_state",
                    {}
                )

                st.session_state.current_options = loaded.get(
                    "current_options",
                    []
                )

                st.success(
                    "✨ 存檔載入成功。"
                )

                st.rerun()

            except Exception:

                st.error(
                    "❌ 存檔格式錯誤。"
                )

        else:

            st.warning(
                "請先貼上存檔。"
            )
