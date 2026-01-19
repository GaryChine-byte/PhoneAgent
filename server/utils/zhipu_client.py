#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
智谱AI HTTP客户端
统一封装所有智谱AI API调用，使用HTTP方式而非SDK

官方文档: https://docs.bigmodel.cn/cn/api/introduction
API端点: https://open.bigmodel.cn/api/paas/v4
"""

import httpx
import json
import logging
from typing import Optional, Dict, Any, AsyncIterator, Union
from pathlib import Path

logger = logging.getLogger(__name__)


class ZhipuAIClient:
    """
    智谱AI HTTP客户端
    
    统一使用HTTP API调用所有智谱AI服务：
    - 对话补全（Chat Completions）
    - 语音转文字（STT）
    - 文字转语音（TTS）
    - 图像生成
    - 文本嵌入
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://open.bigmodel.cn/api/paas/v4",
        timeout: float = 300.0
    ):
        """
        初始化客户端
        
        Args:
            api_key: 智谱AI API密钥
            base_url: API基础URL
            timeout: 请求超时时间（秒）
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        
        # 创建HTTP客户端
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers=self._get_headers()
        )
    
    def _get_headers(self, content_type: str = "application/json") -> Dict[str, str]:
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": content_type
        }
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()
    
    # ============================================
    # 对话补全（Chat Completions）
    # ============================================
    
    async def chat_completions(
        self,
        model: str,
        messages: list,
        stream: bool = False,
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Union[Dict[str, Any], AsyncIterator[str]]:
        """
        对话补全
        
        Args:
            model: 模型名称，如 "glm-4.6", "autoglm-phone"
            messages: 消息列表 [{"role": "user", "content": "hello"}]
            stream: 是否流式输出
            temperature: 温度参数 (0.0-1.0)
            top_p: Top-p采样
            max_tokens: 最大token数
            **kwargs: 其他参数（tools, tool_choice等）
        
        Returns:
            非流式: 完整响应字典
            流式: 异步生成器，yield 每个chunk的文本
        
        API文档: https://docs.bigmodel.cn/cn/api/chat/completions
        """
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "temperature": temperature,
            "top_p": top_p,
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        # 添加其他参数
        payload.update(kwargs)
        
        if stream:
            # 流式输出
            return self._stream_chat(url, payload)
        else:
            # 非流式输出
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
    
    async def _stream_chat(self, url: str, payload: Dict) -> AsyncIterator[str]:
        """
        流式对话生成器
        
        Yields:
            每个chunk的文本内容
        """
        async with self.client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                if not line or line.startswith(':'):
                    continue
                
                # SSE格式: "data: {...}"
                if line.startswith('data: '):
                    data_str = line[6:]  # 去掉 "data: "
                    
                    if data_str == '[DONE]':
                        break
                    
                    try:
                        data = json.loads(data_str)
                        
                        # 提取content
                        if 'choices' in data and len(data['choices']) > 0:
                            choice = data['choices'][0]
                            
                            # 流式响应中是delta
                            if 'delta' in choice and 'content' in choice['delta']:
                                content = choice['delta']['content']
                                if content:
                                    yield content
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse SSE data: {data_str}, error: {e}")
                        continue
    
    # ============================================
    # 语音转文字（STT）
    # ============================================
    
    async def audio_transcriptions(
        self,
        audio_file: Union[bytes, Path, str],
        model: str = "glm-asr-2512",
        filename: str = "audio.mp3",
        prompt: Optional[str] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        语音转文字（Speech-to-Text）
        
        官方API文档: https://docs.bigmodel.cn/api-reference/模型-api/语音转文本
        
        Args:
            audio_file: 音频文件（bytes、文件路径）
                - 支持格式: .wav / .mp3
                - 文件大小: ≤ 25 MB
                - 音频时长: ≤ 30 秒
            model: 模型名称，默认 "glm-asr-2512"
            filename: 文件名（当audio_file是bytes时使用）
            prompt: 上下文提示词，用于长文本场景（建议 < 8000字）
            stream: 是否使用流式输出（默认False）
        
        Returns:
            {
                "text": "识别的文本内容",
                "model": "glm-asr-2512",
                "id": "任务ID",
                "created": 1234567890
            }
        
        完整curl示例:
            curl -X POST "https://open.bigmodel.cn/api/paas/v4/audio/transcriptions" \\
              -H "Authorization: Bearer YOUR_API_KEY" \\
              -F "file=@audio.mp3" \\
              -F "model=glm-asr-2512" \\
              -F "prompt=上下文提示"
        """
        url = f"{self.base_url}/audio/transcriptions"
        
        # 准备文件（multipart/form-data）
        import mimetypes
        
        if isinstance(audio_file, bytes):
            # 从filename推断MIME类型
            mime_type = mimetypes.guess_type(filename)[0] or "audio/mpeg"
            logger.debug(f"STT: filename={filename}, size={len(audio_file)} bytes, mime={mime_type}")
            files = {"file": (filename, audio_file, mime_type)}
        
        elif isinstance(audio_file, (str, Path)):
            audio_path = Path(audio_file)
            mime_type = mimetypes.guess_type(str(audio_path))[0] or "audio/mpeg"
            
            with open(audio_file, "rb") as f:
                audio_data = f.read()
            
            logger.debug(f"STT: file={audio_path.name}, size={len(audio_data)} bytes, mime={mime_type}")
            files = {"file": (audio_path.name, audio_data, mime_type)}
        
        else:
            raise ValueError(f"Unsupported audio_file type: {type(audio_file)}")
        
        # 构建表单数据（multipart/form-data）
        data = {
            "model": model,
            "stream": "true" if stream else "false"
        }
        
        # 添加可选参数
        if prompt:
            if len(prompt) > 8000:
                logger.warning(f"Prompt too long ({len(prompt)} chars), truncating to 8000")
                prompt = prompt[:8000]
            data["prompt"] = prompt
            logger.debug(f"使用上下文提示词: {prompt[:50]}...")
        
        logger.info(f"🎤 Zhipu STT: model={model}, stream={stream}, prompt={'yes' if prompt else 'no'}")
        logger.debug(f"🎤 Request URL: {url}")
        
        # 调用API
        try:
            # 创建独立的client，确保multipart/form-data正确编码
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
                response = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    files=files,
                    data=data
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"STT Success: text_length={len(result.get('text', ''))}")
                return result
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if hasattr(e, 'response') else str(e)
            logger.error(f"Zhipu STT Error: status={e.response.status_code}")
            logger.error(f"Detail: {error_detail}")
            logger.error(f"Request data: model={model}, stream={stream}, prompt_len={len(prompt) if prompt else 0}")
            raise
        except Exception as e:
            logger.error(f"Unexpected STT error: {e}", exc_info=True)
            raise
    
    # ============================================
    # 文字转语音（TTS）
    # ============================================
    
    async def audio_speech(
        self,
        text: str,
        model: str = "glm-tts",
        voice: str = "tongtong",
        speed: float = 1.0,
        volume: float = 1.0,
        response_format: str = "wav",
        stream: bool = False,
        watermark_enabled: bool = True
    ) -> bytes:
        """
        文字转语音（非流式）
        
        Args:
            text: 要转换的文本（≤1024字符）
            model: 模型名称，默认 "glm-tts"
            voice: 音色选择
                - tongtong: 彤彤（默认）
                - chuichui: 锤锤
                - xiaochen: 小陈
                - jam/kazi/douji/luodo: 动动动物圈系列
            speed: 语速，范围 0.5-2.0，默认 1.0
            volume: 音量，范围 0-10，默认 1.0
            response_format: 输出格式，"wav" 或 "pcm"
            stream: 是否流式输出（此方法固定为False）
            watermark_enabled: 是否添加AI生成水印
        
        Returns:
            音频文件的二进制数据
        
        API文档: https://docs.bigmodel.cn/api-reference/模型-api/文本转语音
        """
        url = f"{self.base_url}/audio/speech"
        
        # 检查文本长度
        if len(text) > 1024:
            logger.warning(f"Text too long: {len(text)} chars, truncating to 1024")
            text = text[:1024]
        
        payload = {
            "model": model,
            "input": text,  # 官方文档使用 input 字段
            "voice": voice,
            "speed": max(0.5, min(2.0, speed)),  # 限制范围 [0.5, 2]
            "volume": max(0.0, min(10.0, volume)),  # 限制范围 (0, 10]
            "response_format": response_format,  # wav 或 pcm
            "stream": False,
            "watermark_enabled": watermark_enabled
        }
        
        logger.info(f"Calling Zhipu TTS API: voice={voice}, text_len={len(text)}, format={response_format}")
        
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        
        # 返回二进制音频数据
        return response.content
    
    async def audio_speech_stream(
        self,
        text: str,
        model: str = "glm-tts",
        voice: str = "tongtong",
        speed: float = 1.0,
        volume: float = 1.0,
        encode_format: str = "base64",
        watermark_enabled: bool = True
    ) -> AsyncIterator[bytes]:
        """
        流式文字转语音
        
        Args:
            text: 要转换的文本（≤1024字符）
            model: 模型名称，默认 "glm-tts"
            voice: 音色选择（同audio_speech）
            speed: 语速，范围 0.5-2.0
            volume: 音量，范围 0-10
            encode_format: 编码格式，"base64" 或 "hex"
            watermark_enabled: 是否添加AI生成水印
        
        Yields:
            音频数据块（PCM格式）
            
        注意: 流式输出仅支持PCM格式
        """
        url = f"{self.base_url}/audio/speech"
        
        # 检查文本长度
        if len(text) > 1024:
            logger.warning(f"Text too long: {len(text)} chars, truncating to 1024")
            text = text[:1024]
        
        payload = {
            "model": model,
            "input": text,
            "voice": voice,
            "speed": max(0.5, min(2.0, speed)),
            "volume": max(0.0, min(10.0, volume)),
            "response_format": "pcm",  # 流式仅支持pcm
            "stream": True,
            "encode_format": encode_format,
            "watermark_enabled": watermark_enabled
        }
        
        logger.info(f"Calling Zhipu TTS Stream API: voice={voice}, text_len={len(text)}")
        
        async with self.client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            
            async for chunk in response.aiter_bytes(chunk_size=1024):
                if chunk:
                    yield chunk
    
    # ============================================
    # 图像生成
    # ============================================
    
    async def images_generations(
        self,
        prompt: str,
        model: str = "cogview-3",
        size: str = "1024x1024",
        n: int = 1
    ) -> Dict[str, Any]:
        """
        图像生成
        
        Args:
            prompt: 图像描述提示词
            model: 模型名称，默认 "cogview-3"
            size: 图像尺寸，如 "1024x1024"
            n: 生成图像数量
        
        Returns:
            {
                "data": [
                    {
                        "url": "图像URL",
                        "b64_json": "base64编码的图像"
                    }
                ],
                ...
            }
        
        API文档: https://docs.bigmodel.cn/cn/api/images/generations
        """
        url = f"{self.base_url}/images/generations"
        
        payload = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "n": n
        }
        
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    
    # ============================================
    # 文本嵌入（Embeddings）
    # ============================================
    
    async def embeddings(
        self,
        input_text: Union[str, list],
        model: str = "embedding-2"
    ) -> Dict[str, Any]:
        """
        文本嵌入
        
        Args:
            input_text: 输入文本（字符串或字符串列表）
            model: 模型名称，默认 "embedding-2"
        
        Returns:
            {
                "data": [
                    {
                        "embedding": [0.1, 0.2, ...],
                        "index": 0
                    }
                ],
                "model": "embedding-2",
                ...
            }
        
        API文档: https://docs.bigmodel.cn/cn/api/embeddings
        """
        url = f"{self.base_url}/embeddings"
        
        payload = {
            "model": model,
            "input": input_text
        }
        
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


# ============================================
# 便捷函数
# ============================================

def get_zhipu_client(api_key: str) -> ZhipuAIClient:
    """
    获取智谱AI客户端实例
    
    Args:
        api_key: API密钥
    
    Returns:
        ZhipuAIClient实例
    """
    return ZhipuAIClient(api_key=api_key)


# ============================================
# 使用示例
# ============================================

"""
# 初始化客户端
client = ZhipuAIClient(api_key="your_api_key")

# 1. 对话补全（非流式）
response = await client.chat_completions(
    model="autoglm-phone",
    messages=[
        {"role": "system", "content": "你是一个AI助手"},
        {"role": "user", "content": "你好"}
    ]
)
print(response['choices'][0]['message']['content'])

# 2. 对话补全（流式）
async for text in await client.chat_completions(
    model="glm-4.6",
    messages=[{"role": "user", "content": "讲个故事"}],
    stream=True
):
    print(text, end='', flush=True)

# 3. 语音转文字
result = await client.audio_transcriptions(
    audio_file="audio.wav"
)
print(result['text'])

# 4. 文字转语音
audio_data = await client.audio_speech(
    text="你好，我是AI助手",
    voice="female"
)
with open("output.mp3", "wb") as f:
    f.write(audio_data)

# 5. 文字转语音（流式）
with open("output.mp3", "wb") as f:
    async for chunk in await client.audio_speech_stream(
        text="这是一段较长的文本..."
    ):
        f.write(chunk)

# 6. 图像生成
result = await client.images_generations(
    prompt="一只可爱的猫"
)
print(result['data'][0]['url'])

# 7. 文本嵌入
result = await client.embeddings(
    input_text="这是一段测试文本"
)
print(result['data'][0]['embedding'][:5])

# 关闭客户端
await client.close()
"""

