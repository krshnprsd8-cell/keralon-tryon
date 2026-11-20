import os
import gradio as gr
from gradio_client import Client, handle_file

# --- PASTE YOUR HUGGING FACE READ TOKEN HERE ---
HF_TOKEN = os.getenv("HF_TOKEN", "")

# --- YOUR LIVE KERALON DROP 01 CATALOG ---
KERALON_CATALOG = {
    'Keralon "Busy Year" Oversized Tee (Rs. 799)': {
        "image": "tee_busy_year.png",
        "desc": "white heavyweight oversized streetwear graphic t-shirt",
        "url": "https://myshopify.com",
    },
    'Keralon "Midnight Drift" Neon Oversized Tee (Rs. 899)': {
        "image": "tee_midnight_drift.png",
        "desc": "jet-black heavyweight oversized neon t-shirt",
        "url": "https://myshopify.com",
    },
    'Keralon "Fortis Fortuna Adiuvat" Stoic Tee (Rs. 899)': {
        "image": "tee_fortis_fortuna.png",
        "desc": "black heavyweight oversized stoic lion graphic t-shirt",
        "url": "https://myshopify.com",
    },
    'Deadline Coffee // No Sleep Club — 240 GSM Oversized Tee (Rs. 1,199)': {
        "image": "tee_deadline_coffee.png",
        "desc": "off-white cream heavyweight oversized streetwear t-shirt with box-head coffee graphic print",
        "url": "https://myshopify.com",
    },
}


VTON_SPACES = ["yisol/IDM-VTON", "jjlealse/IDM-VTON"]


def run_virtual_tryon(user_photo_path, selected_tee_name):
    if not user_photo_path:
        raise gr.Error("Please upload a clear front-facing photo of yourself first.")

    item = KERALON_CATALOG[selected_tee_name]
    garment_path = item["image"]
    if not os.path.exists(garment_path):
        raise gr.Error(
            f"Store setup missing '{garment_path}'. Place all 3 tee mockups in the app folder."
        )

    last_error = None
    for space_id in VTON_SPACES:
        try:
            client = Client(space_id, token=HF_TOKEN)
            result = client.predict(
                dict={"background": handle_file(user_photo_path), "layers": [], "composite": None},
                garm_img=handle_file(garment_path),
                garment_des=item["desc"],
                is_checked=True,
                is_checked_crop=False,
                denoise_steps=30,
                seed=42,
                api_name="/tryon",
            )
            output_img = result[0] if isinstance(result, (list, tuple)) else result
            buy_banner = f"### Like the fit? [Order {selected_tee_name} on Keralon â†’]({item['url']})"
            return output_img, buy_banner
        except Exception as e:
            last_error = e
            continue

    raise gr.Error(f"All free GPU fitting rooms are currently busy. Try again shortly. ({last_error})")


def preview_garment(selected_tee_name):
    path = KERALON_CATALOG[selected_tee_name]["image"]
    return path if os.path.exists(path) else None


with gr.Blocks(theme=gr.themes.Monochrome(), title="KERALON // Virtual Fitting Room") as demo:
    gr.Markdown(
        """
        # KERALON // VIRTUAL FITTING ROOM
        **See how Drop 01 fits before you order.** Upload a clear front-facing photo, choose your oversized tee, and generate your fit preview in ~20 seconds.
        """
    )

    with gr.Row():
        with gr.Column(scale=1):
            tee_selector = gr.Dropdown(
                choices=list(KERALON_CATALOG.keys()),
                value=list(KERALON_CATALOG.keys())[0],
                label="1. Select Keralon Drop 01 Tee",
            )
            garment_preview = gr.Image(
                value=preview_garment(list(KERALON_CATALOG.keys())[0]),
                label="Selected Garment",
                interactive=False,
                height=260,
            )
            user_input = gr.Image(
                type="filepath",
                label="2. Upload Your Photo (Front-facing, good lighting)",
                height=320,
            )
            tryon_btn = gr.Button("TRY IT ON VIRTUALLY", variant="primary", size="lg")

        with gr.Column(scale=1):
            result_output = gr.Image(label="Your Keralon Fit Preview", height=540)
            cta_markdown = gr.Markdown("")

    tee_selector.change(fn=preview_garment, inputs=tee_selector, outputs=garment_preview)
    tryon_btn.click(
        fn=run_virtual_tryon,
        inputs=[user_input, tee_selector],
        outputs=[result_output, cta_markdown],
    )

if __name__ == "__main__":
    # share=True generates a public https://gradio.live URL you can link in Shopify!
    demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)))

