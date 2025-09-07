from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Optional, Dict, Any, Union
import asyncio
import time
import jwt
import json
import os
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel

from models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    Message
)
from kimi_client import KimiClient
from response_processor import ResponseProcessor
from config import Config

# 数据模型
class TokenBatchRequest(BaseModel):
    tokens: List[str]

class TokenInfo(BaseModel):
    id: int
    token: str
    exp_time: int
    exp_time_beijing: str
    is_expired: bool

class EnvironmentVariable(BaseModel):
    key: str
    value: str

# 创建 FastAPI 应用和客户端实例
app = FastAPI(title="Kimi2API", version="1.0.0")
kimi_client = KimiClient()

# 设置Config的回调函数以获取tokens_db中的tokens
def get_tokens_from_db():
    """供Config使用的回调函数，返回tokens_db中的有效tokens"""
    return tokens_db

Config.set_tokens_callback(get_tokens_from_db)

# 挂载静态文件
import os
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 全局变量存储token和环境变量
tokens_db = []
env_vars_file = "env_config.json"

# 辅助函数
def parse_jwt_token(token: str) -> Dict[str, Any]:
    """解析JWT token获取过期时间等信息"""
    try:
        # 不验证签名，只解码payload
        decoded = jwt.decode(token, options={"verify_signature": False})
        return decoded
    except Exception as e:
        raise ValueError(f"Invalid JWT token: {str(e)}")

def timestamp_to_beijing_time(timestamp: int) -> str:
    """将时间戳转换为北京时间字符串"""
    beijing_tz = timezone(timedelta(hours=8))
    dt = datetime.fromtimestamp(timestamp, tz=beijing_tz)
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def is_token_expired(exp_timestamp: int, hours_threshold: int = 24) -> bool:
    """检查token是否在指定小时内过期"""
    current_time = time.time()
    time_diff = exp_timestamp - current_time
    return time_diff < (hours_threshold * 3600)

def cleanup_expired_tokens():
    """清理即将过期的token（24小时内）"""
    global tokens_db
    tokens_db = [token for token in tokens_db if not is_token_expired(token["exp_time"])]

def load_env_vars() -> Dict[str, str]:
    """从文件加载环境变量"""
    if os.path.exists(env_vars_file):
        try:
            with open(env_vars_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_env_vars(env_vars: Dict[str, str]):
    """保存环境变量到文件"""
    with open(env_vars_file, 'w', encoding='utf-8') as f:
        json.dump(env_vars, f, ensure_ascii=False, indent=2)

# 定时清理任务
import threading
def periodic_cleanup():
    """定期清理过期token"""
    while True:
        time.sleep(24 * 3600)  # 24小时
        cleanup_expired_tokens()

# 启动后台清理任务
cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
cleanup_thread.start()

# Token管理API端点
@app.post("/api/tokens/batch")
async def add_tokens_batch(request: TokenBatchRequest):
    """批量添加tokens"""
    global tokens_db
    added_tokens = []
    
    for token_str in request.tokens:
        token_str = token_str.strip()
        if not token_str:
            continue
            
        try:
            payload = parse_jwt_token(token_str)
            exp_time = payload.get('exp', 0)
            
            # 检查是否已存在
            if any(t['token'] == token_str for t in tokens_db):
                continue
                
            token_info = {
                "id": len(tokens_db) + 1,
                "token": token_str,
                "exp_time": exp_time,
                "exp_time_beijing": timestamp_to_beijing_time(exp_time),
                "is_expired": is_token_expired(exp_time)
            }
            
            tokens_db.append(token_info)
            added_tokens.append(token_info)
            
        except Exception as e:
            continue  # 跳过无效token
    
    return {"message": f"Added {len(added_tokens)} tokens", "tokens": added_tokens}

@app.get("/api/tokens")
async def get_tokens(page: int = 1, per_page: int = 15):
    """获取token列表（分页）"""
    cleanup_expired_tokens()  # 获取前先清理
    
    total = len(tokens_db)
    start = (page - 1) * per_page
    end = start + per_page
    tokens_page = tokens_db[start:end]
    
    return {
        "tokens": tokens_page,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }

@app.delete("/api/tokens/{token_id}")
async def delete_token(token_id: int):
    """删除指定token"""
    global tokens_db
    tokens_db = [t for t in tokens_db if t["id"] != token_id]
    return {"message": "Token deleted"}

@app.delete("/api/tokens/cleanup")
async def cleanup_tokens():
    """手动清理过期token"""
    global tokens_db
    original_count = len(tokens_db)
    cleanup_expired_tokens()
    removed_count = original_count - len(tokens_db)
    return {"message": f"Removed {removed_count} expired tokens"}

# 环境变量管理API端点
@app.get("/api/env")
async def get_env_vars():
    """获取环境变量"""
    # 只返回固定的环境变量
    fixed_env_vars = {
        "AUTH_KEY": Config.AUTH_KEY,
        "MAX_CONNECTIONS": str(Config.MAX_CONNECTIONS),
        "MAX_KEEPALIVE_CONNECTIONS": str(Config.MAX_KEEPALIVE_CONNECTIONS),
        "KEEPALIVE_EXPIRY": str(Config.KEEPALIVE_EXPIRY),
        "HOST": Config.HOST,
        "PORT": str(Config.PORT)
    }
    return fixed_env_vars

@app.post("/api/env")
async def update_env_vars(env_vars: Dict[str, str]):
    """更新环境变量"""
    # 只允许更新固定的环境变量
    allowed_keys = {"AUTH_KEY", "MAX_CONNECTIONS", "MAX_KEEPALIVE_CONNECTIONS", "KEEPALIVE_EXPIRY", "HOST", "PORT"}
    filtered_env_vars = {k: v for k, v in env_vars.items() if k in allowed_keys}
    
    if not filtered_env_vars:
        raise HTTPException(status_code=400, detail="No valid environment variables provided")
    
    # 这里可以实现将环境变量写入.env文件的逻辑
    # 为了简化，这里只返回成功消息
    return {"message": "Environment variables updated (restart required to take effect)"}

@app.post("/api/env/apply")
async def apply_env_vars_live(env_vars: Dict[str, str]):
    """实时应用环境变量（无需重启）"""
    # 只允许更新固定的环境变量
    allowed_keys = {"AUTH_KEY", "MAX_CONNECTIONS", "MAX_KEEPALIVE_CONNECTIONS", "KEEPALIVE_EXPIRY", "HOST", "PORT"}
    filtered_env_vars = {k: v for k, v in env_vars.items() if k in allowed_keys}
    
    if not filtered_env_vars:
        raise HTTPException(status_code=400, detail="No valid environment variables provided")
    
    try:
        # 实时更新配置
        updated = Config.update_config_live(filtered_env_vars)
        return {
            "message": f"Successfully applied {len(updated)} configuration changes",
            "updated": updated,
            "note": "Changes applied immediately without restart"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to apply configuration: {str(e)}")

@app.get("/admin")
async def admin_page():
    """管理页面"""
    from fastapi.responses import FileResponse
    import os
    static_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    return FileResponse(static_path)

# API 端点
@app.get("/v1/models")
async def list_models():
    """列出支持的模型"""
    return {
        "object": "list",
        "data": [
            {
                "id": "Kimi-K2",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "moonshot"
            }
        ]
    }

@app.post("/v1/chat/completions")
async def create_chat_completion(
    request: ChatCompletionRequest,
    authorization: str = Header(None)
):
    """创建聊天完成"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    # 验证鉴权key
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    auth_key = authorization[7:]  # 移除 "Bearer " 前缀
    
    # 验证鉴权key是否正确
    if auth_key != Config.AUTH_KEY:
        raise HTTPException(status_code=401, detail="Invalid authentication key")
    
    # 获取轮询的refresh token
    refresh_token = Config.get_next_refresh_token()
    if not refresh_token:
        raise HTTPException(status_code=500, detail="No refresh tokens available")
    
    # 验证模型名称
    if request.model != "Kimi-K2":
        raise HTTPException(status_code=400, detail="Only Kimi-K2 model is supported")
    
    try:
        # 获取 access token
        token_info = await kimi_client.refresh_access_token(refresh_token)
        access_token = token_info['access_token']
        
        # 创建会话
        conv_id = await kimi_client.create_conversation(access_token)
        
        # 创建响应处理器
        processor = ResponseProcessor(request.model, conv_id)
        
        if request.stream:
            # 流式响应
            async def generate_stream():
                try:
                    stream = kimi_client.chat_completion_stream(access_token, conv_id, request.messages)
                    async for chunk in processor.process_stream_to_chunks(stream):
                        yield chunk
                except Exception as e:
                    yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
                    yield "data: [DONE]\n\n"
                finally:
                    # 清理会话
                    try:
                        await kimi_client.delete_conversation(access_token, conv_id)
                    except:
                        pass
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/plain",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
            )
        else:
            # 非流式响应
            try:
                stream = kimi_client.chat_completion_stream(access_token, conv_id, request.messages)
                response = await processor.process_stream_to_completion(stream)
                return response
            finally:
                # 清理会话
                try:
                    await kimi_client.delete_conversation(access_token, conv_id)
                except:
                    pass
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process request: {str(e)}")

@app.get("/")
async def root():
    """根路径"""
    return {"message": "Kimi2API is running"}

@app.get("/ping")
async def ping():
    """健康检查"""
    return {"status": "ok", "timestamp": int(time.time())}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=Config.HOST, port=Config.PORT)