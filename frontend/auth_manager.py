# frontend/auth_manager.py
import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

def update_config(config):
    """Ghi lại file config.yaml với thông tin người dùng mới."""
    with open('./config.yaml', 'w', encoding='utf-8') as file:
        yaml.dump(config, file, default_flow_style=False, allow_unicode=True)

def initialize_authenticator():
    try:
        with open('./config.yaml', 'r', encoding='utf-8') as file:
            config = yaml.load(file, Loader=SafeLoader)
            
    except FileNotFoundError:
        st.error("Lỗi: Không tìm thấy file 'config.yaml'.")
        st.stop()

    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days'],
        config['preauthorized']
    )
    # Trả về cả config để có thể cập nhật
    return authenticator, config