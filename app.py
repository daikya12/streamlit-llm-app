from dotenv import load_dotenv
load_dotenv()

# app.py
import os
import streamlit as st

# Lesson8スタイル: ChatOpenAI と schema メッセージ
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# ======================
# 設定（モデルなど）
# ======================
MODEL_NAME = "gpt-4o-mini"   # 軽量・低コストで十分
TEMPERATURE = 0.3            # 再現性重視

# ======================
# 役割（専門家）→ システムメッセージの定義
# A,B は要件固定。+αは任意で追加
# ======================
ROLE_SYSTEM_PROMPTS = {
    "コーヒーの専門家（A）": (
        "あなたは世界レベルのコーヒー専門家（トップバリスタ兼ロースター）です。"
        "質問者の目的と器具・豆の条件を確認し、実用的で再現性の高いアドバイスを日本語で端的に返してください。"
        "\n\n"
        "【回答ポリシー】\n"
        "1) まず前提の確認（豆の種類/焙煎度/挽目/抽出器具/湯温/粉量/注湯時間/狙う風味）を1行で要約。\n"
        "2) 推奨レシピ（粉量, 湯量, 比率, 湯温, 挽目の目安, 抽出時間, 注湯ステップ）を数値入りで提示。\n"
        "3) 味の微調整Tips（酸・甘み・ボディの調整方法）を箇条書きで3個以内。\n"
        "4) 家庭環境での落とし穴（スケール除去/湯温精度/挽目の再現）を1行で注意喚起。\n"
        "5) 可能なら代替案（他器具や浅深焙煎の切替）を1つ。\n"
        "\n"
        "【数値ガイド（目安）】\n"
        "- ドリップ比率: 1:15〜1:17、浅煎りは湯温93±2℃、深煎りは90±2℃。\n"
        "- エスプレッソ: 1:2前後, 25–32秒, ブルーム不要。\n"
        "- グラインド：浅煎り→細かめ/深煎り→やや粗めが傾向。\n"
        "\n"
        "【出力形式】\n"
        "・前提要約: ...\n"
        "・推奨レシピ: ...\n"
        "・微調整Tips: …（箇条書き）\n"
        "・注意点: ...\n"
        "・代替案: ...\n"
    ),
    "抹茶の専門家（B）": (
        "あなたは抹茶に精通した茶の専門家です。品種（てん茶由来）、点て方（薄茶/濃茶）、"
        "道具（茶碗/茶筅/茶杓/ふるい）、水質（硬度/温度）を踏まえ、家庭でも再現しやすい手順で日本語回答してください。"
        "\n\n"
        "【回答ポリシー】\n"
        "1) まず用途確認（薄茶/濃茶/ラテ/菓子ペアリング）と抹茶の等級・量・器の有無を1行要約。\n"
        "2) 標準レシピ（抹茶g, 湯ml, 湯温℃, ふるい有無, 茶筅の動かし方, 時間）を数値で提示。\n"
        "3) 味の調整（渋み/旨味/香り/泡立ち）のコツを箇条書きで3個以内。\n"
        "4) 水と保存の要点（軟水推奨, 湯冷まし, 低温多湿回避, 脱酸素/遮光容器）を1行で注意喚起。\n"
        "5) アレンジ提案（ラテ/ソーダ/和菓子ペア）を1つ。\n"
        "\n"
        "【数値ガイド（目安）】\n"
        "- 薄茶: 抹茶2g / 湯60–70ml / 80±2℃、茶筅は『M字の素早い前後』10–15秒。\n"
        "- 濃茶: 抹茶3–4g / 湯30–40ml / 75±2℃、練りを意識し泡は控えめ。\n"
        "- ラテ: 抹茶2g / 湯20mlで溶き、ミルク130–150ml（60–65℃）。\n"
        "\n"
        "【出力形式】\n"
        "・前提要約: ...\n"
        "・標準レシピ: ...\n"
        "・調整のコツ: …（箇条書き）\n"
        "・水/保存の注意: ...\n"
        "・アレンジ: ...\n"
    ),
}


# ======================
# LLM呼び出し関数（要件）
# 入力: 入力テキスト(str), 選択ロール(str)
# 出力: 回答テキスト(str), トークン使用量(dict) もおまけで返す
# ======================
def get_llm_response(user_text: str, role_key: str) -> tuple[str, dict]:
    """
    指定の専門家ロールで、入力テキストに回答する。

    Parameters
    ----------
    user_text : str
        画面の入力フォームからのテキスト
    role_key : str
        ラジオボタンの選択肢キー（ROLE_SYSTEM_PROMPTSのキー）

    Returns
    -------
    tuple[str, dict]
        (回答テキスト, token_usage辞書) 例: {"prompt_tokens": 123, "completion_tokens": 45, "total_tokens": 168}
    """
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("環境変数 OPENAI_API_KEY が設定されていません。")

    system_prompt = ROLE_SYSTEM_PROMPTS.get(role_key, "You are a helpful assistant. Use Japanese.")

    llm = ChatOpenAI(model=MODEL_NAME, temperature=TEMPERATURE, api_key=os.getenv("OPENAI_API_KEY"))

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_text),
    ]
    result = llm(messages)  # AIMessage が返る
    content = result.content

    # トークン使用量（ある場合のみ）
    usage = {}
    try:
        meta = result.response_metadata or {}
        usage = (meta.get("token_usage") or {})  # {"prompt_tokens":..., "completion_tokens":..., "total_tokens":...}
    except Exception:
        pass

    return content, usage


# ======================
# Streamlit UI
# ======================
st.set_page_config(page_title="Expert Q&A (Coffee / Matcha)", page_icon="☕️", layout="centered")

st.title("☕️🍵 Expert Q&A (Coffee / Matcha) – LangChain Lesson8スタイル")
st.caption(
    "本アプリは、入力テキストを LangChain（ChatOpenAI + System/HumanMessage）で LLM に渡し、"
    "選択した『専門家ロール』として回答を返します。"
)

with st.expander("アプリの概要と操作方法", expanded=True):
    st.markdown(
        """
**使い方**
1. 下のラジオボタンで「専門家ロール」を選びます（A=コーヒー、B=抹茶。他に紅茶・カフェ経営も用意）。
2. テキストエリアに質問や相談を書きます。
3. **送信** を押すと、選択ロールに応じた口調・観点で回答が表示されます。

**内部構成**
- `ChatOpenAI` と `SystemMessage` / `HumanMessage` を用い、シンプルな **Model I/O** 構成。
- システムメッセージはラジオの選択に応じて切り替えています。
- 戻り値に回答テキストとトークン使用量（可能な場合）を含めています。
        """
    )

with st.form("q_form", clear_on_submit=False):
    role = st.radio(
        "専門家ロールを選択してください（A/Bは要件固定・追加入り）",
        list(ROLE_SYSTEM_PROMPTS.keys()),
        index=0,
        horizontal=False,
    )
    user_text = st.text_area(
        "質問・相談内容（例：浅煎りエチオピアの華やかな香りを活かす抽出レシピを教えて）",
        height=140,
        placeholder="ここに入力してください…",
    )
    submitted = st.form_submit_button("送信")

if submitted:
    if not user_text.strip():
        st.warning("入力テキストが空です。内容を入力してください。")
    else:
        with st.spinner("LLMに問い合わせ中…"):
            try:
                answer, usage = get_llm_response(user_text.strip(), role)
                st.success("回答")
                st.write(answer)

                if usage:
                    c1, c2, c3 = st.columns(3)
                    c1.metric("prompt_tokens", usage.get("prompt_tokens", "—"))
                    c2.metric("completion_tokens", usage.get("completion_tokens", "—"))
                    c3.metric("total_tokens", usage.get("total_tokens", "—"))
            except Exception as e:
                st.error(f"エラー: {e}\n\nOPENAI_API_KEY の設定やネットワーク状況をご確認ください。")
