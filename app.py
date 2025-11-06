# filename: app_direct_key.py

from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import json, re, time, os

# ========================================
# ⚙️ Cấu hình API - NẠP KHÓA TRỰC TIẾP
# ========================================
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("❌ 缺少 OPENAI_API_KEY 环境变量，请在 Render 上设置 Environment Variables。")

# ✅ 使用 OpenRouter 代理（可换成官方 endpoint）
client = OpenAI(api_key=OPENAI_API_KEY, base_url="https://openrouter.ai/api/v1")
MODEL = "gpt-4o-mini"

app = Flask(__name__)
CORS(app)

# ========================================
# 🔧 HÀM CÔNG CỤ
# ========================================
def call_chat(prompt, max_tokens=300, temperature=0.6, system_prompt=None):
    """Gọi mô hình OpenAI"""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return resp.choices[0].message.content.strip()





def generate_article(main_kw, url, index):
    """
    Sinh 3 từ khóa phụ liên quan và nội dung quảng bá trong 1 prompt duy nhất.
    Trả về dict: {related_keywords: [...], content: ...}
    """
    system_prompt = "你是一位精通SEO的中文文案策划，请根据提供的关键词和URL生成一段自然的推广内容。"
    prompt = (
        f"请为主关键词「{main_kw}」生成3个高度相关的中文长尾关键词（JSON数组），"
        f"并用这3个长尾关键词写一段推广文案，长度100-150字，开头必须是：{main_kw}【网址：{url}】。\n"
        "要求：\n"
        "1. 每个长尾关键词必须包含主关键词；\n"
        "2. 不与主关键词完全重复；\n"
        "3. 推广文案要自然流畅、有吸引力，不能过度重复关键词；\n"
        "4. 如果出现年份，只能使用“2026年”，不能出现2025年或更早的年份；\n"
        "5. 只返回JSON对象，如：{related_keywords: [...], content: \"...\"}"
    )
    text = call_chat(prompt, max_tokens=700, temperature=0.9, system_prompt=system_prompt)
    try:
        obj = json.loads(text)
        related_kws = obj.get("related_keywords", [])
        content = obj.get("content", "")
        return related_kws, content
    except Exception:
        # fallback: try to extract manually
        match = re.search(r'\[(.*?)\]', text)
        related_kws = []
        if match:
            related_kws = [kw.strip('"') for kw in match.group(1).split(',') if kw.strip()]
        content = text
        return related_kws[:3], content


# ========================================
# 🔥 API ROUTE
# ========================================
@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()

    if not data or "main_keyword" not in data or "num_articles" not in data:
        return jsonify({"error": "Thiếu tham số bắt buộc: main_keyword hoặc num_articles."}), 400

    base_kw = data["main_keyword"].strip()
    url = data.get("url", "http://191.run").strip()

    try:
        num_articles = int(data["num_articles"])
    except ValueError:
        return jsonify({"error": "num_articles phải là số nguyên."}), 400

    if not base_kw:
        return jsonify({"error": "Từ khóa chính không được để trống."}), 400

    if num_articles <= 0 or num_articles > 50:
        return jsonify({"error": "num_articles phải nằm trong khoảng 1–50."}), 400

    results = []

    # Dùng 1 prompt duy nhất cho mỗi bài viết
    for i in range(num_articles):
        try:
            main_kw = base_kw
            related_kws, content = generate_article(main_kw, url, i)
            results.append({
                "base_keyword": base_kw,
                "main_kw_quality": main_kw,
                "related_keywords": related_kws,
                "content": content
            })
            time.sleep(0.5)
        except Exception as e:
            results.append({
                "main_kw_quality": base_kw,
                "error": f"Lỗi khi tạo bài {i+1}: {str(e)}"
            })
            time.sleep(0.5)
    return jsonify(results)


@app.route("/")
def home():
    return "✅ API nâng cấp: 1 từ khóa gốc → sinh nhiều từ khóa chính chất lượng + bài viết tương ứng."


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)


