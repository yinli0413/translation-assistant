#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
腾讯云语音识别（一句话识别）
配置：环境变量 TENCENT_SECRET_ID / TENCENT_SECRET_KEY
"""

import os
import base64
import json
import hashlib
import hmac
import time
import requests

# 腾讯云 ASR 一句话识别接口
ASR_URL = "https://asr.tencentcloudapi.com/"
ASR_REGION = "ap-guangzhou"
ASR_VERSION = "2019-06-14"
ASR_ACTION = "SentenceRecognition"

# 语言 → 腾讯云引擎模型类型
# 16k_zh: 中文普通话；16k_en: 英文
# 注：一句话识别不支持 16k_zh_en 混合（混合只属于实时语音识别 WebSocket 流式接口）
LANG_ENGINE = {
    "zh-CN": "16k_zh",
    "zh": "16k_zh",
    "en-US": "16k_en",
    "en": "16k_en",
    "mix": "16k_en",  # 自动通话模式先按英文识别，前端根据结果是否含中文再决定翻译方向
}


def _sign(key, msg):
    """HMAC-SHA256 签名（key/msg 都统一转 bytes）"""
    if isinstance(key, str):
        key = key.encode("utf-8")
    if isinstance(msg, str):
        msg = msg.encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).digest()


def _get_headers(secret_id, secret_key, payload, service="asr"):
    """构造腾讯云 API v3 签名请求头"""
    algorithm = "TC3-HMAC-SHA256"
    timestamp = int(time.time())
    date = time.strftime("%Y-%m-%d", time.localtime(timestamp))

    # 1. 拼接规范请求串
    canonical_request = "POST\n/\n\n" + \
        "content-type:application/json; charset=utf-8\n" + \
        "host:asr.tencentcloudapi.com\n\n" + \
        "content-type;host\n" + hashlib.sha256(payload.encode("utf-8")).hexdigest()

    # 2. 拼接待签名字符串
    credential_scope = f"{date}/{service}/tc3_request"
    hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    string_to_sign = f"{algorithm}\n{timestamp}\n{credential_scope}\n{hashed_canonical_request}"

    # 3. 计算签名
    secret_date = _sign("TC3" + secret_key, date)
    secret_service = _sign(secret_date, service)
    secret_signing = _sign(secret_service, "tc3_request")
    signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    # 4. 拼接 Authorization
    authorization = (
        f"{algorithm} Credential={secret_id}/{credential_scope}, "
        f"SignedHeaders=content-type;host, Signature={signature}"
    )

    return {
        "Authorization": authorization,
        "Content-Type": "application/json; charset=utf-8",
        "Host": "asr.tencentcloudapi.com",
        "X-TC-Action": ASR_ACTION,
        "X-TC-Timestamp": str(timestamp),
        "X-TC-Version": ASR_VERSION,
        "X-TC-Region": ASR_REGION,
    }


def speech_to_text(audio_b64, lang="zh-CN"):
    """
    一句话识别：把 base64 音频转成文字
    audio_b64: base64 编码的音频（wav/pcm，16k 采样率，单声道）
    lang: zh-CN / en-US
    返回：(成功标志, 文字或错误信息)
    """
    secret_id = os.environ.get("TENCENT_SECRET_ID", "")
    secret_key = os.environ.get("TENCENT_SECRET_KEY", "")
    if not secret_id or not secret_key:
        return False, "未配置腾讯云密钥（TENCENT_SECRET_ID/TENCENT_SECRET_KEY）"

    engine = LANG_ENGINE.get(lang, "16k_zh")

    # 解码 base64 计算数据长度
    try:
        audio_bytes = base64.b64decode(audio_b64)
    except Exception:
        return False, "音频数据解码失败"

    payload = {
        "ProjectId": 0,
        "SubServiceType": 2,  # 一句话识别
        "EngSerViceType": engine,
        "SourceType": 1,  # 1 = 音频数据
        "VoiceFormat": "wav",
        "Data": audio_b64,
        "DataLen": len(audio_bytes),
    }

    try:
        headers = _get_headers(secret_id, secret_key, json.dumps(payload))
        resp = requests.post(ASR_URL, headers=headers, data=json.dumps(payload), timeout=15)
        data = resp.json()

        if "Response" not in data:
            return False, "识别失败: " + json.dumps(data, ensure_ascii=False)[:200]

        result = data["Response"]
        if "Error" in result:
            return False, "识别错误: " + result["Error"].get("Message", "未知错误")

        text = result.get("Result", "")
        return (True, text) if text else (False, "未识别到语音内容")

    except Exception as e:
        return False, "识别请求出错: " + str(e)
