import json
import time
from typing import AsyncGenerator, Dict, Any
from models import (
    ChatCompletionResponse, 
    ChatCompletionStreamResponse, 
    Choice, 
    StreamChoice, 
    Message, 
    Usage,
    KimiStreamEvent
)

class ResponseProcessor:
    """响应处理器，基于原项目的流处理逻辑"""
    
    def __init__(self, model: str, conv_id: str):
        self.model = model
        self.conv_id = conv_id
        self.created = int(time.time())
        
    async def process_stream_to_completion(
        self, 
        stream: AsyncGenerator[KimiStreamEvent, None]
    ) -> ChatCompletionResponse:
        """处理流响应为完整响应"""
        content = ""
        segment_id = ""
        finish_reason = "stop"
        
        async for event in stream:
            if event.event == 'cmpl' and event.text:
                content += event.text
            elif event.event == 'req' and event.id:
                segment_id = event.id
            elif event.event == 'length':
                finish_reason = "length"
            elif event.event == 'all_done':
                break
            elif event.event == 'error':
                content += '\n[内容由于不合规被停止生成，我们换个话题吧]'
                finish_reason = "stop"
                break
        
        # 计算token使用量（简化版本）
        prompt_tokens = 1  # 简化计算
        completion_tokens = len(content.split()) if content else 1
        
        return ChatCompletionResponse(
            id=f"chatcmpl-{self.conv_id}",
            object="chat.completion",
            created=self.created,
            model=self.model,
            choices=[Choice(
                index=0,
                message=Message(role="assistant", content=content),
                finish_reason=finish_reason
            )],
            usage=Usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens
            )
        )
    
    async def process_stream_to_chunks(
        self, 
        stream: AsyncGenerator[KimiStreamEvent, None]
    ) -> AsyncGenerator[str, None]:
        """处理流响应为SSE格式的chunk"""
        # 发送开始chunk
        start_chunk = ChatCompletionStreamResponse(
            id=f"chatcmpl-{self.conv_id}",
            object="chat.completion.chunk",
            created=self.created,
            model=self.model,
            choices=[StreamChoice(
                index=0,
                delta={"role": "assistant", "content": ""},
                finish_reason=None
            )]
        )
        yield f"data: {start_chunk.model_dump_json()}\n\n"
        
        # 处理内容chunk
        async for event in stream:
            if event.event == 'cmpl' and event.text:
                content_chunk = ChatCompletionStreamResponse(
                    id=f"chatcmpl-{self.conv_id}",
                    object="chat.completion.chunk",
                    created=self.created,
                    model=self.model,
                    choices=[StreamChoice(
                        index=0,
                        delta={"content": event.text},
                        finish_reason=None
                    )]
                )
                yield f"data: {content_chunk.model_dump_json()}\n\n"
                
            elif event.event == 'all_done':
                # 发送结束chunk
                end_chunk = ChatCompletionStreamResponse(
                    id=f"chatcmpl-{self.conv_id}",
                    object="chat.completion.chunk",
                    created=self.created,
                    model=self.model,
                    choices=[StreamChoice(
                        index=0,
                        delta={},
                        finish_reason="stop"
                    )]
                )
                yield f"data: {end_chunk.model_dump_json()}\n\n"
                yield "data: [DONE]\n\n"
                break
                
            elif event.event == 'error':
                # 错误情况下的结束chunk
                error_chunk = ChatCompletionStreamResponse(
                    id=f"chatcmpl-{self.conv_id}",
                    object="chat.completion.chunk", 
                    created=self.created,
                    model=self.model,
                    choices=[StreamChoice(
                        index=0,
                        delta={"content": "\n[内容由于不合规被停止生成，我们换个话题吧]"},
                        finish_reason="stop"
                    )]
                )
                yield f"data: {error_chunk.model_dump_json()}\n\n"
                yield "data: [DONE]\n\n"
                break
                
            elif event.event == 'length':
                # 长度超限的结束chunk
                length_chunk = ChatCompletionStreamResponse(
                    id=f"chatcmpl-{self.conv_id}",
                    object="chat.completion.chunk",
                    created=self.created,
                    model=self.model,
                    choices=[StreamChoice(
                        index=0,
                        delta={},
                        finish_reason="length"
                    )]
                )
                yield f"data: {length_chunk.model_dump_json()}\n\n"
                yield "data: [DONE]\n\n"
                break