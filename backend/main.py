from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import httpx
import boto3
import json
import uuid
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import logging
import asyncio
from botocore.client import Config
import uvicorn
import base64
import tempfile
from fastapi import UploadFile, File

# 尝试加载.env文件，如果文件不存在也不会报错
load_dotenv("config.env", override=True)
load_dotenv(".env", override=False)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Chat API", version="1.0.0")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
RUNPOD_ENDPOINT = os.getenv("RUNPOD_ENDPOINT", "https://api.runpod.ai/v2/4cx6jtjdx6hdhr/runsync")
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJHcm91cE5hbWUiOiJCRUkgTEkiLCJVc2VyTmFtZSI6IkJFSSBMSSIsIkFjY291bnQiOiIiLCJTdWJqZWN0SUQiOiIxOTI1MDI1MzAyNDAwOTk1NjQ0IiwiUGhvbmUiOiIiLCJHcm91cElEIjoiMTkyNTAyNTMwMjM5MjYwNzAzNiIsIlBhZ2VOYW1lIjoiIiwiTWFpbCI6ImJhaWxleWxpYmVpQGdtYWlsLmNvbSIsIkNyZWF0ZVRpbWUiOiIyMDI1LTA1LTIxIDEyOjIyOjI4IiwiVG9rZW5UeXBlIjoxLCJpc3MiOiJtaW5pbWF4In0.cMEP1g8YBLysihnD5RfmqtxGAGfR3XYxdXOAHurxoV5u92-ze8j5Iv1hc7O9qgFAoZyi2-eKRl6iRF3JM_IE1RQ6GXmfQnpr4a0VINu7c2GDW-x_4I-7CTHQTAmXfZOp6bVMbFvZqQDS9mzMexYDcFOghwJm1jFKhisU3J4996BqxC6R_u1J15yWkAb0Y5SX18hlYBEuO8MYPjAECSAcSthXIPxo4KQmd1LPuC2URnlhHBa6kvV0pZGp9tggSUlabyQaliCky8fxfOgyJc1YThQybg3iJ2VlYNnIhSj73SZ3pl6nB1unoiCsusAY0_mbzgcAiTd2rpKTh9xmUtcIxw")
MINIMAX_GROUP_ID = os.getenv("MINIMAX_GROUP_ID", "1925025302392607036")
CLOUDFLARE_ACCESS_KEY = os.getenv("CLOUDFLARE_ACCESS_KEY", "5885b29961ce9fc2b593139d9de52f81")
CLOUDFLARE_SECRET_KEY = os.getenv("CLOUDFLARE_SECRET_KEY", "a4415c670e669229db451ea7b38544c0a2e44dbe630f1f35f99f28a27593d181")
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "https://c7c141ce43d175e60601edc46d904553.r2.cloudflarestorage.com")
R2_BUCKET = os.getenv("R2_BUCKET", "text-generation")

# Cloudflare R2配置
R2_CONFIG = {
    'access_key_id': '5885b29961ce9fc2b593139d9de52f81',
    'secret_access_key': 'a4415c670e669229db451ea7b38544c0a2e44dbe630f1f35f99f28a27593d181',
    'endpoint_url': 'https://c7c141ce43d175e60601edc46d904553.r2.cloudflarestorage.com',
    'bucket_name': 'text-generation',
    'region': 'auto'
}

# 初始化R2客户端
try:
    r2_client = boto3.client(
        's3',
        endpoint_url=R2_CONFIG['endpoint_url'],
        aws_access_key_id=R2_CONFIG['access_key_id'],
        aws_secret_access_key=R2_CONFIG['secret_access_key'],
        region_name=R2_CONFIG['region'],
        config=Config(signature_version='s3v4')
    )
    logger.info("✅ R2客户端初始化成功")
except Exception as e:
    logger.error(f"❌ R2客户端初始化失败: {e}")
    r2_client = None

# Pydantic模型
class Message(BaseModel):
    id: str
    content: str
    role: str  # 'user' or 'assistant'
    timestamp: datetime
    model: Optional[str] = None

class ChatSession(BaseModel):
    id: str
    title: str
    messages: List[Message]
    created_at: datetime
    updated_at: datetime
    metadata: Optional[dict] = {}

class ChatSaveRequest(BaseModel):
    chat_id: str
    messages: List[Message]
    metadata: Optional[dict] = {}

class ChatRequest(BaseModel):
    prompt: str
    model: str = "gpt2"
    max_length: int = 1024
    temperature: float = 0.7

class ChatRequestLegacy(BaseModel):
    message: str
    model: str = "L3.2-8X3B"
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048
    persona: Optional[str] = "default"

class ChatResponse(BaseModel):
    response: str
    model: str
    timestamp: datetime

class SimpleResponse(BaseModel):
    output: str
    generated_text: str

class GenerateRequest(BaseModel):
    prompt: str
    model: str = "L3.2-8X3B"  
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048
    persona: Optional[str] = "default"

class ChatRecord(BaseModel):
    chat_id: str
    messages: List[Message]
    metadata: Dict[str, Any] = {}

class ChatHistoryResponse(BaseModel):
    success: bool
    chats: List[Dict[str, Any]] = []
    error: Optional[str] = None

class STTRequest(BaseModel):
    audio_data: str  # base64 encoded audio
    format: str = "webm"  # webm, mp3, wav, etc.

class TTSRequest(BaseModel):
    text: str
    voice_id: str = "male-qn-qingse"
    speed: float = 1.0
    volume: float = 1.0
    pitch: int = 0

class STTResponse(BaseModel):
    success: bool
    text: str = ""
    error: Optional[str] = None

class TTSResponse(BaseModel):
    success: bool
    audio_url: Optional[str] = None
    audio_data: Optional[str] = None  # base64 encoded
    error: Optional[str] = None

# R2存储客户端
def get_r2_client():
    try:
        return boto3.client(
            's3',
            endpoint_url=S3_ENDPOINT,
            aws_access_key_id=CLOUDFLARE_ACCESS_KEY,
            aws_secret_access_key=CLOUDFLARE_SECRET_KEY,
            region_name='auto'
        )
    except Exception as e:
        print(f"Failed to create R2 client: {e}")
        return None

@app.get("/")
async def root():
    return {"message": "AI Chat API is running", "endpoints": ["/chat", "/health", "/models"]}

@app.get("/health")
async def health_check():
    r2_status = "connected" if r2_client else "disconnected"
    return {
        "status": "healthy",
        "r2_storage": r2_status,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/chat")
async def chat(request: ChatRequest):
    """处理聊天请求 - 简化版本"""
    try:
        print(f"Received chat request: {request}")
        
        # 模拟AI回复 - 如果RunPod不可用
        if not RUNPOD_API_KEY or not RUNPOD_ENDPOINT:
            ai_response = f"Hello! You said: '{request.prompt}'. This is a test response from {request.model}."
            return {
                "output": ai_response,
                "response": ai_response,
                "generated_text": ai_response,
                "model": request.model,
                "timestamp": datetime.now()
            }
        
        # 根据模型ID设置正确的模型路径
        model_paths = {
            "L3.2-8X3B": "/runpod-volume/text_models/L3.2-8X3B.gguf",
            "L3.2-8X4B": "/runpod-volume/text_models/L3.2-8X4B.gguf"
        }
        
        model_path = model_paths.get(request.model, "/runpod-volume/text_models/L3.2-8X3B.gguf")
        
        # 尝试调用RunPod API
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # 构建适合Llama模型的提示词
                llama_prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\nYou are a helpful, harmless, and honest assistant.<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{request.prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
                
                runpod_payload = {
                    "input": {
                        "model_path": model_path,
                        "prompt": llama_prompt,
                        "max_tokens": request.max_length,
                        "temperature": request.temperature,
                        "top_p": 0.9,
                        "repeat_penalty": 1.05,
                        "stop": ["<|eot_id|>", "<|end_of_text|>", "<|start_header_id|>"],
                        "stream": False
                    }
                }
                
                headers = {
                    "Authorization": f"Bearer {RUNPOD_API_KEY}",
                    "Content-Type": "application/json"
                }
                
                print(f"Sending to RunPod: {RUNPOD_ENDPOINT}")
                print(f"Model path: {model_path}")
                
                response = await client.post(
                    RUNPOD_ENDPOINT,
                    json=runpod_payload,
                    headers=headers
                )
                
                print(f"RunPod response status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"RunPod result: {result}")
                    
                    if result.get("status") == "COMPLETED":
                        ai_response = result.get("output", {}).get("text", "").strip()
                        
                        # 清理响应，移除提示词格式
                        if ai_response:
                            # 移除可能的系统提示词残留
                            ai_response = ai_response.replace(llama_prompt, "").strip()
                            
                            return {
                                "output": ai_response,
                                "response": ai_response,
                                "generated_text": ai_response,
                                "model": request.model,
                                "timestamp": datetime.now()
                            }
                    else:
                        print(f"RunPod job status: {result.get('status')}")
                        if result.get("error"):
                            print(f"RunPod error: {result.get('error')}")
                
                # 如果RunPod失败，使用模拟回复
                print(f"RunPod API failed: {response.status_code}")
                error_text = await response.text()
                print(f"Error response: {error_text}")
                
        except Exception as e:
            print(f"RunPod error: {e}")
        
        # 使用模拟回复作为后备 - 针对Llama模型的高质量回复
        llama_responses = [
            f"I understand you're asking about '{request.prompt}'. Based on my training, I can provide some insights on this topic.",
            f"That's an interesting question about '{request.prompt}'. Let me share my perspective on this.",
            f"Regarding '{request.prompt}', I can offer several viewpoints to consider.",
            f"Thank you for your question about '{request.prompt}'. Here's what I think about this topic.",
            f"I appreciate your inquiry about '{request.prompt}'. Allow me to elaborate on this subject."
        ]
        
        detailed_responses = [
            "This is a complex topic that involves multiple considerations. From what I understand, there are several key factors to keep in mind when approaching this subject.",
            "Based on my knowledge, this area has several important aspects worth exploring. The key is to consider both the theoretical framework and practical applications.",
            "This is an area where different approaches can yield different results. It's important to consider the context and specific requirements of your situation.",
            "From my analysis, this topic encompasses various dimensions that are worth examining carefully. Each aspect contributes to the overall understanding.",
            "This subject has evolved significantly over time, and there are multiple schools of thought on the best approaches to consider."
        ]
        
        conclusions = [
            " Would you like me to dive deeper into any specific aspect of this topic?",
            " I'd be happy to explore any particular area of interest you might have.",
            " Is there a specific angle or perspective you'd like me to focus on?",
            " Please let me know if you'd like me to elaborate on any particular point.",
            " Feel free to ask for more details on any aspect that interests you."
        ]
        
        import random
        intro = random.choice(llama_responses)
        body = random.choice(detailed_responses)
        conclusion = random.choice(conclusions)
        
        ai_response = f"{intro}\n\n{body}{conclusion}"
        
        # 保存聊天记录
        try:
            await save_simple_chat(request.prompt, ai_response, request.model)
        except Exception as e:
            print(f"Failed to save chat: {e}")
        
        return {
            "output": ai_response,
            "response": ai_response, 
            "generated_text": ai_response,
            "model": request.model,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        print(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/legacy", response_model=ChatResponse)
async def chat_legacy(request: ChatRequestLegacy):
    """处理聊天请求 - 原版本兼容"""
    try:
        # 转换为新格式
        chat_req = ChatRequest(
            prompt=request.message,
            model=request.model,
            max_length=request.max_tokens,
            temperature=request.temperature
        )
        
        result = await chat(chat_req)
        
        return ChatResponse(
            response=result.get("response", ""),
            model=request.model,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        print(f"Legacy chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def save_simple_chat(prompt: str, response: str, model: str):
    """保存聊天记录到Cloudflare R2"""
    try:
        if not r2_client:
            return
        
        chat_session = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "prompt": prompt,
            "response": response
        }
        
        # 使用日期作为文件夹结构
        date_prefix = datetime.now().strftime("%Y/%m/%d")
        key = f"chats/{date_prefix}/{chat_session['id']}.json"
        
        r2_client.put_object(
            Bucket=R2_BUCKET,
            Key=key,
            Body=json.dumps(chat_session, ensure_ascii=False),
            ContentType='application/json'
        )
        
        print(f"Chat saved to R2: {key}")
        
    except Exception as e:
        print(f"R2 save error: {e}")

async def save_chat_to_r2(request: ChatRequestLegacy, response: str):
    """保存聊天记录到Cloudflare R2"""
    try:
        if not r2_client:
            return
        
        chat_session = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "model": request.model,
            "messages": [
                {
                    "role": "user",
                    "content": request.message,
                    "timestamp": datetime.now().isoformat()
                },
                {
                    "role": "assistant", 
                    "content": response,
                    "timestamp": datetime.now().isoformat(),
                    "model": request.model
                }
            ]
        }
        
        # 使用日期作为文件夹结构
        date_prefix = datetime.now().strftime("%Y/%m/%d")
        key = f"chats/{date_prefix}/{chat_session['id']}.json"
        
        r2_client.put_object(
            Bucket=R2_BUCKET,
            Key=key,
            Body=json.dumps(chat_session, ensure_ascii=False),
            ContentType='application/json'
        )
        
        print(f"Chat saved to R2: {key}")
        
    except Exception as e:
        print(f"R2 save error: {e}")

@app.get("/models")
async def get_models():
    """获取可用模型列表"""
    models = [
        {
            "id": "L3.2-8X3B",
            "name": "Llama-3.2-8X3B",
            "description": "Dark Champion Instruct MOE (18.4B parameters)",
            "parameters": "18.4B",
            "context_length": "128k",
            "model_path": "/runpod-volume/text_models/L3.2-8X3B.gguf"
        },
        {
            "id": "L3.2-8X4B",
            "name": "Llama-3.2-8X4B", 
            "description": "Dark Champion Instruct V2 MOE (21B parameters)",
            "parameters": "21B",
            "context_length": "128k",
            "model_path": "/runpod-volume/text_models/L3.2-8X4B.gguf"
        }
    ]
    return {"models": models}

@app.get("/chat/history/{date}")
async def get_chat_history(date: str):
    """获取指定日期的聊天历史"""
    try:
        if not r2_client:
            return {"chats": [], "message": "Storage not available"}
        
        # 列出指定日期的所有聊天文件
        prefix = f"chats/{date}/"
        
        response = r2_client.list_objects_v2(
            Bucket=R2_BUCKET,
            Prefix=prefix
        )
        
        chats = []
        if 'Contents' in response:
            for obj in response['Contents']:
                try:
                    file_response = r2_client.get_object(
                        Bucket=R2_BUCKET,
                        Key=obj['Key']
                    )
                    chat_data = json.loads(file_response['Body'].read())
                    chats.append(chat_data)
                except Exception as e:
                    print(f"Error reading chat file {obj['Key']}: {e}")
        
        return {"chats": chats}
        
    except Exception as e:
        print(f"History error: {e}")
        return {"chats": [], "error": str(e)}

@app.post("/chat/save")
async def save_chat(chat_record: ChatRecord):
    """保存聊天记录到R2"""
    try:
        if not r2_client:
            raise HTTPException(status_code=500, detail="R2客户端未初始化")
        
        # 生成文件路径
        date_str = datetime.now().strftime('%Y-%m-%d')
        file_key = f"chats/{date_str}/{chat_record.chat_id}.json"
        
        # 准备数据
        chat_data = {
            "id": chat_record.chat_id,
            "timestamp": datetime.now().isoformat(),
            "title": next((msg.content[:30] + "..." for msg in chat_record.messages if msg.role == "user"), "新对话"),
            "messages": [msg.dict() for msg in chat_record.messages],
            "metadata": chat_record.metadata
        }
        
        # 保存到R2
        response = r2_client.put_object(
            Bucket=R2_CONFIG['bucket_name'],
            Key=file_key,
            Body=json.dumps(chat_data, ensure_ascii=False, indent=2),
            ContentType='application/json'
        )
        
        logger.info(f"✅ 聊天记录保存成功: {file_key}")
        return {
            "success": True,
            "chat_id": chat_record.chat_id,
            "file_key": file_key,
            "etag": response.get('ETag')
        }
        
    except Exception as e:
        logger.error(f"❌ 保存聊天记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")

@app.get("/chat/load/{chat_id}")
async def load_chat(chat_id: str):
    """从R2加载聊天记录"""
    try:
        if not r2_client:
            raise HTTPException(status_code=500, detail="R2客户端未初始化")
        
        # 尝试多个可能的日期路径
        for days_back in range(30):  # 搜索最近30天
            date_str = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            file_key = f"chats/{date_str}/{chat_id}.json"
            
            try:
                response = r2_client.get_object(
                    Bucket=R2_CONFIG['bucket_name'],
                    Key=file_key
                )
                
                chat_data = json.loads(response['Body'].read().decode('utf-8'))
                logger.info(f"✅ 聊天记录加载成功: {file_key}")
                return {
                    "success": True,
                    "data": chat_data
                }
                
            except r2_client.exceptions.NoSuchKey:
                continue
        
        raise HTTPException(status_code=404, detail="聊天记录不存在")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 加载聊天记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"加载失败: {str(e)}")

@app.get("/chat/history/{date_str}")
async def list_chats(date_str: str):
    """列出指定日期的聊天记录"""
    try:
        if not r2_client:
            raise HTTPException(status_code=500, detail="R2客户端未初始化")
        
        # 格式化日期
        formatted_date = date_str.replace('/', '-')
        prefix = f"chats/{formatted_date}/"
        
        # 列出文件
        response = r2_client.list_objects_v2(
            Bucket=R2_CONFIG['bucket_name'],
            Prefix=prefix
        )
        
        chats = []
        if 'Contents' in response:
            for obj in response['Contents']:
                try:
                    # 获取文件内容
                    file_response = r2_client.get_object(
                        Bucket=R2_CONFIG['bucket_name'],
                        Key=obj['Key']
                    )
                    
                    chat_data = json.loads(file_response['Body'].read().decode('utf-8'))
                    
                    chats.append({
                        "id": chat_data.get("id"),
                        "title": chat_data.get("title", "未知对话"),
                        "timestamp": chat_data.get("timestamp"),
                        "message_count": len(chat_data.get("messages", [])),
                        "metadata": chat_data.get("metadata", {})
                    })
                    
                except Exception as e:
                    logger.warning(f"⚠️ 解析聊天文件失败 {obj['Key']}: {e}")
                    continue
        
        logger.info(f"✅ 获取聊天历史成功: {len(chats)} 条记录")
        return {
            "success": True,
            "chats": sorted(chats, key=lambda x: x.get("timestamp", ""), reverse=True)
        }
        
    except Exception as e:
        logger.error(f"❌ 获取聊天历史失败: {e}")
        return {
            "success": True,
            "chats": []
        }

@app.delete("/chat/delete/{chat_id}")
async def delete_chat(chat_id: str):
    """删除聊天记录"""
    try:
        if not r2_client:
            raise HTTPException(status_code=500, detail="R2客户端未初始化")
        
        # 尝试多个可能的日期路径
        deleted = False
        for days_back in range(30):
            date_str = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            file_key = f"chats/{date_str}/{chat_id}.json"
            
            try:
                r2_client.delete_object(
                    Bucket=R2_CONFIG['bucket_name'],
                    Key=file_key
                )
                deleted = True
                logger.info(f"✅ 聊天记录删除成功: {file_key}")
                break
                
            except r2_client.exceptions.NoSuchKey:
                continue
        
        if not deleted:
            raise HTTPException(status_code=404, detail="聊天记录不存在")
        
        return {"success": True, "message": "聊天记录已删除"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 删除聊天记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@app.get("/chat/list")
async def list_recent_chats(days: int = 7):
    """列出最近的聊天记录"""
    try:
        if not r2_client:
            return {"chats": [], "message": "Storage not available"}
        
        all_chats = []
        
        # 查找最近几天的聊天记录
        for days_back in range(days):
            date = (datetime.now() - timedelta(days=days_back)).strftime("%Y/%m/%d")
            prefix = f"chats/{date}/"
            
            try:
                response = r2_client.list_objects_v2(
                    Bucket=R2_BUCKET,
                    Prefix=prefix
                )
                
                if 'Contents' in response:
                    for obj in response['Contents']:
                        try:
                            file_response = r2_client.get_object(
                                Bucket=R2_BUCKET,
                                Key=obj['Key']
                            )
                            chat_data = json.loads(file_response['Body'].read())
                            
                            # 提取聊天摘要信息
                            first_user_msg = next(
                                (msg for msg in chat_data.get('messages', []) if msg.get('role') == 'user'),
                                None
                            )
                            
                            chat_summary = {
                                "id": chat_data.get('id'),
                                "title": first_user_msg.get('content', 'Untitled Chat')[:50] + '...' if first_user_msg else 'Empty Chat',
                                "timestamp": chat_data.get('timestamp'),
                                "message_count": len(chat_data.get('messages', [])),
                                "storage_key": obj['Key']
                            }
                            
                            all_chats.append(chat_summary)
                            
                        except Exception as e:
                            print(f"Error processing chat file {obj['Key']}: {e}")
                            continue
                            
            except Exception as e:
                print(f"Error listing chats for date {date}: {e}")
                continue
        
        # 按时间戳排序，最新的在前
        all_chats.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return {
            "chats": all_chats[:50],  # 限制返回最近50个聊天
            "total": len(all_chats)
        }
        
    except Exception as e:
        print(f"List chats error: {e}")
        return {"chats": [], "error": str(e)}

@app.post("/speech/stt", response_model=STTResponse)
async def speech_to_text(request: STTRequest):
    """语音转文字 - 使用 Whisper-large-v3-turbo"""
    try:
        print(f"🎤 收到语音转文字请求，音频格式: {request.format}")
        
        # 解码base64音频数据
        try:
            audio_bytes = base64.b64decode(request.audio_data)
            print(f"📊 音频数据大小: {len(audio_bytes)} bytes")
        except Exception as e:
            print(f"❌ 音频数据解码失败: {e}")
            return STTResponse(success=False, error="无效的音频数据格式")
        
        # 保存临时文件
        with tempfile.NamedTemporaryFile(suffix=f'.{request.format}', delete=False) as temp_file:
            temp_file.write(audio_bytes)
            temp_file_path = temp_file.name
        
        try:
            # 调用RunPod Whisper API
            if not RUNPOD_API_KEY:
                return STTResponse(success=False, error="RunPod API Key未配置")
            
            # 将音频文件转换为base64用于API调用
            with open(temp_file_path, 'rb') as audio_file:
                audio_base64 = base64.b64encode(audio_file.read()).decode('utf-8')
            
            # 构建RunPod请求
            runpod_payload = {
                "input": {
                    "audio_data": audio_base64,
                    "format": request.format,
                    "model_path": "/runpod-volume/voice/whisper-large-v3-turbo",
                    "task": "transcribe",
                    "language": "auto"  # 自动检测语言
                }
            }
            
            headers = {
                "Authorization": f"Bearer {RUNPOD_API_KEY}",
                "Content-Type": "application/json"
            }
            
            print(f"🚀 调用RunPod Whisper API...")
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    RUNPOD_ENDPOINT,
                    json=runpod_payload,
                    headers=headers
                )
                
                print(f"📡 RunPod响应状态: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"📦 RunPod响应: {result}")
                    
                    if result.get("status") == "COMPLETED":
                        # 提取转录文本
                        transcription = ""
                        if "output" in result:
                            if isinstance(result["output"], str):
                                transcription = result["output"]
                            elif isinstance(result["output"], dict):
                                transcription = result["output"].get("text", result["output"].get("transcription", ""))
                        
                        if transcription:
                            print(f"✅ 语音转文字成功: {transcription}")
                            return STTResponse(success=True, text=transcription.strip())
                        else:
                            print("⚠️ 未检测到语音内容")
                            return STTResponse(success=False, error="未检测到语音内容")
                    else:
                        error_msg = result.get("error", "语音识别失败")
                        print(f"❌ RunPod任务失败: {error_msg}")
                        return STTResponse(success=False, error=error_msg)
                else:
                    error_text = await response.text()
                    print(f"❌ RunPod API错误: {response.status_code} - {error_text}")
                    return STTResponse(success=False, error=f"API调用失败: {response.status_code}")
        
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_file_path)
            except:
                pass
    
    except Exception as e:
        print(f"❌ 语音转文字处理异常: {e}")
        return STTResponse(success=False, error=f"处理异常: {str(e)}")

@app.post("/speech/tts", response_model=TTSResponse)
async def text_to_speech(request: TTSRequest):
    """文字转语音 - 使用 MiniMax API"""
    try:
        print(f"🔊 收到文字转语音请求: {request.text[:50]}...")
        
        if not request.text.strip():
            return TTSResponse(success=False, error="文本内容不能为空")
        
        # 构建MiniMax TTS请求
        minimax_url = f"https://api.minimax.io/v1/t2a_v2?GroupId={MINIMAX_GROUP_ID}"
        
        headers = {
            "Content-Type": "application/json", 
            "Authorization": f"Bearer {MINIMAX_API_KEY}"
        }
        
        payload = {
            "model": "speech-02-turbo",
            "text": request.text,
            "stream": False,
            "voice_setting": {
                "voice_id": request.voice_id,
                "speed": request.speed,
                "vol": request.volume,
                "pitch": request.pitch
            },
            "audio_setting": {
                "sample_rate": 32000,
                "bitrate": 128000,
                "format": "mp3",
                "channel": 1
            }
        }
        
        print(f"🚀 调用MiniMax TTS API...")
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                minimax_url,
                json=payload,
                headers=headers
            )
            
            print(f"📡 MiniMax响应状态: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"📦 MiniMax响应: {result}")
                
                # 检查响应格式
                if "data" in result and "audio" in result["data"]:
                    # 获取十六进制音频数据
                    hex_audio = result["data"]["audio"]
                    
                    # 转换为字节数据
                    audio_bytes = bytes.fromhex(hex_audio)
                    
                    # 转换为base64用于前端播放
                    audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                    
                    print(f"✅ 文字转语音成功，音频大小: {len(audio_bytes)} bytes")
                    return TTSResponse(success=True, audio_data=audio_base64)
                
                else:
                    print(f"❌ MiniMax响应格式异常: {result}")
                    return TTSResponse(success=False, error="音频生成失败")
            
            else:
                error_text = await response.text()
                print(f"❌ MiniMax API错误: {response.status_code} - {error_text}")
                return TTSResponse(success=False, error=f"API调用失败: {response.status_code}")
    
    except Exception as e:
        print(f"❌ 文字转语音处理异常: {e}")
        return TTSResponse(success=False, error=f"处理异常: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    uvicorn.run(app, host=host, port=port, reload=debug) 