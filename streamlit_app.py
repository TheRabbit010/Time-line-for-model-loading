import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import re
from PIL import Image
import os

# ==============================================================================
# 1. ฟังก์ชันสำหรับแยกประเภทเตา (NB1, NB2, NB3) จากชื่อไฟล์
# ==============================================================================
def identify_furnace_type(text_to_search):
    furnace_id = "NB3" # Default
    
    if re.search(r'\b(RAD|CDS|KN9|12SHP|DNGA|P42QR|P42V|SU2|F44|Y4L)\b', text_to_search, re.IGNORECASE): 
        furnace_id = "NB1"
    elif re.search(r'\b(Utahc|UT|Tahc|G2|NB2)\b', text_to_search, re.IGNORECASE): 
        furnace_id = "NB2"
    elif re.search(r'\b(BTM|KE8|M2|EVO|NB3)\b', text_to_search, re.IGNORECASE): 
        furnace_id = "NB3"
    elif re.search(r'\bWK\d{1,2}\b', text_to_search, re.IGNORECASE) or re.search(r'\b\d{6}\b', text_to_search): 
        furnace_id = "NB1"
    else:
        f_match = re.search(r'NB\s*Furnace\s*0?([123])\b|NB\s*#?\s*0?([123])\b|NB-0?([123])\b', text_to_search, re.IGNORECASE)
        if f_match: 
            found_num = next(g for g in f_match.groups() if g is not None)
            furnace_id = f"NB{found_num}"

    return furnace_id

# ==============================================================================
# 2. ฐานข้อมูลโซนของเตา (Zone Lengths) และ Model Pitch
# ==============================================================================
FURNACE_ZONE_DATA = {
    "NB1": [
        {"name": "Dryer Z#1", "len": 3.15, "type": "Dryer"}, {"name": "Dryer Z#2", "len": 3.13, "type": "Dryer"},
        {"name": "EXT Dryer", "len": 0.70, "type": "Dryer"}, {"name": "ENT DB", "len": 0.67, "type": "Debinder"},
        {"name": "DB Z#1", "len": 3.13, "type": "Debinder"}, {"name": "DB Z#2", "len": 2.60, "type": "Debinder"},
        {"name": "DB Z#3", "len": 2.60, "type": "Debinder"}, {"name": "DB Z#4", "len": 3.13, "type": "Debinder"},
        {"name": "XFER#1", "len": 2.71, "type": "Xfer"}, {"name": "Z#1", "len": 3.14, "type": "Heating"},
        {"name": "Z#2", "len": 2.68, "type": "Heating"}, {"name": "Z#3", "len": 2.72, "type": "Heating"},
        {"name": "Z#4", "len": 2.04, "type": "Heating"}, {"name": "Z#5", "len": 2.00, "type": "Heating"},
        {"name": "Z#6", "len": 2.00, "type": "Heating"}, {"name": "Z#7", "len": 2.29, "type": "Heating"},
        {"name": "WatCool#1", "len": 2.39, "type": "Cooling"}, {"name": "WatCool#2", "len": 1.90, "type": "Cooling"},
        {"name": "Exit curtain", "len": 1.90, "type": "Cooling"}, {"name": "XFER#2", "len": 0.45, "type": "Cooling"},
        {"name": "Air Cool#1", "len": 1.25, "type": "Cooling"}, {"name": "Air Cool#2", "len": 1.25, "type": "Cooling"},
        {"name": "Exit", "len": 1.85, "type": "Exit"}
    ],
    "NB2": [
        {"name": "Xfer", "len": 2.00, "type": "Xfer"}, {"name": "Flux spray", "len": 4.70, "type": "Flux"},
        {"name": "Xfer", "len": 2.50, "type": "Xfer"}, {"name": "DryOFF-Z#1", "len": 2.80, "type": "Dryer"},
        {"name": "DryOFF-Z#2", "len": 2.80, "type": "Dryer"}, {"name": "Xfer1", "len": 3.13, "type": "Xfer"},
        {"name": "Z#1", "len": 3.60, "type": "Heating"}, {"name": "Z#2", "len": 2.70, "type": "Heating"},
        {"name": "Z#3", "len": 2.40, "type": "Heating"}, {"name": "Z#4", "len": 2.10, "type": "Heating"},
        {"name": "Z#5", "len": 2.30, "type": "Heating"}, {"name": "Z#6", "len": 1.90, "type": "Heating"},
        {"name": "Z#7", "len": 2.20, "type": "Heating"}, {"name": "Xfer2", "len": 0.80, "type": "Cooling"},
        {"name": "WatCol1", "len": 1.75, "type": "Cooling"}, {"name": "WatCol2", "len": 1.85, "type": "Cooling"},
        {"name": "Xfer3", "len": 2.30, "type": "Cooling"}, {"name": "Airc1", "len": 1.25, "type": "Cooling"},
        {"name": "Airc2", "len": 1.25, "type": "Cooling"}, {"name": "Exit", "len": 1.80, "type": "Exit"}
    ],
    "NB3": [
        {"name": "XFER", "len": 0.10, "type": "Xfer"}, {"name": "Dryer#1", "len": 1.85, "type": "Dryer"},
        {"name": "Dryer#2", "len": 1.85, "type": "Dryer"}, {"name": "Dryer#3", "len": 1.95, "type": "Dryer"},
        {"name": "XFER#1", "len": 3.39, "type": "Xfer"}, {"name": "Z#1", "len": 3.60, "type": "Heating"},
        {"name": "Z#2", "len": 2.75, "type": "Heating"}, {"name": "Z#3", "len": 2.30, "type": "Heating"},
        {"name": "Z#4", "len": 2.10, "type": "Heating"}, {"name": "Z#5", "len": 2.10, "type": "Heating"},
        {"name": "Z#6", "len": 1.90, "type": "Heating"}, {"name": "Z#7", "len": 1.63, "type": "Heating"},
        {"name": "WatCool#1", "len": 2.56, "type": "Cooling"}, {"name": "WatCool#2", "len": 1.90, "type": "Cooling"},
        {"name": "Exit curtain", "len": 2.35, "type": "Cooling"}, {"name": "AirCool#1", "len": 1.25, "type": "Cooling"},
        {"name": "AirCool#2", "len": 1.25, "type": "Cooling"}, {"name": "Exit", "len": 1.85, "type": "Exit"}
    ]
}

MODEL_DB = pd.DataFrame([
    {"Model": "New design standard dummy SUS304L", "Pitch (mm)": 350},
    {"Model": "Dummy SUS", "Pitch (mm)": 455},
    {"Model": "Dummy KN9", "Pitch (mm)": 790},
    {"Model": "KN9 #6", "Pitch (mm)": 760},
    {"Model": "D12A", "Pitch (mm)": 790},
    {"Model": "Y4L", "Pitch (mm)": 790},
    {"Model": "F44 / F48 50T", "Pitch (mm)": 660},
    {"Model": "P42QR/W42JK 63T", "Pitch (mm)": 760},
    {"Model": "CDS SU2 50T", "Pitch (mm)": 660},
    {"Model": "CDS DNGA 52T", "Pitch (mm)": 610}
])

ZONE_COLORS = {
    "Dryer": "#FFD700", "Debinder": "#FFA500", "Heating": "#FF4500",
    "Cooling": "#87CEFA", "Flux": "#9370DB", "Xfer": "#D3D3D3", "Exit": "#A9A9A9"
}

IMAGE_MAPPING = {
    "NB1": "image_c55827.png",
    "NB2": "image_c5aa27.png",
    "NB3": "image_c5aa7e.png"
}

# ==============================================================================
# 3. ส่วนของหน้าจอ Streamlit (UI)
# ==============================================================================
st.set_page_config(page_title="Furnace Timeline Tracker", page_icon="🔥", layout="wide")

st.title("🔥 Furnace Timeline Tracker & Simulation")
st.markdown("ระบบวิเคราะห์และจำลองตำแหน่งชิ้นงานในกระบวนการเตาอบประสาน (Brazing Furnace)")

# สร้าง Tabs หลัก
tab1, tab2 = st.tabs(["📂 File Upload & Layout", "🚚 Furnace Product Simulation"])

current_nb = "NB3" # Default fallback

# ------------------------------------------------------------------------------
# TAB 1: อัปโหลดไฟล์และแสดงรูป Layout
# ------------------------------------------------------------------------------
with tab1:
    st.markdown("### 1. อัปโหลดไฟล์ข้อมูล Datapaq (.PAQ)")
    uploaded_file = st.file_uploader("📂 ลากไฟล์ .PAQ มาวางที่นี่", type=["paq"])

    if uploaded_file is not None:
        filename = uploaded_file.name
        current_nb = identify_furnace_type(filename)
        
        st.success(f"✅ อัปโหลดไฟล์สำเร็จ: `{filename}`")
        st.info(f"📍 ตรวจพบว่าเป็นเตา: **{current_nb}**")
        
        # แสดงรูปภาพ Layout ตามที่ตรวจจับได้
        img_file = IMAGE_MAPPING.get(current_nb)
        
        if os.path.exists(img_file):
            st.image(img_file, caption=f"Brazing Line Layout - {current_nb}", use_container_width=True)
        else:
            st.warning(f"⚠️ ไม่พบไฟล์รูปภาพ `{img_file}` ในโฟลเดอร์ กรุณานำรูปมาวางไว้ในโฟลเดอร์เดียวกับโค้ด")
    else:
        st.info("กรุณาอัปโหลดไฟล์ .PAQ เพื่อเริ่มต้นการทำงาน หรือข้ามไปจำลองชิ้นงานที่ Tab 2 ได้เลย")

# ------------------------------------------------------------------------------
# TAB 2: จำลองตำแหน่งชิ้นงาน (2D Simulation)
# ------------------------------------------------------------------------------
with tab2:
    st.markdown("### 2. จำลองตำแหน่งชิ้นงานในเตาแบบอัตโนมัติ")
    st.markdown("อ้างอิงจากระยะ Pitch ของโมเดลและความยาวของแต่ละ Zone ในเตา")
    
    col1, col2 = st.columns(2)
    
    # เลือกเตา (กำหนด Default เป็นเตาที่ตรวจเจอจากการอัปโหลด)
    furnace_options = ["NB1", "NB2", "NB3"]
    default_index = furnace_options.index(current_nb) if current_nb in furnace_options else 2
    
    with col1:
        selected_nb = st.selectbox("เลือกเตา (Select Furnace):", furnace_options, index=default_index)
    with col2:
        selected_model = st.selectbox("เลือกโมเดล (Select Model):", MODEL_DB["Model"].tolist())

    # ดึงค่า Pitch
    pitch_mm = MODEL_DB.loc[MODEL_DB["Model"] == selected_model, "Pitch (mm)"].values[0]
    pitch_m = pitch_mm / 1000.0

    st.success(f"📍 **Model:** {selected_model} | **ระยะห่างต่อชิ้น (Pitch):** {pitch_mm} mm ({pitch_m:.3f} เมตร)")

    # คำนวณความยาวสะสมของแต่ละ Zone
    zones = FURNACE_ZONE_DATA[selected_nb]
    cumulative_len = 0
    furnace_zones_df = []

    for z in zones:
        start = cumulative_len
        end = cumulative_len + z["len"]
        furnace_zones_df.append({
            "Name": z["name"], "Type": z["type"], "Length": z["len"], 
            "Start": start, "End": end
        })
        cumulative_len = end

    total_furnace_length = cumulative_len
    df_zones = pd.DataFrame(furnace_zones_df)

    # สร้างตำแหน่งชิ้นงานทั้งหมดในเตา
    product_positions = np.arange(0, total_furnace_length, pitch_m)

    # วาดกราฟ 2D Map โครงสร้างเตา
    fig = go.Figure()

    # วาดแถบของแต่ละ Zone
    for idx, row in df_zones.iterrows():
        fig.add_shape(
            type="rect", x0=row["Start"], x1=row["End"], y0=0, y1=1,
            fillcolor=ZONE_COLORS.get(row["Type"], "#ccc"), line=dict(color="white", width=1),
            layer="below"
        )
        # ใส่ชื่อ Zone กึ่งกลาง
        fig.add_annotation(
            x=(row["Start"] + row["End"]) / 2, y=0.5,
            text=row["Name"], showarrow=False, textangle=-90,
            font=dict(size=11, color="black" if row["Type"] in ["Dryer", "Xfer", "Cooling"] else "white")
        )

    # วาดชิ้นงาน (Product Markers) ทับลงไป
    fig.add_trace(go.Scatter(
        x=product_positions, y=[0.5] * len(product_positions), # ให้อยู่กึ่งกลางความสูง
        mode="markers", name=f"ชิ้นงาน {selected_model}",
        marker=dict(symbol="square", size=12, color="#32CD32", line=dict(width=2, color="black")),
        hovertemplate="ตำแหน่ง: %{x:.2f} เมตร<extra></extra>"
    ))

    # นำภาพเตาขึ้นไปวางด้านบนโครงสร้าง (ถ้ามีไฟล์)
    img_file_sim = IMAGE_MAPPING.get(selected_nb)
    y_range = [-0.2, 1.2]
    
    if os.path.exists(img_file_sim):
        img = Image.open(img_file_sim)
        fig.add_layout_image(
            dict(
                source=img, xref="x", yref="y",
                x=0, y=2.5, sizex=total_furnace_length, sizey=1.5,
                sizing="stretch", opacity=1, layer="above"
            )
        )
        y_range = [-0.2, 2.6] # ขยายแกน Y เพื่อให้มีพื้นที่แสดงรูปด้านบน

    # ตั้งค่ากราฟให้สวยงาม
    fig.update_layout(
        title=f"Furnace Timeline: {selected_nb} (Total Length: {total_furnace_length:.2f} m)",
        xaxis=dict(title="Distance (Meters)", range=[0, total_furnace_length], tickmode="linear", tick0=0, dtick=2),
        yaxis=dict(visible=False, range=y_range),
        height=400, margin=dict(l=20, r=20, t=50, b=40),
        template="plotly_white", hovermode="x unified",
        showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)

    # ==============================================================================
    # ตารางสรุปจำนวนชิ้นงาน (WIP) ในแต่ละ Zone
    # ==============================================================================
    st.markdown("### 📋 สรุปจำนวนชิ้นงานที่กำลังอยู่ในแต่ละกระบวนการ (WIP)")
    
    # คำนวณว่าแต่ละชิ้นงานอยู่ในช่วงของ Zone ใด
    bins = [0] + df_zones["End"].tolist()
    labels = df_zones["Name"].tolist()
    zone_counts = pd.cut(product_positions, bins=bins, labels=labels, right=True).value_counts()
    
    df_wip = pd.DataFrame({"Zone / Process": zone_counts.index, "จำนวนชิ้นงาน (ชิ้น)": zone_counts.values})
    
    # กรองเอาเฉพาะโซนที่มีชิ้นงานอยู่ (จำนวน > 0)
    df_wip = df_wip[df_wip["จำนวนชิ้นงาน (ชิ้น)"] > 0]
    
    # แปลงตารางให้เป็นแนวนอนเพื่อให้ดูง่ายขึ้นบนหน้าจอ
    st.dataframe(df_wip.set_index("Zone / Process").T, use_container_width=True)
