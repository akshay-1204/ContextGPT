"""Login page."""

import streamlit as st
from frontend.api_client import api_client
from frontend.utils.session import set_user_session


def render_login_page():
    st.markdown(
        """
        <div style="max-width: 480px; margin: 0 auto; padding-top: 30px;">
            <h1 style="color: #6366f1; text-align: center;">⚡ ContextGPT</h1>
            <p style="text-align: center; color: #888;">Understand more. Ask anything.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            st.subheader("🔑 Sign In")
            email = st.text_input("Email Address", placeholder="user@example.com", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")

            if st.button("Sign In", key="btn_login_submit", type="primary", use_container_width=True):
                if not email or not password:
                    st.error("Please enter both email and password.")
                else:
                    with st.spinner("Authenticating..."):
                        try:
                            token_data = api_client.login(email.strip(), password.strip())
                            # Temporarily save tokens into session state so get_me() works

                            st.session_state["access_token"] = token_data.get("access_token")
                            st.session_state["refresh_token"] = token_data.get("refresh_token")
                            user_data = api_client.get_me()
                            set_user_session(user_data, token_data)
                            st.success(f"Welcome back, {user_data.get('name')}!")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

            st.markdown("---")
            st.markdown("<p style='text-align:center;'>Don't have an account yet?</p>", unsafe_allow_html=True)
            if st.button("Create ContextGPT Account", key="btn_goto_register", use_container_width=True):
                st.session_state["current_page"] = "Register"
                st.rerun()
