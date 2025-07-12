import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from openai import OpenAI  # pip install openai

# ページ設定
st.set_page_config(
    page_title="旅行プランナー",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #2E86AB;
        text-align: center;
        margin-bottom: 2rem;
    }
    .destination-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 1rem 0;
    }
    .budget-info {
        background: #f0f8ff;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #2E86AB;
    }
</style>
""", unsafe_allow_html=True)

# サイドバー
st.sidebar.title("🗺️ 旅行設定")

# 旅行タイプ選択
travel_type = st.sidebar.selectbox(
    "旅行タイプ",
    ["国内旅行", "海外旅行", "出張", "グループ旅行", "一人旅"]
)

# 目的地選択
if travel_type == "国内旅行":
    destinations = ["東京", "大阪", "京都", "沖縄", "北海道", "金沢", "広島", "福岡"]
else:
    destinations = ["パリ", "ロンドン", "ニューヨーク", "バンコク", "ソウル", "台北", "シンガポール", "ローマ"]

destination = st.sidebar.selectbox("目的地", destinations)

# 日程
start_date = st.sidebar.date_input("出発日", datetime.now())
end_date = st.sidebar.date_input("帰着日", datetime.now() + timedelta(days=3))
days = (end_date - start_date).days

# 予算
budget = st.sidebar.number_input("予算（円）", min_value=10000, max_value=1000000, value=100000, step=10000)

# 人数
travelers = st.sidebar.number_input("旅行者数", min_value=1, max_value=20, value=2)

# メインコンテンツ
st.markdown('<h1 class="main-header">✈️ 旅行プランナー</h1>', unsafe_allow_html=True)

# タブ作成
tab1, tab2, tab3, tab4 = st.tabs(["📍 目的地情報", "📅 スケジュール", "💰 予算管理", "📊 統計"])

with tab1:
    st.markdown(f'<div class="destination-card"><h2>🏙️ {destination}への旅行</h2><p>期間: {days}日間 | 人数: {travelers}人</p></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎯 おすすめスポット")
        
        # サンプルデータ
        spots_data = {
            "東京": ["東京スカイツリー", "浅草寺", "明治神宮", "渋谷スクランブル交差点"],
            "大阪": ["大阪城", "道頓堀", "ユニバーサル・スタジオ・ジャパン", "通天閣"],
            "京都": ["清水寺", "金閣寺", "伏見稲荷大社", "嵐山"],
            "パリ": ["エッフェル塔", "ルーブル美術館", "ノートルダム大聖堂", "シャンゼリゼ通り"],
            "ロンドン": ["ビッグベン", "大英博物館", "タワーブリッジ", "バッキンガム宮殿"]
        }
        
        if destination in spots_data:
            for spot in spots_data[destination]:
                st.write(f"• {spot}")
        else:
            st.write("• 現地の人気スポットを調べましょう")
            st.write("• 歴史的建造物")
            st.write("• 自然スポット")
            st.write("• グルメエリア")
    
    with col2:
        st.subheader("🌤️ 天気予報")
        
        # 模擬天気データ
        weather_data = pd.DataFrame({
            'date': pd.date_range(start_date, periods=min(days, 7)),
            'temperature': np.random.randint(15, 30, min(days, 7)),
            'condition': np.random.choice(['晴れ', '曇り', '雨'], min(days, 7))
        })
        
        fig = px.line(weather_data, x='date', y='temperature', title='予想気温')
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("📅 旅行スケジュール")
    
    # スケジュール入力
    schedule_data = []
    for i in range(min(days, 5)):  # 最大5日間表示
        day = start_date + timedelta(days=i)
        st.write(f"**{day.strftime('%Y年%m月%d日')} (Day {i+1})**")
        
        morning = st.text_input(f"午前", key=f"morning_{i}", placeholder="例: ホテルチェックイン")
        afternoon = st.text_input(f"午後", key=f"afternoon_{i}", placeholder="例: 観光地巡り")
        evening = st.text_input(f"夜", key=f"evening_{i}", placeholder="例: 現地料理を楽しむ")
        
        schedule_data.append({
            '日付': day.strftime('%m/%d'),
            '午前': morning,
            '午後': afternoon,
            '夜': evening
        })
        
        st.write("---")
    
    # スケジュール表示
    if any(item['午前'] or item['午後'] or item['夜'] for item in schedule_data):
        st.subheader("📋 スケジュール一覧")
        df_schedule = pd.DataFrame(schedule_data)
        st.dataframe(df_schedule, use_container_width=True)

with tab3:
    st.subheader("💰 予算管理")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="budget-info">', unsafe_allow_html=True)
        st.write(f"**総予算:** ¥{budget:,}")
        st.write(f"**一人当たり:** ¥{budget//travelers:,}")
        st.write(f"**一日当たり:** ¥{budget//days:,}")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 費用項目
        st.subheader("費用項目")
        transport = st.number_input("交通費", value=budget//4, step=1000)
        accommodation = st.number_input("宿泊費", value=budget//3, step=1000)
        food = st.number_input("食費", value=budget//4, step=1000)
        activities = st.number_input("観光・娯楽費", value=budget//6, step=1000)
        shopping = st.number_input("お土産・買い物", value=budget//12, step=1000)
        
        total_planned = transport + accommodation + food + activities + shopping
        remaining = budget - total_planned
        
        if remaining < 0:
            st.error(f"予算オーバー: ¥{abs(remaining):,}")
        else:
            st.success(f"残り予算: ¥{remaining:,}")
    
    with col2:
        # 予算円グラフ
        budget_data = pd.DataFrame({
            '項目': ['交通費', '宿泊費', '食費', '観光・娯楽費', 'お土産・買い物'],
            '金額': [transport, accommodation, food, activities, shopping]
        })
        
        fig = px.pie(budget_data, values='金額', names='項目', title='予算配分')
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("📊 旅行統計")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 旅行日数の統計
        st.metric("旅行日数", f"{days}日")
        st.metric("総費用", f"¥{budget:,}")
        st.metric("一日当たり費用", f"¥{budget//days:,}")
        st.metric("一人当たり費用", f"¥{budget//travelers:,}")
    
    with col2:
        # 月別旅行回数（サンプルデータ）
        monthly_trips = pd.DataFrame({
            '月': ['1月', '2月', '3月', '4月', '5月', '6月'],
            '旅行回数': [2, 1, 3, 2, 4, 3]
        })
        
        fig = px.bar(monthly_trips, x='月', y='旅行回数', title='月別旅行回数')
        st.plotly_chart(fig, use_container_width=True)

# フッター
st.markdown("---")
st.markdown("**💡 機能追加のアイデア:**")
st.markdown("• 写真アップロード機能")
st.markdown("• 地図連携")
st.markdown("• 旅行記録の保存")
st.markdown("• 他のユーザーとのプラン共有")
st.markdown("• リアルタイム天気情報")
st.markdown("• 為替レート表示")

# 保存ボタン
if st.button("旅行プランを保存", type="primary"):
    st.success("旅行プランが保存されました！")
    st.balloons()

st.title("ChatBot")

# APIキーを Streamlit secrets から読み込み
client = OpenAI(api_key="OPENAI_API")

# モデル設定と履歴初期化
if "openai_model" not in st.session_state:
    st.session_state.openai_model = "gpt-4o"
if "messages" not in st.session_state:
    st.session_state.messages = []

# 過去メッセージの表示
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message("role"):
            st.markdown(msg["content"])

url1 = "https://www.nta.co.jp/media/tripa/articles/FgthG"
url2 = "https://www.jalan.net/news/article/145790/"
url3 = "https://www.nta.co.jp/media/tripa/articles/W4f7p"
if prompt := st.chat_input("質問してください。"):
    st.session_state.messages.append({"role": "system", "content": f"あなたは優秀な旅行プランナーです。旅行を計画してください。ただし、以下の条件を守ってください。 -目的地:{destination} -期間:{start_date}から{end_date}まで -予算:{budget}円 -旅行者数:{travelers}人 -主に参考にする旅行まとめサイト:{url1}、{url2}、{url3}"})
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # OpenAI に問い合わせし、応答をストリーミング表示
    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model=st.session_state.openai_model,
            messages=st.session_state.messages,
            stream=True
        )
        response = st.write_stream(stream)

    st.session_state.messages.append({"role": "assistant", "content": response})
