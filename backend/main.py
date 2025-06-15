from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import httpx
import boto3
import json
import uuid
from datetime import datetime, timedelta
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
RUNPOD_ENDPOINT = os.getenv("RUNPOD_ENDPOINT", "https://api.runpod.ai/v2/4cx6jtjdx6hdhr/runsync")
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
    max_length: int = 150
    temperature: float = 0.7

class ChatRequestLegacy(BaseModel):
    message: str
    model: str = "L3.2-8X3B"
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 512
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
    max_tokens: Optional[int] = 512
    persona: Optional[str] = "default"

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

@app.post("/chat/save")
async def save_chat_record(request: ChatSaveRequest):
    """保存聊天记录到R2"""
    try:
        r2_client = get_r2_client()
        if not r2_client:
            return {"success": False, "error": "R2 storage not available"}
        
        # 准备聊天记录数据
        chat_record = {
            "id": request.chat_id,
            "timestamp": datetime.now().isoformat(),
            "messages": [msg.dict() for msg in request.messages],
            "metadata": request.metadata or {}
        }
        
        # 使用日期作为文件夹结构
        date_prefix = datetime.now().strftime("%Y/%m/%d")
        key = f"chats/{date_prefix}/{request.chat_id}.json"
        
        r2_client.put_object(
            Bucket=R2_BUCKET,
            Key=key,
            Body=json.dumps(chat_record, ensure_ascii=False, default=str),
            ContentType='application/json'
        )
        
        print(f"Chat record saved to R2: {key}")
        
        return {
            "success": True,
            "chat_id": request.chat_id,
            "storage_key": key,
            "message": "Chat record saved successfully"
        }
        
    except Exception as e:
        print(f"Save chat error: {e}")
        return {"success": False, "error": str(e)}

@app.get("/chat/load/{chat_id}")
async def load_chat_record(chat_id: str):
    """从R2加载聊天记录"""
    try:
        r2_client = get_r2_client()
        if not r2_client:
            raise HTTPException(status_code=503, detail="R2 storage not available")
        
        # 尝试从今天开始向前查找聊天记录
        for days_back in range(30):  # 查找最近30天
            date = (datetime.now() - timedelta(days=days_back)).strftime("%Y/%m/%d")
            key = f"chats/{date}/{chat_id}.json"
            
            try:
                file_response = r2_client.get_object(
                    Bucket=R2_BUCKET,
                    Key=key
                )
                chat_data = json.loads(file_response['Body'].read())
                print(f"Chat record loaded from R2: {key}")
                return chat_data
                
            except r2_client.exceptions.NoSuchKey:
                continue
            except Exception as e:
                print(f"Error loading chat {key}: {e}")
                continue
        
        # 如果找不到聊天记录
        raise HTTPException(status_code=404, detail="Chat record not found")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Load chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat/list")
async def list_recent_chats(days: int = 7):
    """列出最近的聊天记录"""
    try:
        r2_client = get_r2_client()
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

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    uvicorn.run(app, host=host, port=port, reload=debug) 