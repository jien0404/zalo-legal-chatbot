# frontend/components/chat_elements.py
import streamlit as st

def display_chat_message(message):
    """Hiển thị một tin nhắn trong chat log."""
    role = message["role"]
    content = message.get("content")
    sources = message.get("sources")

    # === THAY ĐỔI: Thêm avatar cho từng role ===
    avatar_map = {"user": "👤", "assistant": "🤖"}
    avatar = avatar_map.get(role)

    with st.chat_message(role, avatar=avatar):
        st.markdown(content)
        
        if sources:
            st.markdown("---")
            st.caption("Nguồn tham khảo:")
            for i, source in enumerate(sources):
                expander_title = f"Nguồn {i+1}: Văn bản {source['doc_id']} (Score: {source['score']:.2f})"
                with st.expander(expander_title):
                    st.text(source['text'])