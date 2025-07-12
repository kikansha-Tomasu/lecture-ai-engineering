import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import openai
import json

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

# OpenAI API設定
st.sidebar.title("🤖 AI設定")
openai_api_key = st.sidebar.text_input("OpenAI APIキー", type="password", help="ChatGPT APIを使用するにはAPIキーが必要です")

if openai_api_key:
    openai.api_key = openai_api_key

st.sidebar.markdown("---")
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
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📍 目的地情報", "📅 スケジュール", "💰 予算管理", "📊 統計", "🤖 AI旅行アシスタント"])

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

with tab5:
    st.subheader("🤖 AI旅行アシスタント")
    
    if not openai_api_key:
        st.warning("⚠️ OpenAI APIキーを入力してください（サイドバー）")
        st.info("APIキーの取得方法：\n1. https://platform.openai.com にアクセス\n2. アカウントを作成またはログイン\n3. API Keys セクションで新しいキーを生成")
    else:
        # ChatGPT API関数
        def get_chatgpt_response(prompt, travel_context):
            try:
                context = f"""
                旅行情報：
                - 目的地: {travel_context['destination']}
                - 旅行タイプ: {travel_context['travel_type']}
                - 期間: {travel_context['days']}日間
                - 人数: {travel_context['travelers']}人
                - 予算: ¥{travel_context['budget']:,}
                - 出発日: {travel_context['start_date']}
                
                あなたは親切な旅行アシスタントです。上記の旅行情報を参考に、具体的で実用的なアドバイスを提供してください。
                """
                
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": context},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1000,
                    temperature=0.7
                )
                return response.choices[0].message.content
            except Exception as e:
                return f"エラーが発生しました: {str(e)}"
        
        # 旅行コンテキスト
        travel_context = {
            'destination': destination,
            'travel_type': travel_type,
            'days': days,
            'travelers': travelers,
            'budget': budget,
            'start_date': start_date.strftime('%Y年%m月%d日')
        }
        
        # プリセット質問
        st.subheader("💡 よくある質問")
        preset_questions = [
            "おすすめの観光スポットを教えて",
            "予算内で楽しめるアクティビティは？",
            "現地の美味しい料理や名物を教えて",
            "交通手段のおすすめは？",
            "持参すべき持ち物リストを作って",
            "現地の文化やマナーについて教えて",
            "効率的な観光ルートを提案して",
            "雨の日の過ごし方を教えて"
        ]
        
        col1, col2 = st.columns(2)
        for i, question in enumerate(preset_questions):
            if i % 2 == 0:
                if col1.button(question, key=f"preset_{i}"):
                    st.session_state['selected_question'] = question
            else:
                if col2.button(question, key=f"preset_{i}"):
                    st.session_state['selected_question'] = question
        
        # 質問入力フォーム
        st.subheader("🗣️ 自由に質問")
        
        # セッション状態の初期化
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        
        # 選択された質問があれば入力欄に設定
        default_question = ""
        if 'selected_question' in st.session_state:
            default_question = st.session_state['selected_question']
            del st.session_state['selected_question']
        
        user_question = st.text_area(
            "質問を入力してください：",
            value=default_question,
            placeholder="例: 3日間で回れる効率的な観光ルートを教えて",
            height=100
        )
        
        col1, col2 = st.columns([1, 4])
        
        with col1:
            if st.button("質問する", type="primary"):
                if user_question.strip():
                    with st.spinner("AIが回答を生成中..."):
                        response = get_chatgpt_response(user_question, travel_context)
                        st.session_state.chat_history.append({
                            'question': user_question,
                            'answer': response,
                            'timestamp': datetime.now()
                        })
                        st.experimental_rerun()
                else:
                    st.warning("質問を入力してください")
        
        with col2:
            if st.button("履歴をクリア"):
                st.session_state.chat_history = []
                st.experimental_rerun()
        
        # チャット履歴表示
        if st.session_state.chat_history:
            st.subheader("💬 質問履歴")
            
            for i, chat in enumerate(reversed(st.session_state.chat_history)):
                with st.expander(f"Q{len(st.session_state.chat_history)-i}: {chat['question'][:50]}..." if len(chat['question']) > 50 else f"Q{len(st.session_state.chat_history)-i}: {chat['question']}", expanded=(i==0)):
                    st.markdown(f"**質問:** {chat['question']}")
                    st.markdown(f"**回答:** {chat['answer']}")
                    st.caption(f"📅 {chat['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 使用上の注意
        st.markdown("---")
        st.subheader("ℹ️ 使用上の注意")
        st.info("""
        **APIキーについて:**
        - OpenAI APIキーは安全に管理してください
        - 使用量に応じて料金が発生します
        - キーは他人と共有しないでください
        
        **回答について:**
        - AIの回答は参考情報として活用してください
        - 最新の情報は公式サイトで確認することをお勧めします
        - 重要な予約や手続きは事前に詳細を確認してください
        """)

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
    
import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time

# 緯度経度取得関数（エラー処理付き）
def get_lat_lng(place_name, retries=3, delay=1):
    geolocator = Nominatim(user_agent="tourism-app")
    for i in range(retries):
        try:
            location = geolocator.geocode(place_name, timeout=10)
            if location:
                return location.latitude, location.longitude
        except (GeocoderTimedOut, GeocoderServiceError):
            time.sleep(delay)
    return None, None

st.title("🗺️ 観光地マップ（API不要）")

# 目的地入力
destination = st.text_input("目的地（例：京都）", "京都")

# 簡単な観光地データ（自由に追加可能）
spots_data = {
    "京都": ["清水寺", "金閣寺", "伏見稲荷大社"],
    "東京": ["東京タワー", "浅草寺", "上野動物園"]
}

# 地図表示
if destination in spots_data:
    base_lat, base_lng = get_lat_lng(destination)
    if base_lat and base_lng:
        m = folium.Map(location=[base_lat, base_lng], zoom_start=12)

        for spot in spots_data[destination]:
            spot_name = f"{destination} {spot}"
            lat, lng = get_lat_lng(spot_name)
            if lat and lng:
                folium.Marker(
                    location=[lat, lng],
                    popup=spot,
                    icon=folium.Icon(color="blue")
                ).add_to(m)
            else:
                st.warning(f"{spot_name} の位置情報が取得できませんでした。")

        st_folium(m, width=700, height=500)
    else:
        st.error("目的地の位置情報を取得できませんでした。")
else:
    st.warning("その目的地の観光地データは未登録です。")
