import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.request
import json
import os
from database import get_cached_airports, fetch_weather_history

API_GATEWAY_URL = "https://vp6vpcafzh.execute-api.us-east-1.amazonaws.com"

def fetch_live_metar(icao_code):
    if not API_GATEWAY_URL: return None
    url = f"{API_GATEWAY_URL}/metar?icao={icao_code}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})) as response:
            return json.loads(response.read().decode())
    except Exception: return None

def fetch_taf_forecast(icao_code):
    url = f"https://aviationweather.gov/api/data/taf?ids={icao_code}&format=json"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})) as response:
            data = json.loads(response.read().decode())
            return data[0] if data else None
    except Exception: return None

def render():
    st.title("Aviation Weather Dashboard")
    
    # Fetch Airport List from SHARED CACHE
    with st.spinner("Loading global airport database..."):
        all_airports = get_cached_airports()
        airport_options = [a['label'] for a in all_airports]
    
    st.sidebar.markdown("### Search")
    
    default_index = next((i for i, opt in enumerate(airport_options) if opt.startswith("LOWW")), 0)
    selected_option = st.sidebar.selectbox("Select Airport:", options=airport_options, index=default_index)
    
    icao_input = selected_option.split(" - ")[0].strip() if selected_option else None
    CORE_AIRPORTS = ['LOWW', 'LOWS', 'LOWI', 'LOWG', 'LOWL', 'LOWK', 'EDDM', 'EDDF', 'EHAM', 'EGLL']
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Note:** Full history tracking is only monitored for the 10 core airports:")
    st.sidebar.code(", ".join(CORE_AIRPORTS))
    st.sidebar.caption("Other airports will display live data directly from the API.")

    if icao_input:
        st.subheader(f"Current Data for {selected_option}")
        
        if icao_input in CORE_AIRPORTS:
            with st.spinner("Loading historical database records..."):
                history_data = fetch_weather_history(icao_input)
                
            if history_data:
                df = pd.DataFrame(history_data).sort_values(by='Time').set_index('Time')
                latest = df.iloc[-1]
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Latest Temperature", f"{latest['Temperature (°C)']} °C")
                col2.metric("Latest Humidity", f"{latest['Humidity (%)']} %")
                col3.metric("Latest QNH", f"{latest['QNH (hPa)']} hPa")
                col4.metric("Wind", latest['Wind'])
                
                st.markdown("---")
                if len(df) > 1:
                    col_chart1, col_chart2 = st.columns(2)
                    with col_chart1:
                        st.markdown("**Temperature Trend (24h)**")
                        st.line_chart(df['Temperature (°C)'], color="#ff4b4b")
                    with col_chart2:
                        st.markdown("**Humidity Trend (24h)**")
                        st.line_chart(df['Humidity (%)'], color="#0068c9")
                
                with st.expander("Show Raw Database Entries"):
                    st.dataframe(df)
            else:
                st.warning("No historical data found. Waiting for next Cronjob run.")
        else:
            st.info("Non-core airport selected. Fetching live weather data directly from API Gateway...")
            with st.spinner("Fetching live METAR..."):
                live_data = fetch_live_metar(icao_input)
                
            if live_data:
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Current Temperature", f"{live_data.get('Temperature_C', '-')} °C")
                col2.metric("Current Humidity", f"{live_data.get('Humidity_Percent', '-')} %")
                col3.metric("Current QNH", f"{live_data.get('QNH_hPa', '-')} hPa")
                col4.metric("Wind", live_data.get('Wind', '-'))
                st.caption(f"**Raw METAR:** {live_data.get('Raw_METAR', '')}")
                st.markdown("---")
            else:
                st.error("Could not fetch live weather data. The airport might not have an active weather station.")

        st.subheader("Forecast (TAF)")
        with st.spinner("Fetching live forecast..."):
            forecast = fetch_taf_forecast(icao_input)
            
        if forecast and 'fcsts' in forecast:
            st.info(f"**Raw TAF:** {forecast.get('rawTAF', 'N/A')}")
            forecast_list = []
            for fcst in forecast['fcsts']:
                time_from = datetime.fromtimestamp(fcst.get('timeFrom', 0)).strftime('%d.%m. %H:%M')
                time_to = datetime.fromtimestamp(fcst.get('timeTo', 0)).strftime('%d.%m. %H:%M')
                wind_str = f"{fcst.get('wdir', 'VRB')}° / {fcst.get('wspd', 0)}kt"
                if fcst.get('wgst'): wind_str += f" (Gusts: {fcst.get('wgst')}kt)"
                    
                forecast_list.append({"Period": f"{time_from} - {time_to}", "Wind": wind_str, "Weather": fcst.get('wxString', 'Clear/None'), "Probability (%)": fcst.get('probability', '-')})
            st.dataframe(pd.DataFrame(forecast_list), use_container_width=True)
        else:
            st.warning(f"No active TAF forecast available for {icao_input}.")