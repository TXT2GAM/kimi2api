#!/usr/bin/env python3
"""
测试脚本，验证环境配置和功能
"""

import asyncio
import httpx
import time
import jwt
from datetime import datetime, timezone, timedelta

# 测试用的示例JWT token（仅用于格式测试，非真实token）
SAMPLE_JWT_TOKEN = "eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ1c2VyLWNlbnRlciIsImV4cCI6MTc2MjkyMjI3MCwiaWF0IjoxNzU1MTQ2MjcwLCJqdGkiOiJkMmVtZzdnaDhuamh2ZDZ0cmZyMCIsInR5cCI6InJlZnJlc2giLCJhcHBfaWQiOiJraW1pIiwic3NpZCI6IjE3MzEzNjM1NzY4ODI4MTM4NTgiLCJkZXZpY2VfaWQiOiI3NTI1ODczMTIxNzc0MDEyNDI0In0.dummy_signature"

async def test_api_endpoints():
    """测试API端点"""
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        try:
            # 测试健康检查
            print("测试健康检查...")
            response = await client.get(f"{base_url}/ping")
            print(f"健康检查: {response.status_code} - {response.json()}")
            
            # 测试模型列表
            print("\n测试模型列表...")
            response = await client.get(f"{base_url}/v1/models")
            print(f"模型列表: {response.status_code} - {response.json()}")
            
            # 测试添加token
            print("\n测试批量添加token...")
            token_data = {"tokens": [SAMPLE_JWT_TOKEN]}
            response = await client.post(f"{base_url}/api/tokens/batch", json=token_data)
            print(f"添加token: {response.status_code} - {response.json()}")
            
            # 测试获取token列表
            print("\n测试获取token列表...")
            response = await client.get(f"{base_url}/api/tokens")
            print(f"token列表: {response.status_code} - {response.json()}")
            
            # 测试环境变量
            print("\n测试环境变量...")
            env_data = {"TEST_VAR": "test_value", "ANOTHER_VAR": "another_value"}
            response = await client.post(f"{base_url}/api/env", json=env_data)
            print(f"保存环境变量: {response.status_code} - {response.json()}")
            
            response = await client.get(f"{base_url}/api/env")
            print(f"获取环境变量: {response.status_code} - {response.json()}")
            
        except Exception as e:
            print(f"测试过程中出现错误: {e}")

def test_jwt_parsing():
    """测试JWT解析功能"""
    print("\n测试JWT解析功能...")
    
    try:
        # 解析JWT token（不验证签名）
        decoded = jwt.decode(SAMPLE_JWT_TOKEN, options={"verify_signature": False})
        print(f"解析结果: {decoded}")
        
        # 转换时间戳
        exp_time = decoded.get('exp', 0)
        beijing_tz = timezone(timedelta(hours=8))
        dt = datetime.fromtimestamp(exp_time, tz=beijing_tz)
        beijing_time = dt.strftime('%Y-%m-%d %H:%M:%S')
        print(f"过期时间（北京时间）: {beijing_time}")
        
        # 检查是否即将过期
        current_time = time.time()
        is_expiring = (exp_time - current_time) < (24 * 3600)
        print(f"是否即将过期（24小时内）: {is_expiring}")
        
    except Exception as e:
        print(f"JWT解析错误: {e}")

if __name__ == "__main__":
    print("=== Kimi2API 功能测试 ===")
    
    # 测试JWT解析
    test_jwt_parsing()
    
    # 测试API端点
    print("\n=== API端点测试 ===")
    print("请先启动服务器：python main.py")
    
    try:
        asyncio.run(test_api_endpoints())
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n无法连接到服务器，请确保服务已启动: {e}")
    
    print("\n=== 测试完成 ===")
    print("访问管理面板: http://localhost:8000/admin")