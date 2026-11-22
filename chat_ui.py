"""
chat_ui - the Gradio chat page that every lab uses.

All the Gradio code lives here, so each lab file shows only its MEMORY logic.
You do not run this file. The labs import it.

Each lab gives us one function:

    respond(message, session_id) -> (reply_text, panel_text)

The panel on the right shows what the model was actually given on that turn.
That is the point of the mission: memory is what you store, context is what you send.
"""

import gradio as gr


def build_chat(respond, title, subtitle, steps, sessions=None, on_session_change=None, show_session=True,
               switch_label=None):
    """
    Build the chat page and return it.

    respond           : function(message, session_id) -> (reply, panel_text)
    steps             : list of "try this" instructions shown on screen
    sessions          : optional list of session names, shown as a dropdown
    on_session_change : optional function(session_id) -> the chat to show for that session
    show_session      : False hides the session box (lab 01 does not need it)
    switch_label      : optional on/off switch. If given, respond also receives its value:
                        respond(message, session_id, switch_is_on)
    """
    with gr.Blocks(title=title) as page:
        gr.Markdown("# " + title + "\n" + subtitle)

        instructions = "### Try this, in order\n"
        number = 1
        for step in steps:
            instructions = instructions + str(number) + ". " + step + "\n"
            number = number + 1
        with gr.Accordion("How to use this lab", open=True):
            gr.Markdown(instructions)

        with gr.Row():
            with gr.Column(scale=2):
                chatbot = gr.Chatbot(height=420, label="Chat")
                box = gr.Textbox(label="Your message", placeholder="Type here and press Enter")
            with gr.Column(scale=1):
                if sessions is None:
                    picker = gr.Textbox(value="session-1", label="Session (thread_id)", visible=show_session)
                else:
                    picker = gr.Dropdown(choices=sessions, value=sessions[0], label="Session (thread_id)")
                switch = None
                if switch_label is not None:
                    switch = gr.Checkbox(value=False, label=switch_label)
                panel = gr.Markdown("What the model was sent will appear here.")

        # "extra" is empty, or holds the switch value when the lab has a switch.
        def on_submit(message, history, session_id, *extra):
            if message.strip() == "":
                return "", history, gr.update()
            reply, panel_text = respond(message, session_id, *extra)
            # DeepSeek sometimes ends a reply with this marker and then keeps writing
            # unrelated text. Keep only what comes before the marker.
            reply = reply.split("<|endoftext|>")[0].strip()
            history = history + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": reply},
            ]
            return "", history, panel_text

        inputs = [box, chatbot, picker]
        if switch is not None:
            inputs.append(switch)
        box.submit(on_submit, inputs, [box, chatbot, panel])

        if on_session_change is not None:
            def on_switch(session_id):
                return on_session_change(session_id), "Switched to " + session_id
            picker.change(on_switch, [picker], [chatbot, panel])

    return page
