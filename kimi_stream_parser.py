import json
import re
from typing import Generator, Dict, Any, Optional

class KimiStreamParser:
    """Kimi流响应解析器，基于实际的API响应格式"""
    
    def __init__(self):
        self.content = ""
        self.buffer = b""
        
    def parse_stream_data(self, data: bytes) -> Generator[Dict[str, Any], None, None]:
        """解析Kimi流数据"""
        self.buffer += data
        
        while len(self.buffer) >= 4:
            # 查找长度前缀 (4字节的null字节 + 1字节长度)
            if self.buffer.startswith(b'\x00\x00\x00\x00'):
                if len(self.buffer) < 5:
                    break
                    
                # 获取消息长度
                length = self.buffer[4]
                total_length = 5 + length
                
                if len(self.buffer) < total_length:
                    break
                
                # 提取JSON消息
                json_data = self.buffer[5:total_length]
                self.buffer = self.buffer[total_length:]
                
                try:
                    # 解析JSON
                    json_str = json_data.decode('utf-8', errors='ignore')
                    message = json.loads(json_str)
                    yield message
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
            else:
                # 跳过无法识别的字节
                self.buffer = self.buffer[1:]
    
    def extract_content_from_message(self, message: Dict[str, Any]) -> Optional[str]:
        """从消息中提取文本内容"""
        try:
            # 检查是否是append操作，包含block.text.content
            if (message.get('op') == 'append' and 
                message.get('mask') == 'block.text.content' and 
                'block' in message):
                
                block = message['block']
                if 'text' in block and 'content' in block['text']:
                    content = block['text']['content']
                    # 过滤掉控制字符和编码错误
                    if content and self._is_valid_text(content):
                        return content
            
            # 检查是否是消息完成状态
            elif (message.get('op') == 'set' and 
                  message.get('mask') == 'message' and 
                  'message' in message):
                
                msg = message['message']
                if (msg.get('role') == 'assistant' and 
                    msg.get('status') == 'MESSAGE_STATUS_COMPLETED' and 
                    'blocks' in msg):
                    
                    # 提取所有文本块的内容
                    content_parts = []
                    for block in msg['blocks']:
                        if 'text' in block and 'content' in block['text']:
                            content_parts.append(block['text']['content'])
                    
                    return ''.join(content_parts)
            
            return None
            
        except (KeyError, TypeError, AttributeError):
            return None
    
    def _is_valid_text(self, text: str) -> bool:
        """检查文本是否有效（非控制字符）"""
        if not text:
            return False
        
        # 检查是否只包含无效字符（如控制字符、编码错误字符等）
        # 如果字符串包含大量不可打印字符，可能是编码错误
        printable_count = sum(1 for char in text if char.isprintable() or char in '\n\r\t ')
        
        # 如果可打印字符太少，认为是无效文本
        if len(text) > 1 and printable_count / len(text) < 0.5:
            return False
        
        # 过滤特定的无效模式
        # 如果文本只包含特殊符号或控制字符的组合，认为无效
        stripped = text.strip()
        if not stripped:
            return False
            
        # 检查是否包含常见的编码错误字符
        invalid_chars = ['��', '�', '\ufffd']
        if any(invalid in text for invalid in invalid_chars):
            # 如果包含编码错误字符，但还有其他有效内容，则尝试清理
            cleaned = text
            for invalid in invalid_chars:
                cleaned = cleaned.replace(invalid, '')
            if cleaned.strip():
                return False  # 暂时拒绝包含编码错误的内容
            return False
        
        return True
    
    def is_stream_complete(self, message: Dict[str, Any]) -> bool:
        """判断流是否完成"""
        try:
            # 检查是否有done事件（更准确的完成标志）
            if 'done' in message:
                return True
            
            # 备用检查：消息状态完成
            return (message.get('op') == 'set' and 
                    message.get('mask') == 'message.status' and 
                    'message' in message and 
                    message['message'].get('status') == 'MESSAGE_STATUS_COMPLETED')
        except (KeyError, TypeError, AttributeError):
            return False