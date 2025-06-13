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

load_dotenv()

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
RUNPOD_ENDPOINT = os.getenv("RUNPOD_ENDPOINT", "https://api.runpod.ai/v2/your-endpoint/runsync")
CLOUDFLARE_ACCESS_KEY = os.getenv("CLOUDFLARE_ACCESS_KEY")
CLOUDFLARE_SECRET_KEY = os.getenv("CLOUDFLARE_SECRET_KEY")
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "https://your-account-id.r2.cloudflarestorage.com")
R2_BUCKET = os.getenv("R2_BUCKET", "text-generation")

# Pydantic模型
class Message(BaseModel):
    id: str
    content: str
    role: str  # 'user' or 'assistant'
    timestamp: datetime
    model: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    model: str = "L3.2-8X3B"
    history: List[Message] = []
    max_tokens: int = 1000
    temperature: float = 0.7

class ChatResponse(BaseModel):
    response: str
    model: str
    timestamp: datetime

# R2存储客户端
def get_r2_client():
    return boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=CLOUDFLARE_ACCESS_KEY,
        aws_secret_access_key=CLOUDFLARE_SECRET_KEY,
        region_name='auto'
    )

@app.get("/")
async def root():
    return {"message": "AI Chat API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now()}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """处理聊天请求"""
    try:
        # 构建聊天上下文
        context = ""
        if request.history:
            for msg in request.history[-10:]:  # 只使用最近10条消息
                role = "User" if msg.role == "user" else "Assistant"
                context += f"{role}: {msg.content}\n"
        
        context += f"User: {request.message}\nAssistant:"
        
        # 准备RunPod请求
        runpod_payload = {
            "input": {
                "prompt": context,
                "model_path": f"/runpod-volume/text_models/{request.model}.gguf",
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
                "stop": ["User:", "Human:", "\n\n"]
            }
        }
        
        # 发送请求到RunPod
        async with httpx.AsyncClient(timeout=60.0) as client:
            headers = {
                "Authorization": f"Bearer {RUNPOD_API_KEY}",
                "Content-Type": "application/json"
            }
            
            response = await client.post(
                RUNPOD_ENDPOINT,
                json=runpod_payload,
                headers=headers
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail=f"RunPod API error: {response.text}")
            
            result = response.json()
            
            if result.get("status") != "COMPLETED":
                raise HTTPException(status_code=500, detail="Model inference failed")
            
            ai_response = result.get("output", {}).get("text", "").strip()
            
            if not ai_response:
                ai_response = "抱歉，我没有收到有效的响应。请重试。"
        
        # 保存聊天记录到R2
        try:
            await save_chat_to_r2(request, ai_response)
        except Exception as e:
            print(f"Failed to save to R2: {e}")
            # 不因为存储失败而中断聊天
        
        return ChatResponse(
            response=ai_response,
            model=request.model,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        print(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def save_chat_to_r2(request: ChatRequest, response: str):
    """保存聊天记录到Cloudflare R2"""
    try:
        r2_client = get_r2_client()
        
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
        raise

@app.get("/models")
async def get_models():
    """获取可用模型列表"""
    models = [
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
        prefix = f"chats/{date}/"
        
        response = r2_client.list_objects_v2(
            Bucket=R2_BUCKET,
            Prefix=prefix
        )
        
        history = []
        for obj in response.get('Contents', []):
            chat_data = r2_client.get_object(
                Bucket=R2_BUCKET,
                Key=obj['Key']
            )
            content = json.loads(chat_data['Body'].read())
            history.append(content)
        
        return {"history": history}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 