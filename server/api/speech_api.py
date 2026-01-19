#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
语音API - 统一的语音转文字和文字转语音接口

设计原则：
1. 只有两个核心接口：STT和TTS
2. 流式输出通过参数控制
3. 直接调用智谱AI API
4. 清晰的参数和文档
"""

import os
import tempfile
import logging
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel

from server.config import Config
from server.utils.zhipu_client import ZhipuAIClient

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================
# 音频格式转换
# ============================================

async def convert_audio_for_zhipu(audio_file_path: str, original_filename: str = None) -> str:
    """
    将音频转换为智谱AI支持的格式
    
    Args:
        audio_file_path: 原始音频文件路径
        original_filename: 原始文件名（用于判断格式）
    
    Returns:
        转换后的音频文件路径
    """
    import asyncio
    from pathlib import Path
    
    # 获取文件扩展名
    if original_filename:
        ext = Path(original_filename).suffix.lower()
    else:
        ext = Path(audio_file_path).suffix.lower()
    
    # 智谱AI支持的格式：mp3, wav, m4a, flac
    supported_formats = {'.mp3', '.wav', '.m4a', '.flac'}
    
    if ext in supported_formats:
        logger.info(f"Audio format {ext} is supported, no conversion needed")
        return audio_file_path
    
    # 需要转换的格式
    logger.info(f"Converting audio from {ext} to wav for Zhipu AI")
    
    try:
        from pydub import AudioSegment
        
        # 读取音频文件
        if ext == '.webm':
            # WebM可能包含音频或视频，尝试作为音频读取
            audio = AudioSegment.from_file(audio_file_path, format='webm')
        else:
            audio = AudioSegment.from_file(audio_file_path)
        
        # 转换为WAV格式（智谱AI推荐）
        # 设置为16kHz单声道，智谱AI的标准格式
        audio = audio.set_frame_rate(16000).set_channels(1)
        
        # 创建输出文件
        output_path = audio_file_path.replace(ext, '.wav')
        
        # 导出为WAV
        audio.export(output_path, format='wav')
        
        logger.info(f"Audio converted successfully: {output_path}")
        return output_path
        
    except ImportError:
        logger.error("pydub not installed, cannot convert audio format")
        raise HTTPException(500, "音频转换功能不可用，请联系管理员安装pydub")
    
    except Exception as e:
        logger.error(f"Audio conversion failed: {e}")
        # 如果转换失败，尝试使用原文件
        logger.warning("Audio conversion failed, trying original file")
        return audio_file_path


# ============================================
# 请求/响应模型
# ============================================

class STTRequest(BaseModel):
    """语音转文字请求（用于文本参数）"""
    prompt: Optional[str] = None  # 上下文提示


class STTResponse(BaseModel):
    """语音转文字响应"""
    text: str
    duration: Optional[float] = None


class TTSRequest(BaseModel):
    """文字转语音请求"""
    text: str
    voice: str = "tongtong"          # 音色
    speed: float = 1.0               # 语速 0.5-2.0
    volume: float = 1.0              # 音量 0-10
    response_format: str = "wav"     # 输出格式 wav/pcm
    stream: bool = False             # 是否流式输出


# ============================================
# 语音转文字 (STT)
# ============================================

@router.post("/stt", response_model=STTResponse, summary="语音转文字")
async def speech_to_text(
    file: UploadFile = File(..., description="音频文件 (.wav/.mp3, ≤25MB, ≤30秒)"),
    prompt: Optional[str] = None,
    api_key: Optional[str] = Form(None, description="API Key（可选，留空使用服务端配置）")
):
    """
    语音转文字 (Speech-to-Text)
    
    **智谱AI模型**: `glm-asr-2512`
    
    **支持格式**: wav, mp3  
    **文件限制**: ≤ 25MB  
    **时长限制**: ≤ 30秒  
    
    **参数说明**:
    - `file`: 音频文件（必填）
    - `prompt`: 上下文提示，可提升识别准确度（可选，建议<8000字）
    
    **返回**:
    - `text`: 识别的文本内容
    - `duration`: 处理耗时（秒）
    
    **调用智谱AI API**: `https://open.bigmodel.cn/api/paas/v4/audio/transcriptions`
    """
    import time
    start_time = time.time()
    
    # 获取配置和API Key
    config = Config()
    
    # API Key优先级：请求参数 > 语音识别专用Key > 模型API Key
    final_api_key = api_key or config.ZHIPU_SPEECH_API_KEY or config.ZHIPU_API_KEY
    
    if not final_api_key:
        raise HTTPException(500, "未配置 ZHIPU_API_KEY，请在 .env 文件中设置或在请求中提供 api_key 参数")
    
    # 保存上传的文件
    temp_file = None
    try:
        # 检查文件大小
        contents = await file.read()
        file_size_mb = len(contents) / (1024 * 1024)
        
        if file_size_mb > 25:
            raise HTTPException(400, f"文件过大：{file_size_mb:.1f}MB，最大支持25MB")
        
        # 保存为临时文件
        suffix = os.path.splitext(file.filename)[1] if file.filename else ".webm"
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_file.write(contents)
        temp_file.close()
        
        logger.info(f"STT: Processing audio file {file.filename} ({file_size_mb:.2f}MB)")
        
        # 音频格式转换（如果需要）
        converted_file = None
        try:
            converted_file = await convert_audio_for_zhipu(temp_file.name, file.filename)
            
            # 调用智谱AI
            client = ZhipuAIClient(api_key=final_api_key)
            result = await client.audio_transcriptions(
                audio_file=converted_file,
                model="glm-asr-2512",
                prompt=prompt
            )
        finally:
            # 清理转换后的文件
            if converted_file and converted_file != temp_file.name and os.path.exists(converted_file):
                try:
                    os.unlink(converted_file)
                except:
                    pass
        
        # 获取文本
        text = result.get("text", "")
        if not text:
            raise HTTPException(500, "语音识别失败：未返回文本")
        
        duration = time.time() - start_time
        logger.info(f"STT: Success in {duration:.2f}s, text length: {len(text)}")
        
        return STTResponse(text=text, duration=duration)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"STT Error: {e}", exc_info=True)
        raise HTTPException(500, f"语音识别失败: {str(e)}")
    finally:
        # 清理临时文件
        if temp_file and os.path.exists(temp_file.name):
            try:
                os.unlink(temp_file.name)
            except:
                pass


# ============================================
# 文字转语音 (TTS)
# ============================================

@router.post("/tts", summary="文字转语音")
async def text_to_speech(request: TTSRequest):
    """
    文字转语音 (Text-to-Speech)
    
    **智谱AI模型**: `glm-tts`
    
    **文本限制**: ≤ 1024 字符  
    **输出格式**: wav (非流式) / pcm (流式)  
    
    **参数说明**:
    - `text`: 要转换的文本（必填，≤1024字符）
    - `voice`: 音色，可选：tongtong(默认), chuichui, xiaochen
    - `speed`: 语速，范围 0.5-2.0（默认1.0）
    - `volume`: 音量，范围 0-10（默认1.0）
    - `response_format`: 输出格式，wav/pcm（默认wav）
    - `stream`: 是否流式输出（默认false）
    
    **返回**:
    - 非流式：完整音频文件（Content-Type: audio/wav 或 audio/pcm）
    - 流式：音频流（Content-Type: audio/pcm, Transfer-Encoding: chunked）
    
    **调用智谱AI API**: `https://open.bigmodel.cn/api/paas/v4/audio/speech`
    """
    # 参数验证
    if len(request.text) > 1024:
        raise HTTPException(400, f"文本过长：{len(request.text)}字符，最大支持1024字符")
    
    if not (0.5 <= request.speed <= 2.0):
        raise HTTPException(400, f"语速无效：{request.speed}，范围应为 0.5-2.0")
    
    if not (0 <= request.volume <= 10):
        raise HTTPException(400, f"音量无效：{request.volume}，范围应为 0-10")
    
    # 获取配置
    config = Config()
    if not config.ZHIPU_API_KEY:
        raise HTTPException(500, "未配置 ZHIPU_API_KEY，请在 .env 文件中设置")
    
    try:
        client = ZhipuAIClient(api_key=config.ZHIPU_API_KEY)
        
        # 流式输出
        if request.stream:
            logger.info(f"TTS Stream: text_length={len(request.text)}, voice={request.voice}")
            
            async def audio_stream():
                """流式音频生成器"""
                async for chunk in await client.audio_speech_stream(
                    text=request.text,
                    voice=request.voice,
                    speed=request.speed,
                    volume=request.volume
                ):
                    yield chunk
            
            return StreamingResponse(
                audio_stream(),
                media_type="audio/pcm",
                headers={
                    "Content-Disposition": f"attachment; filename=speech.pcm",
                    "Transfer-Encoding": "chunked"
                }
            )
        
        # 非流式输出
        else:
            logger.info(f"TTS: text_length={len(request.text)}, voice={request.voice}, format={request.response_format}")
            
            audio_data = await client.audio_speech(
                text=request.text,
                voice=request.voice,
                speed=request.speed,
                volume=request.volume,
                response_format=request.response_format
            )
            
            media_type = f"audio/{request.response_format}"
            filename = f"speech.{request.response_format}"
            
            return Response(
                content=audio_data,
                media_type=media_type,
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
            
    except Exception as e:
        logger.error(f"TTS Error: {e}", exc_info=True)
        raise HTTPException(500, f"文字转语音失败: {str(e)}")


# ============================================
# 健康检查
# ============================================

@router.get("/health")
async def speech_health():
    """语音服务健康检查"""
    config = Config()
    
    return {
        "status": "healthy",
        "zhipu_api_configured": bool(config.ZHIPU_API_KEY),
        "endpoints": {
            "stt": "/api/v1/speech/stt",
            "tts": "/api/v1/speech/tts"
        }
    }

