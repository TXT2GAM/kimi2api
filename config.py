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
    
    # 用于从main.py中的tokens_db获取tokens的回调函数
    _get_tokens_callback = None
    
    @classmethod
    def _load_refresh_tokens(cls):
        """从环境变量加载refresh tokens"""
        tokens_str = os.getenv('REFRESH_TOKENS', '')
        if tokens_str:
            cls._refresh_tokens = [token.strip() for token in tokens_str.split(',') if token.strip()]
        else:
            cls._refresh_tokens = []
    
    @classmethod
    def set_tokens_callback(cls, callback):
        """设置获取tokens的回调函数"""
        cls._get_tokens_callback = callback
    
    @classmethod
    def _get_active_tokens(cls) -> List[str]:
        """获取有效的refresh tokens"""
        # 优先从回调函数获取tokens（前端管理的）
        if cls._get_tokens_callback:
            try:
                db_tokens = cls._get_tokens_callback()
                active_tokens = [t['token'] for t in db_tokens if not t.get('is_expired', False)]
                if active_tokens:
                    return active_tokens
            except:
                pass
        
        # fallback到环境变量
        if not cls._refresh_tokens:
            cls._load_refresh_tokens()
        return cls._refresh_tokens
    
    @classmethod
    def get_next_refresh_token(cls) -> Optional[str]:
        """
        获取下一个refresh token (轮询方式)
        线程安全的实现
        """
        active_tokens = cls._get_active_tokens()
        
        if not active_tokens:
            return None
        
        with cls._token_lock:
            token = active_tokens[cls._token_index % len(active_tokens)]
            cls._token_index = (cls._token_index + 1) % len(active_tokens)
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
    
    @classmethod
    def update_config_live(cls, config_dict: dict) -> dict:
        """实时更新配置（无需重启）"""
        updated = {}
        
        if 'AUTH_KEY' in config_dict:
            cls.AUTH_KEY = config_dict['AUTH_KEY']
            updated['AUTH_KEY'] = config_dict['AUTH_KEY']
        
        if 'MAX_CONNECTIONS' in config_dict:
            cls.MAX_CONNECTIONS = int(config_dict['MAX_CONNECTIONS'])
            updated['MAX_CONNECTIONS'] = cls.MAX_CONNECTIONS
        
        if 'MAX_KEEPALIVE_CONNECTIONS' in config_dict:
            cls.MAX_KEEPALIVE_CONNECTIONS = int(config_dict['MAX_KEEPALIVE_CONNECTIONS'])
            updated['MAX_KEEPALIVE_CONNECTIONS'] = cls.MAX_KEEPALIVE_CONNECTIONS
        
        if 'KEEPALIVE_EXPIRY' in config_dict:
            cls.KEEPALIVE_EXPIRY = int(config_dict['KEEPALIVE_EXPIRY'])
            updated['KEEPALIVE_EXPIRY'] = cls.KEEPALIVE_EXPIRY
        
        if 'HOST' in config_dict:
            cls.HOST = config_dict['HOST']
            updated['HOST'] = config_dict['HOST']
        
        if 'PORT' in config_dict:
            cls.PORT = int(config_dict['PORT'])
            updated['PORT'] = cls.PORT
        
        return updated

# 初始化加载tokens
Config._load_refresh_tokens()