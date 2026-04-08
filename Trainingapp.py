import streamlit as st
from garminconnect import Garmin
import pandas as pd
import datetime
import json
import os

# --- APP CONFIG ---
st.set_page_config(page_title="Hybrid Athlete Monitor", page_icon="⚡")

st.title("🏋️‍♂️ Hybrid Athlete Monitor")
st.markdown("### Powerlifting & Trail Integration")

# File to store the session so we don't get 429 Rate Limited
SESSION_FILE = "garmin_session.json"

# --- HELPER FUNCTIONS ---
def login_garmin(email, password):
    """Logs in and saves or loads session data."""
    client = None
    
    # Try to load session from file if it exists
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r") as f:
                session_data = json.load(f)
            client = Garmin(session_data=session_data)
            client.login() # Re-authenticates using token
            return client
        except Exception:
            # If session is expired, we need to log in fresh
            pass

    # Fresh login if no session or expired
    if not email or not password:
        st.warning("Please enter email and password.")
        return None
        
    client = Garmin(email, password)
    client.login()
    
    # Save session to file
    with open(SESSION_FILE, "w") as f:
        json.dump(client.session_data, f)
    
    return client

# --- SIDEBAR: LOGIN & SETTINGS ---
st.sidebar.header("Garmin Login")
email = st.sidebar.text_input("Email", value="")
password = st.sidebar.text_input("Password", type="password")
baseline_squat = st.sidebar.number_input("Baseline Squat Max (kg)", value=180)

if st.sidebar.button("Logout / Clear Session"):
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)
    st.sidebar.success("Session cleared. Please log in again.")

# --- MAIN APP LOGIC ---
if st.sidebar.button("Fetch My Data"):
    try:
        with st.spinner("Talking to Garmin..."):
            client = login_garmin(email, password)
            
            if client:
                # 1. Get Recovery Stats
                today = datetime.date.today().isoformat()
                stats = client.get_user_summary(today)
                hrv_data = client.get_hrv_data(today)
                
                # Extract Key Metrics
                body_battery = stats.get('bodyBatteryMostRecentValue', 0)
                hrv_val = hrv_data.get('lastNightAvg', 0)
                stress_level = stats.get('averageStressLevel', 0)
                
                # 2. Display Metrics
                col1, col2, col3 = st.columns(3)
                col1.metric("Body Battery", f"{body_battery}%")
                col2.metric("Avg HRV", f"{hrv_val} ms")
                col3.metric("Stress Score", stress_level)

                # --- HYBRID LOGIC ---
                st.subheader("🚀 Performance Predictions")
                
                # Prediction A: 1RM Strength Adjustment
                # Body Battery and Stress affect neural drive
                fatigue_penalty = (100 - body_battery) * 0.25 
                predicted_max = baseline_squat - (fatigue_penalty)
                
                st.write(f"**Predicted Squat Capacity Today:** {round(predicted_max, 1)} kg")
                st.progress(max(0, min(body_battery / 100, 1.0)))

                # Prediction B: Trail Running & Dizziness Risk
                st.subheader("⛰️ Trail Safety Check")
                
                # Critical check for the dizziness you feel
                if hrv_val > 0 and hrv_val < 35 or stress_level > 45:
                    st.error("⚠️ HIGH DIZZINESS RISK: Your nervous system is under recovery strain. Blood pressure regulation will be slow on inclines. Hike slowly and double your electrolyte intake.")
                elif body_battery < 50:
                    st.warning("🟡 MODERATE FATIGUE: Expect heavy legs. Your 14km pace will likely be 10-15% slower than usual.")
                else:
                    st.success("🟢 GREEN LIGHT: System looks recovered. Good day for elevation.")

                # --- RECENT ACTIVITIES ---
                st.subheader("📅 Recent Activity Log")
                activities = client.get_activities(0, 5)
                if activities:
                    df_data = []
                    for act in activities:
                        df_data.append({
                            "Name": act.get('activityName'),
                            "Date": act.get('startTimeLocal'),
                            "Dist (km)": round(act.get('distance', 0)/1000, 2),
                            "Time (min)": round(act.get('duration', 0)/60, 1)
                        })
                    st.table(pd.DataFrame(df_data))

    except Exception as e:
        if "429" in str(e):
            st.error("❌ Garmin Error 429: Too many login attempts. STOP for 1 hour, then try again.")
        else:
            st.error(f"Connection Failed: {e}")

else:
    if not os.path.exists(SESSION_FILE):
        st.info("Enter your Garmin credentials in the sidebar and click 'Fetch My Data'.")
    else:
        st.success("Session found! Click 'Fetch My Data' to update.")