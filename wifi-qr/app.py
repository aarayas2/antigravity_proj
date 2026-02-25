import streamlit as st
import segno
from segno import helpers
import io
import base64

# Configure page
st.set_page_config(
    page_title="WiFi QR Code Generator",
    page_icon="📶",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for a beautiful, premium modern dark UI
st.markdown("""
<style>
    /* Global App Background */
    .stApp {
        background: linear-gradient(135deg, #121420 0%, #1e2130 100%);
        color: #e2e8f0;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #f8fafc !important;
        font-family: 'Inter', 'Roboto', sans-serif;
    }

    .main-header {
        text-align: center;
        margin-bottom: 2rem;
        background: -webkit-linear-gradient(45deg, #4facfe 0%, #00f2fe 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 3rem !important;
    }
    
    .sub-header {
        text-align: center;
        color: #94a3b8 !important;
        margin-bottom: 3rem;
        font-size: 1.2rem;
        font-family: 'Inter', sans-serif;
    }

    /* Input fields and Selectboxes */
    .stTextInput > div > div > input, 
    .stSelectbox > div > div > div {
        background-color: #1e293b !important;
        color: #f8fafc !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.3s ease;
    }
    
    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > div:focus {
        border-color: #38bdf8 !important;
        box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2) !important;
    }
    
    /* Input Labels */
    .stTextInput label, .stSelectbox label, .stCheckbox label {
        color: #cbd5e1 !important;
        font-weight: 500 !important;
    }

    /* Expanders */
    .streamlit-expanderHeader {
        background-color: rgba(30, 41, 59, 0.5) !important;
        border-radius: 8px !important;
        border: 1px solid #334155 !important;
        color: #f8fafc !important;
        font-weight: 600 !important;
    }
    
    .streamlit-expanderContent {
        background-color: rgba(15, 23, 42, 0.3) !important;
        border: 1px solid #334155 !important;
        border-top: none !important;
        border-bottom-left-radius: 8px !important;
        border-bottom-right-radius: 8px !important;
        padding: 1rem !important;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%) !important;
        color: white !important;
        border: none !important;
        padding: 0.75rem 2rem !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        width: 100% !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05) !important;
        background: linear-gradient(135deg, #38bdf8 0%, #3b82f6 100%) !important;
        border: none !important;
        color: white !important;
    }
    
    .stButton > button:active {
        transform: translateY(0) !important;
    }
    
    /* Download Button Specific */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
    }
    
    .stDownloadButton > button:hover {
        background: linear-gradient(135deg, #34d399 0%, #10b981 100%) !important;
    }

    /* Panel container for main form */
    .css-1r6slb0, .css-1r6slb0 > div {
        background-color: rgba(30, 41, 59, 0.6) !important;
        border-radius: 12px !important;
        padding: 2rem !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04) !important;
        backdrop-filter: blur(10px);
    }

    /* QR Code Display Container */
    .qr-container {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 2rem;
        background-color: white;
        border-radius: 16px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        margin-top: 2rem;
        margin-bottom: 2rem;
        transition: transform 0.3s ease;
    }
    .qr-container:hover {
        transform: scale(1.02);
    }
    
    /* Alerts/Warnings */
    .stAlert {
        background-color: rgba(239, 68, 68, 0.1) !important;
        color: #fca5a5 !important;
        border: 1px solid rgba(239, 68, 68, 0.2) !important;
        border-radius: 8px !important;
    }
</style>
""", unsafe_allow_html=True)

# Application Header
st.markdown('<h1 class="main-header">Wi-Fi QR Code Generator</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Instantly create high-quality QR codes for your wireless network.<br>Guests can scan to connect without typing passwords!</p>', unsafe_allow_html=True)

# Main Form Area
with st.container():
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Network Details")
        ssid = st.text_input("Network Name (SSID)", placeholder="e.g. My Awesome Home Wi-Fi", help="The name of your wireless network.")
        password = st.text_input("Password", type="password", placeholder="Enter network password", help="Leave blank if the network is open.")
        
        col_enc, col_hidden = st.columns(2)
        with col_enc:
            security = st.selectbox("Encryption Type", options=["WPA/WPA2/WPA3", "WEP", "None"], help="Most modern routers use WPA/WPA2/WPA3.")
        with col_hidden:
            st.write("") # Spacer
            st.write("") # Spacer
            hidden = st.checkbox("Hidden Network?", help="Check this if your network SSID is not broadcasted.")

    with col2:
        st.markdown("### Customization")
        # Map nice names to internal representations
        color_dark = st.color_picker("QR Code Color", value="#000000", help="The color of the QR code modules.")
        color_light = st.color_picker("Background Color", value="#FFFFFF", help="The background color behind the QR code.")
        scale = st.slider("Size (Scale)", min_value=3, max_value=20, value=8, help="Determines the size of the generated image.")
        border = st.slider("Border Size", min_value=1, max_value=10, value=4, help="The quiet zone padding around the QR code.")

# Generate Logic
st.markdown("---")
col_center, _, _ = st.columns([1, 1, 1]) # dummy layout just to center button somewhat if needed, though we styled it to 100% width

if st.button("Generate QR Code"):
    if not ssid:
        st.error("Please enter a Network Name (SSID).")
    elif security != "None" and not password:
        st.warning("You selected an encryption type but didn't provide a password. If the network has no password, select 'None' for Encryption Type.")
    else:
        # Map security selection to segno values
        sec_map = {
            "WPA/WPA2/WPA3": "WPA",
            "WEP": "WEP",
            "None": "nopass"
        }
        
        try:
            # Create the QR code
            qr = helpers.make_wifi(
                ssid=ssid,
                password=password if security != "None" else '',
                security=sec_map[security],
                hidden=hidden
            )
            
            # Save QR to a buffer (PNG)
            buff = io.BytesIO()
            qr.save(
                buff, 
                kind='png', 
                scale=scale, 
                border=border, 
                dark=color_dark, 
                light=color_light
            )
            
            # encode for display in HTML
            img_str = base64.b64encode(buff.getvalue()).decode()
            img_html = f'<div class="qr-container"><img src="data:image/png;base64,{img_str}" alt="WiFi QR Code" style="max-width: 100%; border-radius: 4px;"></div>'
            
            st.markdown("### Your QR Code is Ready!")
            st.markdown(img_html, unsafe_allow_html=True)
            
            # Provide Download Buttons
            st.markdown("<br>", unsafe_allow_html=True)
            dl_col1, _, _ = st.columns([2, 1, 1])
            with dl_col1:
                st.download_button(
                    label="⬇️ Download QR Code (PNG)",
                    data=buff.getvalue(),
                    file_name=f"{ssid}_wifi_qr.png",
                    mime="image/png",
                )
                
            # Optional SVG Download
            svg_buff = io.BytesIO()
            qr.save(
                svg_buff, 
                kind='svg', 
                scale=scale, 
                border=border, 
                dark=color_dark, 
                light=color_light
            )
            with dl_col1:
                st.download_button(
                    label="⬇️ Download QR Code (SVG - Vector)",
                    data=svg_buff.getvalue(),
                    file_name=f"{ssid}_wifi_qr.svg",
                    mime="image/svg+xml",
                )
                    
            if st.session_state.get('show_fireworks', True):
                st.balloons()
                st.session_state['show_fireworks'] = False

        except Exception as e:
            st.error(f"An error occurred while generating the QR code: {str(e)}")

# Footer
st.markdown("""
<div style="text-align: center; margin-top: 4rem; color: #64748b; font-size: 0.8rem;">
    <p>Simply point your smartphone camera at the QR code to connect instantly.</p>
</div>
""", unsafe_allow_html=True)
