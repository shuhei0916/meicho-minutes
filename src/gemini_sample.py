import google.generativeai as genai

genai.configure(api_key="AIzaSyCDiEdfsVIMAnBXraxo8C3EdRaXpVGG4Do")
model = genai.GenerativeModel("gemini-2.5-flash")

response = model.generate_content(
    "https://www.amazon.co.jp/dp/4167193205/?coliid=INDCGOENPV1NP&colid=YAEUCTRPQIXU&psc=0&ref_=list_c_wl_lv_ov_lig_dp_it_im  あなたはYouTubeショート動画の台本作成の専門家です。この書籍情報を基に、30～60秒程度のショート動画用台本を作成してください。"
)
print(response.text)
