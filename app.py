from typing import Any, List, Tuple

import gradio as gr

from sidekick import Sidekick


async def setup() -> Sidekick:
    sidekick = Sidekick()
    await sidekick.setup()
    return sidekick


async def process_message(
    sidekick: Sidekick, message: str, success_criteria: str, history: List[Any]
) -> Tuple[List[Any], Sidekick]:
    results = await sidekick.run_superstep(message, success_criteria, history)
    return results, sidekick


async def reset(sidekick: Sidekick) -> Tuple[str, str, None, Sidekick]:
    """Reset the UI and create a fresh Sidekick, cleaning up the existing one if present."""
    try:
        if sidekick:
            sidekick.free_resources()
    except Exception:
        pass  # Ignore cleanup failures during reset

    new_sidekick = Sidekick()
    await new_sidekick.setup()
    return "", "", None, new_sidekick


def free_resources(sidekick: Sidekick) -> None:
    try:
        if sidekick:
            sidekick.free_resources()
    except Exception as e:
        print(f"Exception during cleanup: {e}")


with gr.Blocks(title="Sidekick", theme=gr.themes.Default(primary_hue="emerald")) as ui:
    gr.Markdown("## Sidekick Personal Co-Worker")
    sidekick = gr.State(delete_callback=free_resources)

    # Chatbot section
    with gr.Row():
        chatbot = gr.Chatbot(
            label="Sidekick", height=300, type="messages", resizable=True
        )

    # Input section
    with gr.Group():
        with gr.Row():
            message = gr.Textbox(
                show_label=False, placeholder="Your request to the Sidekick"
            )
        with gr.Row():
            success_criteria = gr.Textbox(
                show_label=False, placeholder="What are your success criteria?"
            )

    # Buttons section
    with gr.Row():
        reset_button = gr.Button("Reset", variant="stop")
        go_button = gr.Button("Go!", variant="primary")

    ui.load(setup, [], [sidekick])
    message.submit(
        process_message,
        [sidekick, message, success_criteria, chatbot],
        [chatbot, sidekick],
    )
    success_criteria.submit(
        process_message,
        [sidekick, message, success_criteria, chatbot],
        [chatbot, sidekick],
    )
    go_button.click(
        process_message,
        [sidekick, message, success_criteria, chatbot],
        [chatbot, sidekick],
    )
    reset_button.click(
        reset, [sidekick], [message, success_criteria, chatbot, sidekick]
    )


if __name__ == "__main__":
    ui.launch()
