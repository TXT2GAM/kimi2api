import json
import time
import random
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator
import httpx
from models import Message, KimiStreamEvent
from kimi_stream_parser import KimiStreamParser

class KimiClient:
    def __init__(self):
        self.base_url = "https://www.kimi.com"
        self.device_id = str(random.randint(7000000000000000000, 9999999999999999999))
        self.session_id = str(random.randint(1700000000000000000, 1999999999999999999))
        self.access_token_map = {}
        self.access_token_expires = 300
        
    def _get_headers(self, access_token: Optional[str] = None) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            'accept': '*/*',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'cache-control': 'no-cache',
            'origin': 'https://www.kimi.com',
            'referer': 'https://www.kimi.com/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
            'x-msh-device-id': self.device_id,
            'x-msh-platform': 'web',
            'x-msh-session-id': self.session_id,
            'r-timezone': 'Asia/Shanghai',
            'x-language': 'zh-CN'
        }
        
        if access_token:
            headers['authorization'] = f'Bearer {access_token}'
            
        return headers
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """刷新访问令牌"""
        if refresh_token in self.access_token_map:
            token_info = self.access_token_map[refresh_token]
            if time.time() < token_info.get('expires_at', 0):
                return token_info
        
        headers = self._get_headers()
        headers['authorization'] = f'Bearer {refresh_token}'
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/auth/token/refresh",
                headers=headers,
                timeout=15.0
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to refresh token: {response.status_code}")
            
            data = response.json()
            access_token = data.get('access_token')
            
            if not access_token:
                raise Exception("No access token in response")
            
            token_info = {
                'access_token': access_token,
                'expires_at': time.time() + self.access_token_expires
            }
            
            self.access_token_map[refresh_token] = token_info
            return token_info
    
    async def create_conversation(self, access_token: str, name: str = "未命名会话") -> str:
        """创建会话"""
        headers = self._get_headers(access_token)
        headers['content-type'] = 'application/json'
        
        data = {
            "enter_method": "new_chat",
            "is_example": False,
            "kimiplus_id": "kimi",
            "name": name
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                headers=headers,
                json=data,
                timeout=15.0
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to create conversation: {response.status_code}")
            
            result = response.json()
            return result.get('id')
    
    async def delete_conversation(self, access_token: str, conv_id: str):
        """删除会话"""
        headers = self._get_headers(access_token)
        
        async with httpx.AsyncClient() as client:
            await client.delete(
                f"{self.base_url}/api/chat/{conv_id}",
                headers=headers,
                timeout=15.0
            )
    
    async def chat_completion_stream(
        self, 
        access_token: str, 
        conv_id: str, 
        messages: list[Message]
    ) -> AsyncGenerator[KimiStreamEvent, None]:
        """流式聊天完成"""
        headers = self._get_headers(access_token)
        headers['content-type'] = 'application/connect+json'
        headers['connect-protocol-version'] = '1'
        headers['x-traffic-id'] = 'd1p2t8gc86s7p05dmj70'
        
        # 构建请求数据
        last_message = messages[-1] if messages else None
        if not last_message:
            raise Exception("No messages provided")
        
        # Based on the capture, the correct format should be:
        payload = {
            "scenario": "SCENARIO_K2",
            "message": {
                "role": "user",
                "blocks": [{
                    "message_id": "",
                    "text": {
                        "content": last_message.content
                    }
                }],
                "scenario": "SCENARIO_K2"
            }
        }
        
        # Calculate the correct length prefix based on the capture
        payload_json = json.dumps(payload)
        payload_bytes = payload_json.encode('utf-8')
        length = len(payload_bytes)
        
        # The capture shows: \x00\x00\x00\x00\x86 which suggests a 5-byte header
        # Let's try the exact format from capture
        data = b'\x00\x00\x00\x00' + bytes([length]) + payload_bytes
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                'POST',
                f"{self.base_url}/apiv2/kimi.chat.v1.ChatService/Chat",
                headers=headers,
                content=data
            ) as response:
                if response.status_code != 200:
                    raise Exception(f"Chat API failed: {response.status_code}")
                
                # 使用专门的解析器处理Kimi流响应
                parser = KimiStreamParser()
                
                # 发送开始事件
                yield KimiStreamEvent(event="req", id=conv_id)
                
                # 处理流式响应
                async for chunk in response.aiter_bytes():
                    # 解析二进制数据中的JSON消息
                    for message in parser.parse_stream_data(chunk):
                        # 提取文本内容
                        content = parser.extract_content_from_message(message)
                        if content:
                            yield KimiStreamEvent(event="cmpl", text=content)
                        
                        # 检查是否完成
                        if parser.is_stream_complete(message):
                            yield KimiStreamEvent(event="all_done")
                            return
    
    async def chat_completion(
        self, 
        access_token: str, 
        conv_id: str, 
        messages: list[Message]
    ) -> str:
        """非流式聊天完成"""
        content = ""
        
        async for event in self.chat_completion_stream(access_token, conv_id, messages):
            if event.event == 'cmpl' and event.text:
                content += event.text
            elif event.event == 'all_done':
                break
            elif event.event == 'error':
                content += '\n[内容由于不合规被停止生成，我们换个话题吧]'
                break
        
        return content or "Hello! I'm Kimi, how can I help you?"