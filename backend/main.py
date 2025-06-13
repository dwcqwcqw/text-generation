from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import httpx
import boto3
import json
import uuid
from datetime import datetime
import os
from dotenv import load_dotenv

# 尝试加载.env文件，如果文件不存在也不会报错
load_dotenv("config.env", override=True)
load_dotenv(".env", override=False)

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
RUNPOD_ENDPOINT = os.getenv("RUNPOD_ENDPOINT", "https://api.runpod.ai/v2/llama-text-gen/runsync")
CLOUDFLARE_ACCESS_KEY = os.getenv("CLOUDFLARE_ACCESS_KEY")
CLOUDFLARE_SECRET_KEY = os.getenv("CLOUDFLARE_SECRET_KEY")
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "https://c7c141ce43d175e60601edc46d904553.r2.cloudflarestorage.com")
R2_BUCKET = os.getenv("R2_BUCKET", "text-generation")

# Pydantic模型
class Message(BaseModel):
    id: str
    content: str
    role: str  # 'user' or 'assistant'
    timestamp: datetime
    model: Optional[str] = None

class ChatRequest(BaseModel):
    prompt: str
    model: str = "gpt2"
    max_length: int = 150
    temperature: float = 0.7

class ChatRequestLegacy(BaseModel):
    message: str
    model: str = "L3.2-8X3B"
    history: List[Message] = []
    max_tokens: int = 1000
    temperature: float = 0.7

class ChatResponse(BaseModel):
    response: str
    model: str
    timestamp: datetime

class SimpleResponse(BaseModel):
    output: str
    generated_text: str

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
    return {"status": "healthy", "timestamp": datetime.now()}

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
        
        # 尝试调用RunPod API
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                runpod_payload = {
                    "input": {
                        "prompt": request.prompt,
                        "max_tokens": request.max_length,
                        "temperature": request.temperature,
                        "stop": ["\n", "User:", "Human:"]
                    }
                }
                
                headers = {
                    "Authorization": f"Bearer {RUNPOD_API_KEY}",
                    "Content-Type": "application/json"
                }
                
                response = await client.post(
                    RUNPOD_ENDPOINT,
                    json=runpod_payload,
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("status") == "COMPLETED":
                        ai_response = result.get("output", {}).get("text", "").strip()
                        if ai_response:
                            return {
                                "output": ai_response,
                                "response": ai_response,
                                "generated_text": ai_response,
                                "model": request.model,
                                "timestamp": datetime.now()
                            }
                
                # 如果RunPod失败，使用模拟回复
                print(f"RunPod API failed: {response.status_code}")
                
        except Exception as e:
            print(f"RunPod error: {e}")
        
        # 使用模拟回复作为后备
        ai_response = f"I understand you're asking about: '{request.prompt}'. This is a simulated response from {request.model} model. The system is currently using fallback mode."
        
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
        r2_client = get_r2_client()
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
        r2_client = get_r2_client()
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
            "id": "gpt2",
            "name": "GPT-2",
            "description": "OpenAI GPT-2 text generation model",
            "parameters": "124M"
        },
        {
            "id": "microsoft/DialoGPT-medium",
            "name": "DialoGPT Medium",
            "description": "Microsoft DialoGPT conversation model",
            "parameters": "117M"
        },
        {
            "id": "L3.2-8X3B",
            "name": "Llama 3.2 8X3B MOE",
            "description": "Dark Champion Instruct (18.4B parameters)",
            "parameters": "18.4B"
        },
        {
            "id": "L3.2-8X4B", 
            "name": "Llama 3.2 8X4B MOE V2",
            "description": "Dark Champion Instruct V2 (21B parameters)",
            "parameters": "21B"
        }
    ]
    return {"models": models}

@app.get("/chat/history/{date}")
async def get_chat_history(date: str):
    """获取指定日期的聊天历史"""
    try:
        r2_client = get_r2_client()
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

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    uvicorn.run(app, host=host, port=port, debug=debug) 