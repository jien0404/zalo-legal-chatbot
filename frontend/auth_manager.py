# frontend/auth_manager.py
import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

def initialize_authenticator():
    """
    Tải cấu hình từ file YAML và khởi tạo đối tượng authenticator.
    """
    try:
        with open('./config.yaml', 'r', encoding='utf-8') as file:
            config = yaml.load(file, Loader=SafeLoader)
    except FileNotFoundError:
        st.error("Lỗi: Không tìm thấy file 'config.yaml'. Vui lòng tạo file này.")
        st.stop()

    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days'],
        config['preauthorized']
    )
    return authenticator