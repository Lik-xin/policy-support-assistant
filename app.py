from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from support_reply_assistant.policies import load_policy_sections
from support_reply_assistant.schemas import TicketContext
from support_reply_assistant.workflows import generate_baseline_reply, generate_grounded_reply


ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

st.set_page_config(page_title="Policy-Grounded Support Reply Assistant", layout="wide")

st.title("Policy-Grounded Support Reply Assistant")
st.caption("A narrow GenAI workflow for drafting first-response support replies and flagging risky tickets.")

handbook_path = ROOT / "data" / "policy_handbook.md"
policy_sections = load_policy_sections(handbook_path)

with st.sidebar:
    st.header("Example cases")
    st.write("The repo includes eight synthetic tickets in `data/test_tickets.csv` for evaluation.")
    st.write("This app compares a prompt-only baseline with a policy-grounded version.")

left, right = st.columns([1, 1])

with left:
    ticket = st.text_area(
        "Customer ticket",
        value="I forgot to cancel before renewal three days ago. We barely used the product this month. Can you help with a refund?",
        height=180,
    )
    account_tier = st.selectbox("Account tier", ["Free", "Pro", "Enterprise"], index=1)
    ownership_verified = st.checkbox("Ownership verified", value=True)
    run_compare = st.button("Compare baseline vs grounded")

if run_compare:
    context = TicketContext(
        customer_ticket=ticket,
        account_tier=account_tier,
        ownership_verified=ownership_verified,
    )

    try:
        with st.spinner("Generating support drafts..."):
            baseline = generate_baseline_reply(context)
            grounded, retrieved = generate_grounded_reply(context, policy_sections)

        with left:
            st.subheader("Prompt-only baseline")
            st.json(json.loads(baseline.model_dump_json(indent=2)))

        with right:
            st.subheader("Policy-grounded workflow")
            st.json(json.loads(grounded.model_dump_json(indent=2)))

            st.markdown("**Retrieved policy sections**")
            for section in retrieved:
                st.markdown(f"- `{section.policy_id}`: {section.title}")

            with st.expander("Show retrieved policy text"):
                for section in retrieved:
                    st.markdown(f"### {section.policy_id} - {section.title}")
                    st.write(section.body)
    except Exception as exc:
        st.error(str(exc))
else:
    with right:
        st.info("Enter a ticket and click **Compare baseline vs grounded**.")
