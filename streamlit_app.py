import streamlit as st
import re

# ==========================================
# 1. ฟังก์ชันสำหรับแยกประเภทเตา (NB1, NB2, NB3)
# ==========================================
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

# ==========================================
# 2. ส่วนของหน้าจอ Streamlit (UI)
# ==========================================
st.set_page_config(page_title="Furnace Timeline Tracker", page_icon="🔥", layout="centered")

st.title("🔥 Furnace Timeline Tracker")
st.markdown("ระบบวิเคราะห์และแสดงไทม์ไลน์เตาเผาจากชื่อไฟล์")

# ช่องสำหรับอัปโหลดไฟล์
uploaded_file = st.file_uploader("📂 อัปโหลดไฟล์ .PAQ ของคุณที่นี่", type=["paq"])

if uploaded_file is not None:
    # ดึงชื่อไฟล์มาใช้งาน
    filename = uploaded_file.name
    st.write(f"**ไฟล์ที่อัปโหลด:** `{filename}`")
    
    # เรียกใช้ฟังก์ชันด้านบนเพื่อเช็คว่าเป็น NB อะไร
    current_nb = identify_furnace_type(filename)
    
    st.subheader(f"📍 ตรวจพบเตา: {current_nb}")
    
    # แสดงผลรูปภาพ/ไทม์ไลน์ ตาม NB ที่แยกได้
    if current_nb == "NB1":
        st.success("✅ โหลดไทม์ไลน์และตั้งค่าสำหรับเตา NB1")
        # แสดงภาพของ NB1 (ภาพซ้าย)
        st.image("image_c55827.png", caption="Brazing Line - NB1", use_container_width=True)
        
    elif current_nb == "NB2":
        st.info("✅ โหลดไทม์ไลน์และตั้งค่าสำหรับเตา NB2")
        # แสดงภาพของ NB2 (ภาพกลาง)
        st.image("image_c5aa27.png", caption="Brazing Line - NB2", use_container_width=True)
        
    elif current_nb == "NB3":
        st.warning("✅ โหลดไทม์ไลน์และตั้งค่าสำหรับเตา NB3")
        # แสดงภาพของ NB3 (ภาพขวา)
        st.image("image_c5aa7e.png", caption="Brazing Line - NB3", use_container_width=True)

else:
    st.info("กรุณาอัปโหลดไฟล์ .PAQ เพื่อเริ่มต้นการทำงาน")
