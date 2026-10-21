"""Registration page."""

import streamlit as st
from frontend.api_client import api_client
from frontend.utils.session import set_user_session


def render_register_page():
    st.markdown(
        """
        <div style="max-width: 480px; margin: 0 auto; padding-top: 20px;">
            <h1 style="color: #6366f1; text-align: center;">⚡ ContextGPT</h1>
            <p style="text-align: center; color: #888;">Create an account to start summarizing and exploring documents.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            st.subheader("✨ Register")
            name = st.text_input("Full Name", placeholder="Jane Doe", key="reg_name")
            email = st.text_input("Email Address", placeholder="jane@example.com", key="reg_email")
            password = st.text_input("Password (min 8 characters)", type="password", key="reg_password")
            password_confirm = st.text_input("Confirm Password", type="password", key="reg_password_confirm")

            if st.button("Create Account", key="btn_register_submit", type="primary", use_container_width=True):
                if not name or not email or not password or not password_confirm:
                    st.error("Please fill in all required fields.")
                elif len(password) < 8:
                    st.error("Password must be at least 8 characters long.")
                elif password != password_confirm:
                    st.error("Passwords do not match.")
                else:
                    with st.spinner("Creating your account..."):
                        try:
                            # 1. Register
                            api_client.register(
                                name=name.strip(),
                                email=email.strip(),
                                password=password.strip(),
                                password_confirm=password_confirm.strip(),
                            )
                            # 2. Automatically log in
                            token_data = api_client.login(email.strip(), password.strip())

                            st.session_state["access_token"] = token_data.get("access_token")
                            st.session_state["refresh_token"] = token_data.get("refresh_token")
                            user_data = api_client.get_me()
                            set_user_session(user_data, token_data)
                            st.success("Account created successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

            st.markdown("---")
            st.markdown("<p style='text-align:center;'>Already registered?</p>", unsafe_allow_html=True)
            if st.button("Back to Sign In", key="btn_goto_login", use_container_width=True):
                st.session_state["current_page"] = "Login"
                st.rerun()
