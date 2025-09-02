import os
import threading
import time
from typing import List, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """配置管理类"""
    
    # 鉴权配置
    AUTH_KEY = os.getenv('AUTH_KEY', 'kimi2api-auth-key-2024')
    
    # 服务器配置
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 8000))
    
    # 连接池配置
    MAX_CONNECTIONS = int(os.getenv('MAX_CONNECTIONS', 600))
    MAX_KEEPALIVE_CONNECTIONS = int(os.getenv('MAX_KEEPALIVE_CONNECTIONS', 500))
    KEEPALIVE_EXPIRY = int(os.getenv('KEEPALIVE_EXPIRY', 10))
    
    # Refresh Token池
    _refresh_tokens = []
    _token_index = 0
    _token_lock = threading.Lock()
    
    @classmethod
    def _load_refresh_tokens(cls):
        """从环境变量加载refresh tokens"""
        tokens_str = os.getenv('REFRESH_TOKENS', '')
        if tokens_str:
            cls._refresh_tokens = [token.strip() for token in tokens_str.split(',') if token.strip()]
        else:
            cls._refresh_tokens = []
    
    @classmethod
    def get_next_refresh_token(cls) -> Optional[str]:
        """
        获取下一个refresh token (轮询方式)
        线程安全的实现
        """
        if not cls._refresh_tokens:
            cls._load_refresh_tokens()
        
        if not cls._refresh_tokens:
            return None
        
        with cls._token_lock:
            token = cls._refresh_tokens[cls._token_index]
            cls._token_index = (cls._token_index + 1) % len(cls._refresh_tokens)
            return token
    
    @classmethod
    def get_refresh_tokens(cls) -> List[str]:
        """获取所有refresh tokens"""
        if not cls._refresh_tokens:
            cls._load_refresh_tokens()
        return cls._refresh_tokens.copy()
    
    @classmethod
    def reload_config(cls):
        """重新加载配置"""
        load_dotenv(override=True)
        cls._load_refresh_tokens()
    
    @classmethod
    def get_connection_limits(cls) -> dict:
        """获取连接池配置"""
        return {
            'max_connections': cls.MAX_CONNECTIONS,
            'max_keepalive_connections': cls.MAX_KEEPALIVE_CONNECTIONS,
            'keepalive_expiry': cls.KEEPALIVE_EXPIRY
        }

# 初始化加载tokens
Config._load_refresh_tokens()