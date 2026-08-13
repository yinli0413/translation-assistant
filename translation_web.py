#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
外贸翻译助手 · Web 版
启动方式：python translation_web.py  → 浏览器打开 http://localhost:5000
依赖：flask, requests, deep-translator
"""

import os
import sys

# 确保能 import 同目录的 translation_bot
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify, render_template, send_from_directory
from translation_bot import smart_translate, polish_text, chat_reply, PHRASES
import asr

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True  # 修改模板后无需重启

PORT = 5001  # 如端口被占用可改为其他

# PWA 静态资源目录
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/manifest.json")
def manifest():
    return send_from_directory(STATIC_DIR, "manifest.json", mimetype="application/manifest+json")


@app.route("/sw.js")
def service_worker():
    return send_from_directory(STATIC_DIR, "sw.js", mimetype="application/javascript")


@app.route("/icon.svg")
def icon():
    return send_from_directory(STATIC_DIR, "icon.svg", mimetype="image/svg+xml")


@app.route("/api/translate", methods=["POST"])
def api_translate():
    data = request.get_json()
    text = (data.get("text") or "").strip()
    target = data.get("target", "en")
    if not text:
        return jsonify({"error": "请输入要翻译的文字"}), 400
    try:
        result = smart_translate(text, target=target)
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/polish", methods=["POST"])
def api_polish():
    data = request.get_json()
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "请输入要润色的文字"}), 400
    try:
        result = polish_text(text)
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/reply", methods=["POST"])
def api_reply():
    data = request.get_json()
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "请输入客户发来的消息"}), 400
    try:
        result = chat_reply(text)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/phrases")
def api_phrases():
    result = []
    for group in PHRASES.values():
        items = [{"id": num, "cn": cn, "en": en} for num, cn, en in group["items"]]
        result.append({"category": group["category"], "items": items})
    return jsonify(result)


@app.route("/api/speech-to-text", methods=["POST"])
def api_speech_to_text():
    data = request.get_json()
    audio = data.get("audio") or ""
    lang = data.get("lang", "zh-CN")
    if not audio:
        return jsonify({"error": "缺少音频数据"}), 400
    ok, text = asr.speech_to_text(audio, lang=lang)
    if ok:
        return jsonify({"text": text})
    return jsonify({"error": text}), 500


if __name__ == "__main__":
    print("\n  翻译助手已启动！")
    print(f"  打开浏览器访问: http://localhost:{PORT}\n")
    app.run(host="0.0.0.0", port=PORT, debug=False)
