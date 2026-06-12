import streamlit as st
import pandas as pd
import plotly.express as px
import urllib.request
import json
import os
from database import get_cached_airports

API_GATEWAY_URL = "https://vp6vpcafzh.execute-api.us-east-1.amazonaws.com"

def fetch_trip_report(route_str):
    if not API_GATEWAY_URL: return None
    url = f"{API_GATEWAY_URL}/trip?route={route_str}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})) as response:
            return json.loads(response.read().decode())
    except Exception: return None

def render():
    st.title("Trip Planner")
    
    if 'trip_route' not in st.session_state: st.session_state.trip_route = []
    if 'trip_submitted' not in st.session_state: st.session_state.trip_submitted = False

    # Fetch from SHARED CACHE - Instantly available if the other page was loaded first!
    with st.spinner("Loading global map data..."):
        all_airports = get_cached_airports()
        airport_labels = [a['label'] for a in all_airports]

    st.sidebar.markdown("### Search & Add")
    selected_label = st.sidebar.selectbox("Select Airport:", options=airport_labels)
    
    if st.sidebar.button("Add to Trip"):
        selected_apt = next(a for a in all_airports if a['label'] == selected_label)
        st.session_state.trip_route.append(selected_apt)
        st.session_state.trip_submitted = False
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Selected Airports")
    
    if len(st.session_state.trip_route) == 0:
        st.sidebar.info("No airports selected yet.")
    else:
        for i, apt in enumerate(st.session_state.trip_route):
            col1, col2 = st.sidebar.columns([4, 1])
            col1.write(f"**{i+1}. {apt['label']}**")
            if col2.button("❌", key=f"del_{i}"):
                st.session_state.trip_route.pop(i)
                st.session_state.trip_submitted = False
                st.rerun()

    st.sidebar.markdown("---")
    can_submit = len(st.session_state.trip_route) >= 3
    
    if st.sidebar.button("Generate Trip Report", disabled=not can_submit, type="primary", use_container_width=True):
        st.session_state.trip_submitted = True

    if not can_submit:
        st.sidebar.caption("Please select at least 3 airports to submit.")

    if len(st.session_state.trip_route) > 0:
        df_route = pd.DataFrame(st.session_state.trip_route)

        fig = px.line_mapbox(
            df_route, lat='lat', lon='lon', hover_name='name', text='icao_code',
            mapbox_style="open-street-map"
        )
        
        # Styling the map markers and lines
        fig.update_traces(mode='markers+lines+text', textposition="top center", 
                          marker=dict(size=10, color="#ff4b4b"), 
                          line=dict(width=3, color="#0068c9"))
        
        fig.update_geos(
            showcountries=True, countrycolor="#e0e0e0",
            showland=True, landcolor="#f4f4f4",
            showocean=True, oceancolor="#e0f2fe",
            fitbounds="locations" if len(df_route) > 1 else None
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Start adding airports in the sidebar to build your route on the map!")

    if st.session_state.trip_submitted:
        st.markdown("---")
        st.subheader("Trip Weather Report")
        
        route_str = ",".join([a['icao_code'] for a in st.session_state.trip_route])
        with st.spinner(f"Fetching live weather for route: {route_str}..."):
            report_data = fetch_trip_report(route_str)
            
        if report_data and "Trip_Route" in report_data:
            st.success("Report successfully generated!")
            for index, step in enumerate(report_data["Trip_Route"]):
                icao = step['Airport']
                apt_info = next((a for a in st.session_state.trip_route if a['icao_code'] == icao), None)
                display_name = apt_info['label'] if apt_info else icao
                st.markdown(f"#### {index + 1}. {display_name}")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Temperature", step.get("Temperature", "-"))
                c2.metric("Humidity", step.get("Humidity", "-"))
                c3.metric("Wind", step.get("Wind", "-"))
                c4.metric("QNH", step.get("QNH", "-"))
                st.caption(f"**Original METAR:** `{step.get('Original_METAR', 'N/A')}`")
                st.divider()
        else:
            st.error("Failed to fetch the report. Please ensure your API Gateway URL is correct.")