"""
Sindibad Chainlit UI — Executive chat interface for Doha Oasis Company.
Run: chainlit run chainlit_app.py
"""

from __future__ import annotations

import chainlit as cl
from chainlit.element import Plotly

from app.agent.sindibad_agent import SindibadAgent
from app.data.loader import load_data

_agent: SindibadAgent | None = None


@cl.on_chat_start
async def on_chat_start():
    global _agent
    load_data()
    _agent = SindibadAgent()

    await cl.Message(
        content=(
            "# Sindibad — Executive Strategic Advisor\n"
            "**Doha Oasis Company** | Virtual CEO Advisory\n\n"
            "كل إجابة مبنية على **Doha_Oasis_Sindibad_Database.xlsx** مع **جدول بيانات + رسم بياني** لكل مؤشر.\n\n"
            "**جرّب:**\n"
            "- *كيف أداء الإيرادات في قسم الضيافة؟*\n"
            "- *How is Engagement in IT?*\n"
            "- *Show SLA compliance in Operations*\n"
        ),
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    global _agent
    if _agent is None:
        load_data()
        _agent = SindibadAgent()

    query = message.content.strip()
    if not query:
        await cl.Message(content="Please enter a strategic question.").send()
        return

    result = _agent.ask(query, include_charts=True)
    display = _agent.format_for_display(result)

    # Send executive text first
    await cl.Message(content=display).send()

    # Send each chart in its own message for clear visibility
    ar = result.response.language == "ar"
    for i, artifact in enumerate(result.chart_artifacts, start=1):
        prefix = f"**رسم {i}:** {artifact.title}" if ar else f"**Chart {i}:** {artifact.title}"
        await cl.Message(
            content=prefix,
            elements=[
                Plotly(name=artifact.title, figure=artifact.figure, display="inline")
            ],
        ).send()

    if result.response.strategic_actions:
        actions = cl.Action(
            name="strategic_action",
            payload={"action": result.response.strategic_actions[0]},
            label="قبول الإجراء الاستراتيجي" if ar else "Accept Strategic Action",
        )
        await cl.Message(
            content=(
                "هل ترغب أن يتابع Sindibad التوصية المقترحة؟"
                if ar
                else "Would you like Sindibad to proceed with the recommended action?"
            ),
            actions=[actions],
        ).send()


@cl.action_callback("strategic_action")
async def on_action(action: cl.Action):
    payload = action.payload or {}
    action_text = payload.get("action", "Strategic initiative")
    await cl.Message(
        content=(
            f"**Action queued for review:** {action_text}\n\n"
            "_In production, this would trigger workflow integration with Adler ERP._"
        ),
    ).send()
