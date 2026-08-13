#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
外贸翻译机器人
功能：
  1. 实时翻译：你说中文/英文/其他语言，自动翻译成目标语言
  2. 外贸润色：把中式英语改成地道商务英语
  3. 快捷短语：外贸常用表达一键调用
  4. 接入 DeepSeek/OpenAI API（可选，翻译质量更高）

使用方法：
  python translation_bot.py
"""

import os
import sys
import json
import requests
from deep_translator import GoogleTranslator

# ==================== 配置区 ====================

# 默认目标语言：zh=中文，en=英文，es=西班牙语，fr=法语，de=德语，ja=日语
DEFAULT_TARGET = "en"

# 可选：接入 DeepSeek / OpenAI API，获得更好的外贸润色效果
# 推荐用环境变量设置（避免密钥硬编码泄露）：
#   Windows (CMD):   set DEEPSEEK_API_KEY=sk-xxxxxx
#   Windows (PowerShell): $env:DEEPSEEK_API_KEY="sk-xxxxxx"
#   macOS / Linux:   export DEEPSEEK_API_KEY=sk-xxxxxx
# 若环境变量未设置，也可直接填到下面的引号里，例如："sk-xxxxxxxx"
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# DeepSeek 默认使用这个地址，OpenAI 用户可改成 https://api.openai.com/v1/chat/completions
LLM_API_URL = "https://api.deepseek.com/v1/chat/completions"
LLM_MODEL = "deepseek-chat"  # OpenAI 可改成 gpt-4o-mini / gpt-4

# ==================== 语言支持 ====================

LANG_MAP = {
    "zh": "中文",
    "en": "英文",
    "es": "西班牙语",
    "fr": "法语",
    "de": "德语",
    "ja": "日语",
    "ko": "韩语",
    "ru": "俄语",
    "pt": "葡萄牙语",
    "it": "意大利语",
    "ar": "阿拉伯语",
    "th": "泰语",
    "vi": "越南语",
}

# ==================== 快捷短语库（回复客户专用） ====================

PHRASES = {
    "1": {
        "category": "📩 询盘回复",
        "items": [
            ("1", "感谢询盘", "Thank you for your interest in our products. We will send you our best offer shortly."),
            ("2", "询盘回复-问数量", "Thanks for your inquiry. May I know your estimated order quantity so that we can quote accordingly?"),
            ("3", "询盘回复-问规格", "Thank you for reaching out. Could you please share more details about the specifications you need?"),
        ],
    },
    "2": {
        "category": "💰 报价与议价回复",
        "items": [
            ("4", "报价已发", "Please find our quotation attached. Should you have any questions, feel free to let us know."),
            ("5", "价格有效期", "This quotation is valid for 30 days. We look forward to your confirmation."),
            ("6", "价格已最低", "We have already offered you our most competitive price. The profit margin is very thin."),
            ("7", "量大可优惠", "For bulk orders, we would be happy to offer a special discount. Please let us know your target quantity."),
            ("8", "同意降价", "In order to support your first cooperation, we can offer a 3% discount on the quoted price."),
            ("9", "部分让步", "We are unable to reduce the price further, but we can offer free shipping for orders over $5,000."),
        ],
    },
    "3": {
        "category": "📦 订单与生产回复",
        "items": [
            ("10", "订单已收到", "Thank you for your order. We have received your PO and will arrange production immediately."),
            ("11", "PI已发送", "We have sent you the Proforma Invoice. Please check and confirm."),
            ("12", "收到定金", "We have received your deposit. Thank you. Production will start soon."),
            ("13", "正在生产", "Your order is now in production and is expected to be completed by the date stated in the PI."),
            ("14", "生产完成", "Your goods have been finished and passed quality inspection. We will arrange shipment soon."),
        ],
    },
    "5": {
        "category": "🚢 发货与物流回复",
        "items": [
            ("15", "已发货附单号", "Your order has been shipped. The tracking number is [XXX]. You can track it online."),
            ("16", "提供提单副本", "Please find the B/L copy attached. Kindly arrange the balance payment at your earliest convenience."),
            ("17", "通知已到港", "The goods have arrived at the destination port. Please arrange customs clearance in time."),
            ("18", "物流延迟说明", "Due to the shipping company's schedule adjustment, the shipment will be delayed by 2-3 days. We apologize for any inconvenience."),
        ],
    },
    "6": {
        "category": "✅ 样品回复",
        "items": [
            ("19", "样品已寄出", "The samples have been sent out today. The tracking number is [XXX]. Please keep an eye on them."),
            ("20", "样品收费说明", "The sample fee is $50, which will be refunded after you place a formal order."),
            ("21", "收到样品反馈", "Thank you for your feedback on the samples. Please let us know if any adjustments are needed."),
        ],
    },
    "7": {
        "category": "🔧 质量与售后回复",
        "items": [
            ("22", "收到质量投诉", "Thank you for your feedback. We take this matter seriously and will investigate it immediately."),
            ("23", "同意退换货", "We apologize for the quality issue. We agree to replace the defective goods or refund you accordingly."),
            ("24", "请求照片证据", "Could you please send us some photos or videos of the defective products? This will help us find the root cause."),
            ("25", "质量问题解释", "The issue might have occurred during transportation. We will work with the shipping company to resolve it."),
        ],
    },
    "8": {
        "category": "💳 付款催款回复",
        "items": [
            ("26", "请安排定金", "Could you please arrange the 30% deposit so that we can start production?"),
            ("27", "请付尾款", "The goods are ready for shipment. Please arrange the balance payment at your earliest convenience."),
            ("28", "收到尾款", "We have received your balance payment. The goods will be shipped out within 2 working days."),
        ],
    },
    "9": {
        "category": "🤝 跟进与关系维护",
        "items": [
            ("29", "跟进报价", "I am writing to follow up on our quotation sent on [date]. Have you had a chance to review it?"),
            ("30", "节日祝福", "Wishing you and your family a joyful holiday season and a prosperous New Year!"),
            ("31", "感谢支持", "Thank you for your continued trust and support. We are always here to assist you."),
            ("32", "邀请返单", "Your last order was well received. If you need to restock, please let us know and we will prioritize your order."),
            ("33", "询问新需求", "We hope everything is going well. Do you have any new purchasing plans for the coming quarter?"),
        ],
    },
    "10": {
        "category": "🎒 书包产品介绍",
        "items": [
            ("34", "颜色丰富", "Our school bags come in a wide range of vibrant colors such as pink, blue, purple and green, which kids really love."),
            ("35", "款式多样", "We offer many styles and designs to choose from, suitable for boys and girls of different ages."),
            ("36", "材质优质", "Our backpacks are made of high-quality Oxford fabric and durable polyester, which are lightweight yet long-lasting."),
            ("37", "护脊设计", "The backpack features an ergonomic padded back panel and adjustable shoulder straps to protect children's spines."),
            ("38", "大容量多隔层", "The bag has multiple compartments including a main compartment, front pocket and side bottle pockets, offering plenty of space for books and a lunch box."),
            ("39", "无毒环保", "All materials are non-toxic, eco-friendly and BPA-free, fully compliant with EN71 and REACH standards."),
            ("40", "支持定制", "We support OEM and ODM. Custom colors, designs and logo printing are all available."),
            ("41", "品牌特色", "Inspired by Smiggle's fun and creative style, our products feature bright colors and playful designs that stand out."),
            ("42", "质量保证", "Each bag goes through strict quality control and is backed by a reliable after-sales guarantee."),
        ],
    },
}

def flatten_phrases():
    """把分类短语扁平化，方便按编号查找"""
    flat = {}
    for group in PHRASES.values():
        for num, cn, en in group["items"]:
            flat[num] = (cn, en)
    return flat

# ==================== 核心功能 ====================

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def print_header():
    print("=" * 50)
    print("       🤖 外贸翻译机器人")
    print("=" * 50)


def print_menu(target):
    print(f"\n当前目标语言：{LANG_MAP.get(target, target)}")
    print("-" * 50)
    print("  [1] 普通翻译：输入任意文字，自动翻译")
    print("  [2] 外贸润色：把中文/中式英语改得更商务")
    print("  [3] 快捷短语：一键发送外贸常用句")
    print("  [4] 切换目标语言")
    print("  [5] 退出")
    print("-" * 50)


# 翻译器缓存：避免每次翻译都重新初始化（重新初始化要重新建连接获取 token，极慢）
_translator_cache = {}


def google_translate(text, target="en"):
    """使用 Google 翻译（带缓存，提升速度）"""
    # Google 翻译对中文的特殊代码
    google_target = "zh-CN" if target == "zh" else target
    try:
        translator = _translator_cache.get(google_target)
        if translator is None:
            translator = GoogleTranslator(source="auto", target=google_target)
            _translator_cache[google_target] = translator
        return translator.translate(text)
    except Exception as e:
        return f"[翻译出错] {e}"


def llm_translate_or_polish(text, target="en", mode="translate"):
    """
    使用 DeepSeek / OpenAI API 进行高质量翻译或润色
    mode: translate | polish
    """
    api_key = DEEPSEEK_API_KEY or OPENAI_API_KEY
    if not api_key:
        return None

    if mode == "polish":
        system_prompt = (
            "You are a professional foreign trade business writing assistant. "
            "Rewrite the user's text into natural, polite, and professional business English suitable for international trade emails/chat. "
            "Keep the original meaning. Only return the rewritten text, no explanations."
        )
    else:
        target_lang = LANG_MAP.get(target, target)
        system_prompt = (
            f"You are a professional translator for foreign trade. "
            f"Translate the user's text into {target_lang} naturally and accurately. "
            f"Only return the translation, no explanations."
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        "temperature": 0.3,
    }

    try:
        response = requests.post(LLM_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"[AI 翻译出错，已回退到 Google 翻译] {e}"


def smart_translate(text, target="en"):
    """优先用 LLM，否则用 Google"""
    result = llm_translate_or_polish(text, target=target, mode="translate")
    if result and not result.startswith("["):
        return result
    return google_translate(text, target=target)


def polish_text(text):
    """外贸润色：优先 LLM，否则用 Google 翻译兜底"""
    result = llm_translate_or_polish(text, mode="polish")
    if result and not result.startswith("["):
        return result
    # 兜底：先翻译成英文
    return google_translate(text, target="en")


# ==================== 对话交流模式 ====================

# 书包/箱包行业背景（注入 LLM 提示词，让回复带行业专业话术）
BAG_INDUSTRY_CONTEXT = """
你服务的用户是 Smiggle 品牌书包（school bags / backpacks）的外贸业务员。
回复时请结合以下书包行业专业背景，使用地道的外贸话术：

【产品与材质】
- 常见材质：牛津布(Oxford fabric)、涤纶(polyester)、尼龙(nylon)、EVA、PU皮(polyurethane leather)
- 结构：主袋(main compartment)、前袋(front pocket)、侧袋/水杯袋(side pocket)、护脊背板(padded back panel)、加厚肩带(padded shoulder straps)、胸扣(chest strap)、午餐盒层(lunch box compartment)
- 规格：容量(capacity, 单位L)、尺寸(dimensions)、重量(weight)、适用学龄段

【贸易术语】
- MOQ(起订量)、lead time(交货期)、sample/打样、FOB/CIF、QC/质检、carton(纸箱)、OEM/ODM

【儿童用品安全标准】
- EN71(欧盟玩具标准)、REACH(欧盟化学品法规)、CPSIA(美国消费品安全)、ASTM、无毒环保(non-toxic/eco-friendly/BPA-free)

【Smiggle 品牌特点】
- 澳洲儿童品牌，色彩鲜艳(vibrant colors)、趣味创意设计(fun & creative design)、创意文具与书包

回复话术要自然、专业、有礼貌，符合外贸邮件/聊天习惯。
"""

# 意图关键词 → 匹配的快捷短语编号（无 LLM 时的兜底）
INTENT_KEYWORDS = {
    "砍价议价": (["discount", "cheap", "cheaper", "expensive", "lower", "reduce", "better price", "best price", "优惠", "便宜", "折扣", "降价"], ["6", "8", "9"]),
    "报价咨询": (["price", "quote", "quotation", "how much", "价格", "报价"], ["5", "6"]),
    "询盘咨询": (["inquiry", "interest", "catalog", "catalogue", "product", "询盘", "产品", "目录"], ["1", "2"]),
    "发货物流": (["ship", "shipping", "tracking", "b/l", "logistics", "发货", "物流", "单号", "到港"], ["15", "16", "17"]),
    "订单生产": (["order", "purchase", "production", "lead time", "订单", "生产", "交期"], ["10", "12", "13"]),
    "样品需求": (["sample", "样品", "打样"], ["19", "20"]),
    "质量投诉": (["quality", "defect", "defective", "broken", "damaged", "质量", "瑕疵", "破损", "坏"], ["22", "23", "24"]),
    "付款催款": (["deposit", "payment", "balance", "pay", "tt", "定金", "付款", "尾款"], ["26", "27", "28"]),
    "跟进返单": (["follow", "restock", "reorder", "again", "跟进", "返单", "补货"], ["29", "32"]),
}


def _classify_intent(text):
    """根据关键词判断客户意图，返回 (意图名, 推荐短语编号列表)"""
    t = text.lower()
    for intent, (keywords, phrase_ids) in INTENT_KEYWORDS.items():
        if any(k in t for k in keywords):
            return intent, phrase_ids
    return "通用咨询", ["1"]


def chat_reply(text, user_intent=""):
    """
    对话交流模式：输入客户发来的话，返回结构化回复
    返回 dict：{intent, meaning, reply, alt_reply}
    - intent: 客户意图（中文）
    - meaning: 客户这句话的中文意思
    - reply: 专业英文回复（可直接发给客户）
    - alt_reply: 备选英文回复
    - user_intent: 用户想表达的主观意思（中文），AI 会把它融入专业话术
    """
    text = text.strip()
    if not text:
        return {"intent": "", "meaning": "", "reply": "", "alt_reply": ""}

    api_key = DEEPSEEK_API_KEY or OPENAI_API_KEY
    if api_key:
        try:
            return _llm_chat_reply(text, api_key, user_intent)
        except Exception:
            pass  # LLM 失败则走兜底

    return _fallback_chat_reply(text, user_intent)


def _llm_chat_reply(text, api_key, user_intent=""):
    """用 LLM 生成对话回复，返回 dict"""
    system_prompt = (
        "你是一名资深外贸业务员，精通国际贸易谈判，熟悉书包/箱包行业。"
        + BAG_INDUSTRY_CONTEXT +
        "客户发来一句话，你需要："
        "1) 判断客户意图；2) 用中文简要说明客户的意思；"
        "3) 给出1条专业、礼貌、地道的英文回复；4) 再给出1条备选英文回复。"
    )
    if user_intent:
        system_prompt += (
            f"另外，用户想表达的主观意思是：「{user_intent}」。"
            "请把用户的这个意思，用专业的外贸话术融入到你给出的英文回复中（主回复 reply 要体现用户的意思）。"
        )
    system_prompt += (
        "严格输出 JSON，格式："
        '{"intent":"客户意图(中文)","meaning":"客户意思(中文)",'
        '"reply":"专业英文回复","alt_reply":"备选英文回复"}'
        "不要输出 JSON 以外的任何内容。"
    )
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        "temperature": 0.5,
    }
    resp = requests.post(LLM_API_URL, headers=headers, json=payload, timeout=40)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"].strip()
    # 清理可能的 markdown 代码块包裹
    content = content.replace("```json", "").replace("```", "").strip()
    data = json.loads(content)
    return {
        "intent": data.get("intent", ""),
        "meaning": data.get("meaning", ""),
        "reply": data.get("reply", ""),
        "alt_reply": data.get("alt_reply", ""),
    }


def _fallback_chat_reply(text, user_intent=""):
    """无 LLM 时：意图分类 + 快捷短语兜底 + 翻译客户原话"""
    intent, phrase_ids = _classify_intent(text)
    flat = flatten_phrases()

    # 取第一条匹配短语作为主回复，第二条作为备选
    cn_main, en_main = flat.get(phrase_ids[0], ("", ""))
    cn_alt, en_alt = flat.get(phrase_ids[1], ("", "")) if len(phrase_ids) > 1 else ("", "")

    # 如果用户给了主观意思，把它翻译成英文并附加到主回复
    if user_intent:
        intent_en = google_translate(user_intent, target="en")
        if intent_en and not intent_en.startswith("["):
            en_main = (en_main + " " + intent_en).strip()

    # 客户原话的中文意思（用 Google 翻译）
    meaning = google_translate(text, target="zh")

    return {
        "intent": intent,
        "meaning": meaning,
        "reply": en_main,
        "alt_reply": en_alt or "",
    }


def list_phrases():
    print("\n📋 外贸快捷短语（回复客户专用）：")
    for group in PHRASES.values():
        print(f"\n{group['category']}")
        for num, cn, en in group["items"]:
            print(f"  [{num}] {cn}")
            print(f"       {en}")


def choose_language():
    print("\n支持的目标语言：")
    codes = list(LANG_MAP.keys())
    for i, code in enumerate(codes, 1):
        print(f"  [{i}] {LANG_MAP[code]} ({code})")

    choice = input("\n请输入编号或语言代码（如 en/zh）：").strip()
    if choice in LANG_MAP:
        return choice
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(codes):
            return codes[idx]
    except ValueError:
        pass
    print("选择无效，保持当前设置。")
    return None


def translate_loop(target):
    print(f"\n💬 普通翻译模式（目标语言：{LANG_MAP.get(target, target)}）")
    print("提示：输入空行返回主菜单\n")
    while True:
        text = input("你：").strip()
        if not text:
            break
        result = smart_translate(text, target=target)
        print(f"译：{result}\n")


def polish_loop():
    print("\n✨ 外贸润色模式：把中文/中式英语改成地道商务英语")
    print("提示：输入空行返回主菜单\n")
    while True:
        text = input("你：").strip()
        if not text:
            break
        result = polish_text(text)
        print(f"润色：{result}\n")


def phrase_loop():
    flat = flatten_phrases()
    list_phrases()
    print("\n提示：输入编号发送短语，输入空行返回主菜单\n")
    while True:
        choice = input("选择短语编号：").strip()
        if not choice:
            break
        if choice in flat:
            cn, en = flat[choice]
            print(f"中文：{cn}")
            print(f"英文：{en}\n")
            # 自动复制到剪贴板（Windows）
            try:
                os.system(f'echo {en} | clip')
                print("✅ 已复制英文到剪贴板\n")
            except Exception:
                pass
        else:
            print("无效的编号，请重新输入。\n")


def main():
    target = DEFAULT_TARGET

    while True:
        clear_screen()
        print_header()
        print_menu(target)

        choice = input("请选择功能（1-5）：").strip()

        if choice == "1":
            translate_loop(target)
        elif choice == "2":
            polish_loop()
        elif choice == "3":
            phrase_loop()
        elif choice == "4":
            new_target = choose_language()
            if new_target:
                target = new_target
                print(f"已切换到：{LANG_MAP[target]}")
        elif choice == "5":
            print("\n再见，祝外贸顺利！🌍")
            sys.exit(0)
        else:
            print("无效输入，请重新选择。")
            input("按回车继续...")


if __name__ == "__main__":
    main()
