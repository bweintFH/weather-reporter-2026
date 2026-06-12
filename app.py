import streamlit as st
import views.airport_weather as airport_weather
import views.trip_planner as trip_planner

# Page Configuration
st.set_page_config(page_title="Aviation Weather", layout="wide")

# Build the Sidebar Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Select a module:",
    ["Airport Weather", "Trip Planner"]
)

st.sidebar.markdown("---")

# Route to the selected page
if page == "Airport Weather":
    airport_weather.render()
elif page == "Trip Planner":
    trip_planner.render()