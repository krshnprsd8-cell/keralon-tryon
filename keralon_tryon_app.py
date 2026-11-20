import os
import urllib.request
import json
import tempfile
import gradio as gr
from gradio_client import Client, handle_file

HF_TOKEN = os.getenv("HF_TOKEN", "")
SHOPIFY_STORE = "https://myshopify.com"

FALLBACK_CATALOG = {
    'Keralon "Busy Year" Oversized Tee (Rs. 799)': {
        "image": "tee_busy_year.png",
        "desc": "white heavyweight oversized streetwear graphic t-shirt",
        "url": SHOPIFY_STORE,
    },
    'Keralon "Midnight Drift" Neon Oversized Tee (Rs. 899)': {
        "image": "tee_midnight_drift.png",
        "desc": "jet-black heavyweight oversized neon t-shirt",
        "url": SHOPIFY_STORE,
    },
    'Keralon "Fortis Fortuna Adiuvat" Stoic Tee (Rs. 899)': {
        "image": "tee_fortis_fortuna.png",
        "desc": "black heavyweight oversized stoic lion graphic t-shirt",
        "url": SHOPIFY_STORE,
    },
    'Deadline Coffee // No Sleep Club — 240 GSM Oversized Tee (Rs. 1,199)': {
        "image": "tee_deadline_coffee.png",
        "desc": "off-white cream heavyweight oversized streetwear t-shirt with box-head coffee graphic print",
        "url": SHOPIFY_STORE,
    },
}


def fetch_shopify_tees():
    try:
        req = urllib.request.Request(
            f"{SHOPIFY_STORE}/products.json?limit=50",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        catalog = {}
        apparel_words = ("tee", "t-shirt", "shirt", "oversized", "hoodie", "gsm", "drop")

        for p in data.get("products", []):
            title = p.get("title", "").strip()
            ptype = p.get("product_type", "").lower()
            raw_tags = p.get("tags", [])
            tags = " ".join(raw_tags).lower() if isinstance(raw_tags, list) else str(raw_tags).lower()
            check_text = f"{title.lower()} {ptype} {tags}"

            if not any(word in check_text for word in apparel_words):
                continue

            images = p.get("images", [])
            variants = p.get("variants", [])
            if not images or not variants:
                continue

            first_variant = variants[0]
            first_image = images[0]
            raw_price = str(first_variant.get("price", "")).replace(".00", "")
            label = f"{title} (Rs. {raw_price})" if raw_price else title
            catalog[label] = {
                "image": first_image["src"],
                "desc": f"{title} heavyweight oversized streetwear t-shirt",
                "url": f"{SHOPIFY_STORE}/products/{p.get('handle', '')}",
            }

        return catalog if catalog else FALLBACK_CATALOG
    except Exception:
        return FALLBACK_CATALOG


def get_local_garment_path(image_source):
    if not str(image_source).startswith("http"):
        return image_source
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tmp.close()
    urllib.request.urlretrieve(image_source, tmp.name)
    return tmp.name


def virtual_tryon(user_photo_path, selected_tee_name):
    if not user_photo_path:
        raise gr.Error("Please upload a clear photo of yourself first.")

    catalog = fetch_shopify_tees()
    item = catalog.get(selected_tee_name) or next(iter(catalog.values()))
    garment_path = get_local_garment_path(item["image"])

    try:
        client = Client("yisol/IDM-VTON", token=HF_TOKEN if HF_TOKEN else None)
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
        buy_html = (
            f'<div style="text-align:center;margin-top:14px;">'
            f'<a href="{item["url"]}" target="_blank" '
            f'style="display:inline-block;padding:12px 26px;background:#111;color:#fff;'
            f'font-weight:700;border-radius:8px;text-decoration:none;">'
            f'Buy This Tee Now — Free COD &rarr;</a></div>'
        )
        return output_img, buy_html
    except Exception as e:
        raise gr.Error(f"AI Fitting Room busy—please try again in a few seconds. ({e})")


def load_catalog_ui():
    catalog = fetch_shopify_tees()
    choices = list(catalog.keys())
    first_choice = choices[0]
    return (
        gr.update(choices=choices, value=first_choice),
        catalog[first_choice]["image"],
        f'<div style="text-align:center;margin-top:8px;"><a href="{catalog[first_choice]["url"]}" target="_blank" style="font-weight:700;">View Product on Keralon &rarr;</a></div>',
    )


def on_select_tee(selected_tee_name):
    catalog = fetch_shopify_tees()
    item = catalog.get(selected_tee_name) or next(iter(catalog.values()))
    link_html = (
        f'<div style="text-align:center;margin-top:8px;">'
        f'<a href="{item["url"]}" target="_blank" style="font-weight:700;">'
        f'View Product on Keralon &rarr;</a></div>'
    )
    return item["image"], link_html


INITIAL_CATALOG = fetch_shopify_tees()
INITIAL_KEYS = list(INITIAL_CATALOG.keys())
FIRST_KEY = INITIAL_KEYS[0]

with gr.Blocks(title="Keralon AI Virtual Fitting Room", theme=gr.themes.Soft()) as demo:
    gr.Markdown("## KERALON // AI VIRTUAL FITTING ROOM\nUpload your photo and preview any Keralon oversized tee on yourself before ordering.")

    with gr.Row():
        with gr.Column():
            tee_dropdown = gr.Dropdown(
                choices=INITIAL_KEYS,
                value=FIRST_KEY,
                label="1. Select Keralon Oversized Tee",
            )
            garment_preview = gr.Image(
                value=INITIAL_CATALOG[FIRST_KEY]["image"],
                label="Selected Tee Preview",
                interactive=False,
                height=300,
            )
            product_link = gr.HTML(
                f'<div style="text-align:center;margin-top:8px;"><a href="{INITIAL_CATALOG[FIRST_KEY]["url"]}" target="_blank" style="font-weight:700;">View Product on Keralon &rarr;</a></div>'
            )

        with gr.Column():
            user_photo = gr.Image(
                type="filepath",
                label="2. Upload Your Photo (Clear Front-Facing Upper Body)",
                height=340,
            )
            tryon_btn = gr.Button("TRY IT ON VIRTUALLY ⚡", variant="primary")

        with gr.Column():
            result_image = gr.Image(label="3. Your AI Fitting Room Result", height=340)
            buy_button = gr.HTML()

    tee_dropdown.change(
        fn=on_select_tee,
        inputs=[tee_dropdown],
        outputs=[garment_preview, product_link],
    )
    tryon_btn.click(
        fn=virtual_tryon,
        inputs=[user_photo, tee_dropdown],
        outputs=[result_image, buy_button],
    )
    demo.load(
        fn=load_catalog_ui,
        inputs=[],
        outputs=[tee_dropdown, garment_preview, product_link],
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    demo.launch(server_name="0.0.0.0", server_port=port)
