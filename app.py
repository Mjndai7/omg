import gradio as gr
import requests

def get_m3u8():
    url = "https://raw.githubusercontent.com/mjndai7/omg/main/247world.m3u8"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad status codes
        return response.text
    except requests.RequestException as e:
        return f"Error fetching M3U8 file: {str(e)}"

iface = gr.Interface(
    fn=get_m3u8,
    inputs=None,
    outputs="text",
    title="247World M3U8 Viewer",
    description="Displays the latest 247world.m3u8 file from GitHub."
)
iface.launch(server_name="0.0.0.0", server_port=7860)
