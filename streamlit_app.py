import streamlit as st

# สมมติว่าได้ชื่อไฟล์มาจากการอัปโหลด
filename = "20231012_EVO_Brazing.paq" 

# 1. เรียกใช้ฟังก์ชันเพื่อแยก NB
current_nb = identify_furnace_type(filename)

st.title(f"Furnace Timeline: {current_nb}")

# 2. ใช้เงื่อนไข (If-Else) เพื่อโหลดรูปภาพหรือ Timeline ที่ต่างกัน
if current_nb == "NB1":
    st.info("กำลังแสดงข้อมูล Timeline และรูปภาพของเตา NB1")
    # st.image("nb1_brazing_line.png", use_container_width=True)
    
elif current_nb == "NB2":
    st.info("กำลังแสดงข้อมูล Timeline และรูปภาพของเตา NB2")
    # st.image("nb2_brazing_line.png", use_container_width=True)
    
elif current_nb == "NB3":
    st.info("กำลังแสดงข้อมูล Timeline และรูปภาพของเตา NB3")
    # st.image("nb3_brazing_line.png", use_container_width=True)
