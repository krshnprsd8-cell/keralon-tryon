import os
import urllib.request
import json
import tempfile
import gradio as gr
from gradio_client import Client, handle_file

HF_TOKEN = os.getenv("HF_TOKEN", "")
SHOPIFY_STORE = "https://keralon-in.myshopify.com"

MODEL_PRESETS = {
    "female": "model_female.png",
    "male": "model_male.png",
}

FALLBACK_CATALOG = {
    'Better Luck Next Lifetime — 240 GSM Oversized Tee (Rs. 1,099)': {
        "image": "https://keralon-in.shopify.com",
        "desc": "off-white cream heavyweight oversized streetwear t-shirt with cosmic hourglass serpent and roses graphic print",
        "url": SHOPIFY_STORE,
    },
    'Deadline Coffee // No Sleep Club — 240 GSM Oversized Tee (Rs. 1,199)': {
        "image": "tee_deadline_coffee.png",
        "desc": "off-white cream heavyweight oversized streetwear t-shirt with box-head coffee graphic print",
        "url": SHOPIFY_STORE,
    },
    'Keralon "Fortis Fortuna Adiuvat" Stoic Tee (Rs. 899)': {
        "image": "tee_fortis_fortuna.png",
        "desc": "black heavyweight oversized stoic lion graphic t-shirt",
        "url": SHOPIFY_STORE,
    },
    'Keralon "Midnight Drift" Neon Oversized Tee (Rs. 899)': {
        "image": "tee_midnight_drift.png",
        "desc": "jet-black heavyweight oversized neon t-shirt",
        "url": SHOPIFY_STORE,
    },
    'Keralon "Busy Year" Oversized Tee (Rs. 799)': {
        "image": "tee_busy_year.png",
        "desc": "white heavyweight oversized streetwear graphic t-shirt",
        "url": SHOPIFY_STORE,
    },
}


def get_local_image(image_source):
    if not str(image_source).startswith("http"):
        return image_source
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tmp.close()
    req = urllib.request.Request(image_source, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp, open(tmp.name, "wb") as f:
        f.write(resp.read())
    return tmp.name


def run_vton(person_path, garment_source, garment_desc):
    if not person_path:
        raise gr.Error("Please upload a clear photo of yourself or tap a Male/Female model button.")
    if not garment_source:
        raise gr.Error("No garment image detected.")

    garm_local = get_local_image(garment_source)
    person_local = get_local_image(person_path)

    try:
        client = Client("yisol/IDM-VTON", token=HF_TOKEN if HF_TOKEN else None)
        result = client.predict(
            dict={"background": handle_file(person_local), "layers": [], "composite": None},
            garm_img=handle_file(garm_local),
            garment_des=garment_desc or "oversized streetwear t-shirt",
            is_checked=True,
            is_checked_crop=False,
            denoise_steps=30,
            seed=42,
            api_name="/tryon",
        )
        return next(iter(result)) if isinstance(result, (list, tuple)) else result
    except Exception as e:
        raise gr.Error(f"AI Fitting Room busy—please tap again in a few seconds. ({e})")


def try_on_user(user_photo, active_garm_url, selected_tee):
    item = FALLBACK_CATALOG.get(selected_tee, next(iter(FALLBACK_CATALOG.values())))
    garm_src = active_garm_url.strip() if active_garm_url and active_garm_url.strip() else item.get("image", "")
    return run_vton(user_photo, garm_src, item.get("desc", "oversized streetwear t-shirt"))


def try_on_preset(gender, active_garm_url, selected_tee):
    item = FALLBACK_CATALOG.get(selected_tee, next(iter(FALLBACK_CATALOG.values())))
    garm_src = active_garm_url.strip() if active_garm_url and active_garm_url.strip() else item.get("image", "")
    model_url = MODEL_PRESETS.get(gender, "")
    return run_vton(model_url, garm_src, item.get("desc", "oversized streetwear t-shirt"))


def init_from_url(request: gr.Request):
    params = dict(request.query_params) if request and request.query_params else {}
    garm_url = params.get("garm", "").strip()
    title = params.get("title", "").strip()

    if garm_url:
        header_md = f"### ✨ Trying On: **{title or 'Keralon Oversized Tee'}**"
        return (
            garm_url,
            gr.update(visible=False),
            gr.update(value=garm_url, visible=True),
            header_md,
        )

    first_key = next(iter(FALLBACK_CATALOG.keys()))
    first_img = FALLBACK_CATALOG.get(first_key, {}).get("image", "")
    return (
        "",
        gr.update(visible=True, value=first_key),
        gr.update(value=first_img, visible=True),
        "### ✨ Keralon AI Virtual Fitting Room",
    )


def on_dropdown_change(selected_tee):
    item = FALLBACK_CATALOG.get(selected_tee, next(iter(FALLBACK_CATALOG.values())))
    return item.get("image", "")


CUSTOM_CSS = """
.gradio-container { max-width: 780px !important; margin: auto !important; }
.pill-btn button { border-radius: 999px !important; font-weight: 700 !important; padding: 12px 18px !important; }
"""

with gr.Blocks(title="Keralon Try It On", theme=gr.themes.Soft(), css=CUSTOM_CSS) as demo:
    active_garm_state = gr.State("")
    title_banner = gr.Markdown("### ✨ Keralon AI Virtual Fitting Room")

    with gr.Row():
        with gr.Column(scale=1):
            tee_dropdown = gr.Dropdown(
                choices=list(FALLBACK_CATALOG.keys()),
                value=next(iter(FALLBACK_CATALOG.keys())),
                label="Select Tee",
                visible=True,
            )
            garment_img = gr.Image(label="Selected Tee", interactive=False, height=260)

        with gr.Column(scale=1):
            result_img = gr.Image(label="Live Fit Preview", height=320)

    with gr.Row(elem_classes="pill-btn"):
        female_btn = gr.Button("👩 Try on a female model", variant="secondary")
        male_btn = gr.Button("👨 Try on a male model", variant="secondary")

    with gr.Accordion("📷 Or upload a photo of yourself (Try on you)", open=False):
        user_photo = gr.Image(type="filepath", label="Upload Clear Front-Facing Photo", height=220)
        user_btn = gr.Button("✨ Try on you", variant="primary", elem_classes="pill-btn")

    demo.load(
        fn=init_from_url,
        inputs=(),
        outputs=(active_garm_state, tee_dropdown, garment_img, title_banner),
    )
    tee_dropdown.change(fn=on_dropdown_change, inputs=(tee_dropdown,), outputs=(garment_img,))
    female_btn.click(
        fn=lambda g, t: try_on_preset("female", g, t),
        inputs=(active_garm_state, tee_dropdown),
        outputs=(result_img,),
    )
    male_btn.click(
        fn=lambda g, t: try_on_preset("male", g, t),
        inputs=(active_garm_state, tee_dropdown),
        outputs=(result_img,),
    )
    user_btn.click(
        fn=try_on_user,
        inputs=(user_photo, active_garm_state, tee_dropdown),
        outputs=(result_img,),
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
        allowed_paths=["."],
        ssr_mode=False,
    )

