import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from openai import OpenAI
import requests

import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time

# APIキーを Streamlit secrets から読み込み
client = OpenAI(api_key="OPENAI_API")

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
    ["観光", "出張"]
)

# 居住地選択
living = "未設定"
living = st.sidebar.text_input("居住地", "")

# 目的地選択
destinations = ["東京", "大阪", "京都", "沖縄", "北海道", "金沢", "広島", "福岡", "パリ", "ロンドン", "ニューヨーク", "バンコク", "ソウル", "台北", "シンガポール", "ローマ", "その他"]
dest = st.sidebar.selectbox("目的地 (その他あり)", destinations)
if dest == "その他":
    destination = "未設定"
    destination = st.sidebar.text_input("目的地を入力してください", "")
else:
    destination = dest

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
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📍 目的地情報", "📅 スケジュール", "🎒 持ち物リスト", "💰 予算管理", "📊 統計", "📤 エクスポート/共有"]) # tab6を追加

# おすすめスポットの取得 (Tab 1 の外で取得し、スケジュール生成でも使えるようにする)
@st.cache_data(show_spinner=False)
def get_spots(place):
    system = f"あなたは優秀な旅行プランナーです。「{place}」への旅行のために、観光客に人気のあるおすすめスポットを日本語で10個、各スポットに簡単な説明（15字以内）付きで教えてください。ただし、箇条書きにし、「スポット:説明」という形で出力してください。また、余計なことは答えないでください。"
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": system}],
        temperature=0.7
    )
    return resp.choices[0].message.content

spots_text = ""
if destination != "未設定":
    spots_text = get_spots(destination)

# 整形して表示
spots = [s.split(":", 1)[0].replace("•", "").strip() for s in spots_text.split("\n") if s.strip()] # スポット名のみを抽出

with tab1:
    st.markdown(f'<div class="destination-card"><h2>🏙️ {destination}への旅行</h2><p>期間: {days}日間 | 人数: {travelers}人</p></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎯 おすすめスポット")
        for spot in spots_text.split("\n"):
            if spot.strip():
                st.write(f"• {spot.strip()}")
        
        spots_data = {}
        if destination:
            spots_data[destination] = []
            for entry in [s.strip() for s in spots_text.split("\n") if s.strip()]:
                name = entry.split("-")[0]
                clean = name.split(". ", 1)[1] if ". " in name else name
                spots_data[destination].append(clean)
        
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

        st.subheader("🗺️ 観光地マップ")

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
    
    with col2:
        # --- 現地天気の取得関数 ---
        @st.cache_data
        def get_coordinates(place):
            url = "https://nominatim.openstreetmap.org/search"
            params = {"q": place, "format": "json", "limit": 1}
            r = requests.get(url, params=params, headers={"User-Agent": "streamlit"})
            if r.ok and r.json():
                loc = r.json()[0]
                return float(loc["lat"]), float(loc["lon"])
            return None, None

        @st.cache_data
        def get_weather(lat, lon, days):
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": lat,
                "longitude": lon,
                "hourly": "temperature_2m,weathercode",
                "timezone": "auto",
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": (start_date + timedelta(days=min(days,7)-1)).strftime("%Y-%m-%d"),
            }
            r = requests.get(url, params=params)
            return pd.DataFrame(r.json()["hourly"]).assign(
                date=lambda df: pd.to_datetime(df["time"]).dt.date,
                temp=lambda df: df["temperature_2m"]
            )

        # --- 表示 ---
        st.subheader("🌤️ 現地の天気予報")
        lat, lon = get_coordinates(destination)
        if lat is None:
            st.error("目的地を正しく入力してください。")
        else:
            dfw = get_weather(lat, lon, days)
            df_daily = dfw.groupby("date")["temp"].mean().reset_index()
            fig = px.line(df_daily, x="date", y="temp", title=f"{destination}の予報 (日平均気温)")
            st.plotly_chart(fig, use_container_width=True)

# グローバルスコープでスケジュールデータを保持するための変数
# これにより、エクスポートタブからアクセスできるようになる
schedule_data = []
if "schedule_data" not in st.session_state:
    st.session_state.schedule_data = []

# グローバルスコープで持ち物リストテキストを保持するための変数
packing_list_text = ""
if "packing_list_text" not in st.session_state:
    st.session_state.packing_list_text = ""

#ai旅行スケール
with tab2:
    st.subheader("📅 旅行スケジュール")
    
    @st.cache_data(show_spinner=False)
    def get_travel_schedule(destination, start_date, end_date, travelers, recommended_spots):
        spot_list_str = ", ".join(recommended_spots)
        system_prompt = f"""
        あなたは優秀な旅行プランナーです。
        以下の情報に基づき、旅行のスケジュール案を作成してください。
        目的地: {destination}
        期間: {start_date.strftime('%Y年%m月%d日')} から {end_date.strftime('%Y年%m月%d日')} ({days}日間)
        旅行者数: {travelers}人
        おすすめスポット: {spot_list_str}

        各日の午前、午後、夜の活動を具体的に提案してください。おすすめスポットを積極的にスケジュールに組み込んでください。
        以下のフォーマットで出力してください。

        日付:
        午前:
        午後:
        夜:

        最大5日間のスケジュールを生成してください。
        """
        
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": system_prompt}],
            temperature=0.7
        )
        return resp.choices[0].message.content

    # スケジュールを生成して表示
    if destination != "未設定" and days > 0 and spots: # `spots`があることを確認
        with st.spinner("おすすめスケジュールを生成中..."):
            generated_schedule_text = get_travel_schedule(destination, start_date, end_date, travelers, spots)
            
            # 生成されたテキストをパースして入力フィールドにセット
            parsed_schedule = []
            current_day_data = {}
            for line in generated_schedule_text.split('\n'):
                if '日付:' in line:
                    if current_day_data:
                        parsed_schedule.append(current_day_data)
                    current_day_data = {'日付': line.replace('日付:', '').strip()}
                elif '午前:' in line:
                    current_day_data['午前'] = line.replace('午前:', '').strip()
                elif '午後:' in line:
                    current_day_data['午後'] = line.replace('午後:', '').strip()
                elif '夜:' in line:
                    current_day_data['夜'] = line.replace('夜:', '').strip()
            if current_day_data:
                parsed_schedule.append(current_day_data)

            # スケジュール入力
            st.session_state.schedule_data = [] # st.session_stateを使用
            for i in range(min(days, 5)):  # 最大5日間表示
                day = start_date + timedelta(days=i)
                st.write(f"**{day.strftime('%Y年%m月%d日')} (Day {i+1})**")
                
                # 生成されたスケジュールがあればそれを初期値に設定
                morning_placeholder = ""
                afternoon_placeholder = ""
                evening_placeholder = ""
                if i < len(parsed_schedule):
                    if '午前' in parsed_schedule[i]:
                        morning_placeholder = parsed_schedule[i]['午前']
                    if '午後' in parsed_schedule[i]:
                        afternoon_placeholder = parsed_schedule[i]['午後']
                    if '夜' in parsed_schedule[i]:
                        evening_placeholder = parsed_schedule[i]['夜']

                morning = st.text_input(f"午前", key=f"morning_{i}", value=morning_placeholder, placeholder="例: ホテルチェックイン")
                afternoon = st.text_input(f"午後", key=f"afternoon_{i}", value=afternoon_placeholder, placeholder="例: 観光地巡り")
                evening = st.text_input(f"夜", key=f"evening_{i}", value=evening_placeholder, placeholder="例: 現地料理を楽しむ")
                
                st.session_state.schedule_data.append({ # st.session_stateを使用
                    '日付': day.strftime('%m/%d'),
                    '午前': morning,
                    '午後': afternoon,
                    '夜': evening
                })
                
                st.write("---")
        
        # スケジュール表示
        if any(item['午前'] or item['午後'] or item['夜'] for item in st.session_state.schedule_data): # st.session_stateを使用
            st.subheader("📋 スケジュール一覧")
            df_schedule = pd.DataFrame(st.session_state.schedule_data) # st.session_stateを使用
            st.dataframe(df_schedule, use_container_width=True)
    elif not spots:
        st.info("おすすめスポットがまだ取得されていません。目的地情報タブでご確認ください。")
    else:
        st.info("目的地と期間を設定すると、おすすめスケジュールが生成されます。")

with tab3: # 持ち物リスト
    st.subheader("🎒 持ち物リスト")

    @st.cache_data(show_spinner=False)
    def get_packing_list(destination, start_date, end_date, travel_type):
        # 季節を判断
        month = start_date.month
        season = ""
        if 3 <= month <= 5:
            season = "春"
        elif 6 <= month <= 8:
            season = "夏"
        elif 9 <= month <= 11:
            season = "秋"
        else:
            season = "冬"

        system_prompt = f"""
        あなたは旅行の専門家です。
        以下の情報に基づき、旅行の持ち物リストを日本語で生成してください。
        目的地: {destination}
        旅行期間: {start_date.strftime('%Y年%m月%d日')} から {end_date.strftime('%Y年%m月%d日')} ({days}日間)
        季節: {season}
        旅行タイプ: {travel_type}

        以下のカテゴリに分けて、具体的な持ち物を箇条書きで提案してください。
        各カテゴリの後に、持ち物を列挙してください。

        衣類:
        洗面用具:
        医薬品・衛生用品:
        貴重品・書類:
        電子機器:
        その他:

        例:
        衣類:
        - Tシャツ 3枚
        - 長ズボン 2枚
        - 薄手のジャケット 1枚
        """
        
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": system_prompt}],
            temperature=0.7
        )
        return resp.choices[0].message.content

    if destination != "未設定" and days > 0:
        with st.spinner("持ち物リストを生成中..."):
            st.session_state.packing_list_text = get_packing_list(destination, start_date, end_date, travel_type) # session_stateに保存
            
            # 生成されたテキストをパースして表示
            st.markdown(st.session_state.packing_list_text)
    else:
        st.info("目的地と期間を設定すると、持ち物リストが生成されます。")


with tab4: # tab4に移動
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

with tab5: # tab5に移動
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

with tab6: # 「エクスポート/共有」
    st.subheader("共有")

    st.write("作成した旅行プランをMarkdown形式でダウンロードできます。")
    st.write("Markdownファイルは、各種テキストエディタや、Markdownビューアで開くことができます。")
    st.write("スマートフォンをご利用の場合はファイルからそのファイルを選択して共有をしてください")

    # プラン内容をMarkdown形式でまとめる
    plan_content = f"# ✈️ 旅行プラン: {destination}\n\n"
    plan_content += f"**期間:** {start_date.strftime('%Y年%m月%d日')} - {end_date.strftime('%Y年%m月%d日')} ({days}日間)\n"
    plan_content += f"**旅行者数:** {travelers}人\n"
    plan_content += f"**総予算:** ¥{budget:,}円\n\n"

    # スケジュール情報
    plan_content += "## 📅 スケジュール\n\n"
    if st.session_state.schedule_data:
        for day_schedule in st.session_state.schedule_data:
            plan_content += f"### {day_schedule['日付']}\n"
            plan_content += f"- 午前: {day_schedule['午前']}\n"
            plan_content += f"- 午後: {day_schedule['午後']}\n"
            plan_content += f"- 夜: {day_schedule['夜']}\n\n"
    else:
        plan_content += "スケジュールはまだ作成されていません。\n\n"

    # 持ち物リスト情報
    plan_content += "## 🎒 持ち物リスト\n\n"
    if st.session_state.packing_list_text:
        plan_content += st.session_state.packing_list_text + "\n\n"
    else:
        plan_content += "持ち物リストはまだ生成されていません。\n\n"

    # 予算情報（概要のみ）
    plan_content += "## 💰 予算概要\n\n"
    plan_content += f"- 総予算: ¥{budget:,}\n"
    plan_content += f"- 一人当たり: ¥{budget//travelers:,}\n"
    plan_content += f"- 一日当たり: ¥{budget//days:,}\n\n"

    # ダウンロードボタン
    st.download_button(
        label="📄 プランをMarkdownでダウンロード",
        data=plan_content.encode('utf-8'), # UTF-8でエンコード
        file_name=f"{destination}_旅行プラン_{start_date.strftime('%Y%m%d')}.md",
        mime="application/pdf", )

    st.markdown("---")
    st.subheader(" (開発中)")
    st.info("開発中")
    st.write("")


# フッター
st.markdown("---")
st.markdown("**💡 機能追加のアイデア:**")
st.markdown("• 写真アップロード機能")
st.markdown("• 為替レート表示")

st.title("ChatBot")

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
    st.session_state.messages.append({"role": "system", "content": f"あなたは優秀な旅行プランナーです。旅行を計画してください。ただし、以下の条件を守ってください。 -居住地:{living} -目的地:{destination} -期間:{start_date}から{end_date}まで -予算:{budget}円 -旅行者数:{travelers}人 -国内旅行の場合、主に参考にする旅行まとめサイト:{url1}、{url2}、{url3} -この旅行に関係のないものが入力された場合、必ず回答するのを避けること。ですが　-目的地:{destination} の周辺のトイレやレストランなとは答えてください"})
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
