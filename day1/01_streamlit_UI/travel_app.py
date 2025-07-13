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
import urllib.parse

# APIキーを Streamlit secrets から読み込み
client = OpenAI(api_key="OPENAI_API")

# Pexels APIキーをStreamlit secretsから読み込み
PEXELS_API_KEY = "X1FgEO71jk1dAB7mqrTYQJXkR3hYGTmSRixEfVFEuZwdruEmzjK41K2l"

# ChatBotのsystemを管理
first_assist = True

# ページ設定
st.set_page_config(
    page_title="Trekka",
    page_icon="trekka.png", # アプリケーションアイコンのパス
    layout="wide",
    initial_sidebar_state="expanded"
)

#with open("style.css", mode="r", encoding="UTF-8") as test:
    # カスタムCSS
    #st.markdown(test.read(), unsafe_allow_html=True)
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
  </style>""",
 unsafe_allow_html=True)

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
st.markdown('<h1 class="main-header">Trekka</h1>', unsafe_allow_html=True) # アプリケーション名を"Trekka"に

# タブ作成
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📍 目的地情報", "📅 スケジュール", "🎒 持ち物リスト", "💰 予算管理", "📊 統計", "📤 エクスポート/共有"])

# --- グローバルスコープに移動した関数定義 ---
@st.cache_data
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

@st.cache_data
def get_coordinates(place):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": place, "format": "json", "limit": 1}
    r = requests.get(url, params=params, headers={"User-Agent": "streamlit"})
    if r.ok and r.json():
        loc = r.json()[0]
        return float(loc["lat"]), float(loc["lon"])
    return None, None

# おすすめスポットの取得 (Tab 1 の外で取得し、スケジュール生成でも使えるようにする)
@st.cache_data(show_spinner=False)
def get_spots(place):
    system_prompt = f"あなたは優秀な旅行プランナーです。「{place}」への旅行のために、観光客に人気のあるおすすめスポットを日本語で10個、各スポットに簡単な説明（15字以内）付きで教えてください。ただし、箇条書きにし、「スポット:説明」という形で出力してください。また、余計なことは答えないでください。"
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": system_prompt}],
        temperature=0.7
    )
    return resp.choices[0].message.content

spots_text = ""
if destination != "未設定":
    spots_text = get_spots(destination)

# 整形して表示
# spots_dataをここで初期化し、常に structured なデータを保持するようにする
spots_data = {}
if destination:
    spots_data[destination] = []
    for entry in [s.strip() for s in spots_text.split("\n") if s.strip()]:
        entry = entry.lstrip("- ").strip()
        if ":" in entry:
            name = entry.split(":", 1)[0].replace("•", "").strip()
            description = entry.split(":", 1)[1].strip()
        else:
            name = entry.replace("•", "").strip()
            description = ""
        
        clean_name = name.split(". ", 1)[1] if ". " in name else name
        spots_data[destination].append({"name": clean_name, "description": description})

# Pexels APIから画像を検索する
@st.cache_data(show_spinner=False)
def get_pexels_images(query, api_key, per_page=4):
    if not api_key:
        st.error("Pexels APIキーが設定されていません。`.streamlit/secrets.toml`に`PEXELS_API_KEY`を設定してください。")
        return []
    
    headers = {
        "Authorization": api_key
    }
    params = {
        "query": query,
        "per_page": per_page,
        "orientation": "landscape"
    }
    url = "https://api.pexels.com/v1/search"
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        image_urls = []
        if "photos" in data:
            for photo in data["photos"]:
                if 'src' in photo and 'medium' in photo['src']:
                    image_urls.append(photo['src']['medium'])
        return image_urls
    except requests.exceptions.Timeout:
        st.error("Pexels APIへのリクエストがタイムアウトしました。")
        return []
    except requests.exceptions.RequestException as e:
        st.error(f"Pexels APIエラー: {e}")
        return []
    except Exception as e:
        st.error(f"画像の取得中に予期せぬエラーが発生しました: {e}")
        return []

# Simplified WMO Weather Code Interpretation (Source: Open-Meteo Documentation)
WEATHER_CODES = {
    0: "☀️ 晴れ",
    1: "🌤️ ほぼ晴れ",
    2: "⛅ 晴れ時々曇り",
    3: "☁️ 曇り",
    45: "🌫️ 霧",
    48: "🌫️ 霧氷",
    51: "🌧️ 霧雨 (軽度)",
    53: "🌧️ 霧雨 (中度)",
    55: "🌧️ 霧雨 (激しい)",
    56: "🥶 凍雨 (軽度)",
    57: "🥶 凍雨 (激しい)",
    61: "☔ 小雨",
    63: "🌧️ 雨 (中度)",
    65: "⛈️ 大雨",
    66: "🥶 凍雨 (軽度)",
    67: "🥶 凍雨 (激しい)",
    71: "🌨️ 小雪",
    73: "❄️ 雪 (中度)",
    75: "🌨️ 大雪",
    77: "🌨️ 雪の粒",
    80: "☔ にわか雨 (小)",
    81: "🌧️ にわか雨 (中度)",
    82: "⛈️ にわか雨 (激しい)",
    85: "🌨️ にわか雪 (小)",
    86: "❄️ にわか雪 (激しい)",
    95: "⚡ 雷雨",
    96: "⚡ 雹を伴う雷雨 (軽度)",
    99: "⚡ 雹を伴う雷雨 (激しい)"
}

def get_weather_description(code):
    return WEATHER_CODES.get(code, "不明")

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
    data = r.json()["hourly"]
    
    # Create DataFrame from hourly data
    df_hourly = pd.DataFrame({
        "time": pd.to_datetime(data["time"]),
        "temperature_2m": data["temperature_2m"],
        "weathercode": data["weathercode"]
    })
    df_hourly["date"] = df_hourly["time"].dt.date

    # Aggregate to daily data
    df_daily_agg = df_hourly.groupby("date").agg(
        min_temp=("temperature_2m", "min"),
        max_temp=("temperature_2m", "max"),
        avg_temp=("temperature_2m", "mean"),
    ).reset_index()

    # Get daily weather description
    daily_weather_descriptions = []
    for date in df_daily_agg['date']:
        # Filter hourly data for the current date
        daily_hourly_data = df_hourly[df_hourly['date'] == date]
        
        # Try to find the weather code at 12:00 for the day
        noon_weather_code = None
        if not daily_hourly_data.empty:
            noon_hour_data = daily_hourly_data[daily_hourly_data['time'].dt.hour == 12]
            if not noon_hour_data.empty:
                noon_weather_code = noon_hour_data['weathercode'].iloc[0]
            else:
                # If 12:00 data is not available, take the first available code for the day
                noon_weather_code = daily_hourly_data['weathercode'].iloc[0]
        
        daily_weather_descriptions.append(get_weather_description(noon_weather_code) if noon_weather_code is not None else "不明")
    
    df_daily_agg["weather_description"] = daily_weather_descriptions
    
    return df_daily_agg


with tab1:
    st.markdown(f'<div class="destination-card"><h2>🏙️ {destination}への旅行</h2><p>期間: {days}日間 | 人数: {travelers}人</p></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎯 おすすめスポット")
        for spot_info in spots_data.get(destination, []):
            # Google Mapsリンクをスポットリストにも追加
            lat, lng = get_lat_lng(f"{destination} {spot_info['name']}")
            if lat and lng:
                Maps_link = f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
                st.markdown(f"• {spot_info['name']}: {spot_info['description']} ([Googleマップ]({Maps_link}))")
            else:
                st.markdown(f"• {spot_info['name']}: {spot_info['description']}")
        
        st.subheader("🗺️ 観光地マップ")

        if destination != "未設定":
            base_lat, base_lng = get_lat_lng(destination)
            living_lat, living_lng = None, None # 初期化

            if living != "未設定":
                living_lat, living_lng = get_lat_lng(living)
                
            if base_lat and base_lng:
                # マップの中心を居住地と目的地の間に設定、または目的地に設定
                if living_lat and living_lng:
                    center_lat = (base_lat + living_lat) / 2
                    center_lng = (base_lng + living_lng) / 2
                    m = folium.Map(location=[center_lat, center_lng], zoom_start=6) # ズームレベルを広域に調整
                else:
                    m = folium.Map(location=[base_lat, base_lng], zoom_start=12)

                # 目的地マーカー
                destination_popup_html = f"{destination}<br><a href='https://www.google.com/maps/search/?api=1&query={base_lat},{base_lng}' target='_blank'>Googleマップで開く</a>"
                folium.Marker(
                    location=[base_lat, base_lng],
                    popup=folium.Popup(destination_popup_html, max_width=300),
                    icon=folium.Icon(color="red", icon="info-sign")
                ).add_to(m)

                # 居住地マーカーとルート表示
                if living_lat and living_lng:
                    living_popup_html = f"{living}<br><a href='https://www.google.com/maps/search/?api=1&query={living_lat},{living_lng}' target='_blank'>Googleマップで開く</a>"
                    folium.Marker(
                        location=[living_lat, living_lng],
                        popup=folium.Popup(living_popup_html, max_width=300),
                        icon=folium.Icon(color="green", icon="home")
                    ).add_to(m)
                    
                    # 居住地から目的地への直線ルート
                    folium.PolyLine(
                        locations=[[living_lat, living_lng], [base_lat, base_lng]],
                        color='blue',
                        weight=5,
                        opacity=0.7
                    ).add_to(m)
                    st.info("居住地から目的地への直線が表示されています。これは実際の交通ルートとは異なる場合があります。")

                for spot_info in spots_data.get(destination, []):
                    spot_name_full = f"{destination} {spot_info['name']}"
                    lat, lng = get_lat_lng(spot_name_full)
                    if lat and lng:
                        spot_popup_html = f"{spot_info['name']}<br>{spot_info['description']}<br><a href='https://www.google.com/maps/search/?api=1&query={lat},{lng}' target='_blank'>Googleマップで開く</a>"
                        folium.Marker(
                            location=[lat, lng],
                            popup=folium.Popup(spot_popup_html, max_width=300),
                            icon=folium.Icon(color="blue")
                        ).add_to(m)
                    else:
                        st.warning(f"{spot_name_full} の位置情報が取得できませんでした。")

                st_folium(m, width=700, height=500)
            else:
                st.error("目的地の位置情報を取得できませんでした。")
        else:
            st.warning("目的地を設定すると、観光地マップが表示されます。")
        
    with col2:
        st.subheader("🌤️ 現地の天気予報")
        if destination != "未設定":
            lat, lon = get_coordinates(destination)
            if lat is None:
                st.error("目的地を正しく入力してください。")
            else:
                dfw_daily = get_weather(lat, lon, days) # This will now return daily aggregated data
                
                st.write(f"**{destination}の{min(days, 7)}日間の天気予報**")
                
                for index, row in dfw_daily.iterrows():
                    col_date, col_temp, col_desc = st.columns([1, 2, 2])
                    with col_date:
                        st.write(f"**{row['date'].strftime('%m/%d')}**")
                    with col_temp:
                        st.write(f"🌡️ 平均: {row['avg_temp']:.1f}°C")
                        st.write(f"⬇️ 最低: {row['min_temp']:.1f}°C")
                        st.write(f"⬆️ 最高: {row['max_temp']:.1f}°C")
                    with col_desc:
                        st.write(f"天気: {row['weather_description']}")
                    st.markdown("---") # Separator for each day

                # 全体的な気温の傾向を示す折れ線グラフも保持
                st.plotly_chart(px.line(dfw_daily, x="date", y="avg_temp", title=f"{destination}の予報 (日平均気温)"), use_container_width=True)
        else:
            st.info("目的地を設定すると、天気予報が表示されます。")

        # --- 目的地の画像表示 ---
        st.subheader("📸 目的地の画像")
        if destination != "未設定":
            with st.spinner("画像を検索中..."):
                image_urls = get_pexels_images(destination, PEXELS_API_KEY)
                if image_urls:
                    cols = st.columns(len(image_urls))
                    for i, url in enumerate(image_urls):
                        with cols[i]:
                            st.image(url, caption=f"{destination}の画像 {i+1}",  use_container_width=True)
                else:
                    st.info("目的地の画像が見つかりませんでした。")
        else:
            st.info("目的地を設定すると、画像が表示されます。")


# グローバルスコープでスケジュールデータを保持するための変数
# これにより、エクスポートタブからアクセスできるようになる
if "schedule_data" not in st.session_state:
    st.session_state.schedule_data = []

# グローバルスコープで持ち物リストテキストを保持するための変数
if "packing_list_text" not in st.session_state:
    st.session_state.packing_list_text = ""

with tab2:
    st.subheader("📅 旅行スケジュール")
    
    @st.cache_data(show_spinner=False)
    def get_travel_schedule(destination, start_date, end_date, travelers, recommended_spots_list): # 引数名を変更
        spot_list_str = ", ".join(recommended_spots_list) # リストとして受け取る
        system_prompt = f"""
        あなたは優秀な旅行プランナーです。
        以下の情報に基づき、旅行のスケジュール案を作成してください。
        旅行目的:{travel_type}"
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
    if destination != "未設定" and days > 0 and spots_data.get(destination):
        # get_travel_schedule に渡す recommended_spots のデータ形式を調整
        spots_for_schedule = [s["name"] for s in spots_data[destination]]
        
        with st.spinner("おすすめスケジュールを生成中..."):
            generated_schedule_text = get_travel_schedule(destination, start_date, end_date, travelers, spots_for_schedule)
            
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
            st.session_state.schedule_data = []
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
                
                st.session_state.schedule_data.append({
                    '日付': day.strftime('%m/%d'),
                    '午前': morning,
                    '午後': afternoon,
                    '夜': evening
                })
                
                st.write("---")
            
        # スケジュール表示
        if any(item['午前'] or item['午後'] or item['夜'] for item in st.session_state.schedule_data):
            st.subheader("📋 スケジュール一覧")
            df_schedule = pd.DataFrame(st.session_state.schedule_data)
            st.dataframe(df_schedule, use_container_width=True)
    elif not spots_data.get(destination):
        st.info("おすすめスポットがまだ取得されていません。目的地情報タブでご確認ください。")
    else:
        st.info("目的地と期間を設定すると、おすすめスケジュールが生成されます。")

with tab3:
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
        旅行目的: {travel_type}
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
            st.session_state.packing_list_text = get_packing_list(destination, start_date, end_date, travel_type)
            
            # 生成されたテキストをパースして表示
            st.markdown(st.session_state.packing_list_text)
    else:
        st.info("目的地と期間を設定すると、持ち物リストが生成されます。")


with tab4:
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

with tab5:
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
            '月': ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'],
            '旅行回数': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        })
        
        fig = px.bar(monthly_trips, x='月', y='旅行回数', title='月別旅行回数')
        st.plotly_chart(fig, use_container_width=True)

with tab6:
    st.subheader("共有")

    st.write("作成した旅行プランをMarkdown形式でダウンロードできます。")
    st.write("Markdownファイルは、各種テキストエディタや、Markdownビューアで開くことができます。")
    st.write("スマートフォンをご利用の場合はファイルからそのファイルを選択して共有をしてください")

    # プラン内容をMarkdown形式でまとめる
    plan_content = f"# ✈️ 旅行プラン: {destination}\n\n"
    plan_content += f"**旅行目的:** {travel_type}"
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
        data=plan_content.encode('utf-8'),
        file_name=f"{destination}_旅行プラン_{start_date.strftime('%Y%m%d')}.md",
        mime="text/markdown",
    )

st.title("ChatBot")

# モデル設定と履歴初期化
if "openai_model" not in st.session_state:
    st.session_state.openai_model = "gpt-4o"
if "messages" not in st.session_state:
    st.session_state.messages = []


# 過去メッセージの表示
for msg in st.session_state.messages:
    if msg["role"] != "system": # システムメッセージは表示しない
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    first_assist = True
    if msg["role"] == "assistant":
      first_assist = False

if prompt := st.chat_input("質問してください。"):
    if first_assist:
        # システムプロンプトを一度だけ追加
        # ChatBotのシステムプロンプトの定義
        url1 = "https://www.nta.co.jp/media/tripa/articles/FgthG"
        url2 = "https://www.jalan.net/news/article/145790/"
        url3 = "https://www.nta.co.jp/media/tripa/articles/W4f7p"
        system_initial_prompt = (
            f"あなたは優秀な旅行プランナーです。旅行を計画してください。ただし、以下の条件を守ってください。"
            f" -旅行目的:{travel_type}"
            f" -居住地:{living}"
            f" -目的地:{destination}"
            f" -期間:{start_date}から{end_date}まで"
            f" -予算:{budget}円"
            f" -旅行者数:{travelers}人"
            f" -国内旅行の場合、主に参考にする旅行まとめサイト:{url1}, {url2}, {url3}"
            f" -この旅行に関係のないものが入力された場合、必ず回答するのを避けること。"
            f" -目的地:{destination} の周辺のトイレやレストランなどは答えてください。"
        )
        st.session_state.messages.append({"role": "system", "content": system_initial_prompt})
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # OpenAI に問い合わせし、応答をストリーミング表示
    with client.chat.completions.create(
        model=st.session_state.openai_model,
        messages=st.session_state.messages,
        stream=True
    ) as stream:
        response = st.write_stream(stream)

    st.session_state.messages.append({"role": "assistant", "content": response})
