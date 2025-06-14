#!/usr/bin/env python3
"""
RunPod Handler with Real AI - Llama 3.2 MOE
支持真正的AI对话，不再是echo模式
"""

import runpod
import os
import logging
import time
import threading
import subprocess
import json
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for model management
model = None
tokenizer = None
model_type = None
model_path = None

# GPU monitoring thread
gpu_monitor_active = False

def check_environment():
    """Check CUDA environment variables"""
    cuda_vars = {
        'CUDA_VISIBLE_DEVICES': os.environ.get('CUDA_VISIBLE_DEVICES', 'Not set'),
        'LLAMA_CUBLAS': os.environ.get('LLAMA_CUBLAS', 'Not set'),
        'CMAKE_ARGS': os.environ.get('CMAKE_ARGS', 'Not set'),
    }
    
    for var, value in cuda_vars.items():
        logger.info(f"Environment {var}: {value}")

def check_gpu():
    """Check GPU availability and CUDA support"""
    try:
        # Check environment first
        check_environment()
        # Check nvidia-smi first
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                gpu_info = result.stdout.strip().split('\n')[0].split(', ')
                gpu_name = gpu_info[0].strip()
                gpu_memory = float(gpu_info[1].split()[0]) / 1024  # Convert MB to GB
                logger.info(f"nvidia-smi detected GPU: {gpu_name}, Memory: {gpu_memory:.1f}GB")
            else:
                logger.warning("nvidia-smi command failed")
        except Exception as e:
            logger.warning(f"nvidia-smi check failed: {e}")
        
        # Check PyTorch CUDA support
        import torch
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            gpu_name = torch.cuda.get_device_name(0) if gpu_count > 0 else "Unknown"
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3 if gpu_count > 0 else 0
            logger.info(f"PyTorch CUDA Available: {gpu_count} GPU(s), Name: {gpu_name}, Memory: {gpu_memory:.1f}GB")
            
            # Test GPU allocation
            try:
                test_tensor = torch.cuda.FloatTensor(1)
                logger.info("GPU allocation test successful")
                del test_tensor
                torch.cuda.empty_cache()
            except Exception as e:
                logger.warning(f"GPU allocation test failed: {e}")
            
            return True, gpu_count, gpu_name
        else:
            logger.warning("PyTorch CUDA not available, will use CPU")
            return False, 0, "None"
    except Exception as e:
        logger.error(f"Error checking GPU: {e}")
        return False, 0, "Error"

def start_gpu_monitoring():
    """Start GPU monitoring in background"""
    global gpu_monitor_active
    gpu_monitor_active = True
    
    def monitor_gpu():
        while gpu_monitor_active:
            try:
                result = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu', '--format=csv,noheader,nounits'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    logger.info(f"GPU Status: {result.stdout.strip()}")
                else:
                    logger.warning("nvidia-smi command failed")
            except Exception as e:
                logger.error(f"GPU monitoring error: {e}")
            time.sleep(30)
    
    monitor_thread = threading.Thread(target=monitor_gpu, daemon=True)
    monitor_thread.start()
    logger.info("GPU monitoring started")

def discover_models():
    """Discover available models in the volume"""
    model_paths = [
        "/runpod-volume/text_models/L3.2-8X4B.gguf",
        "/runpod-volume/text_models/L3.2-8X3B.gguf"
    ]
    
    available_models = []
    for path in model_paths:
        if os.path.exists(path):
            size = os.path.getsize(path) / (1024**3)  # Size in GB
            available_models.append((path, size))
            logger.info(f"Found model: {path} ({size:.1f}GB)")
        else:
            logger.warning(f"Model not found: {path}")
    
    return available_models

def load_gguf_model(model_path: str, use_gpu: bool = True):
    """Load GGUF model using llama-cpp-python with GPU support"""
    try:
        from llama_cpp import Llama
        import llama_cpp
        
        logger.info(f"llama-cpp-python version: {llama_cpp.__version__}")
        logger.info(f"Loading GGUF model from {model_path}")
        
        # Start with CPU-only to avoid crashes
        logger.info("Starting with CPU-only loading to ensure stability...")
        
        model = Llama(
            model_path=model_path,
            n_ctx=512,  # Very small context
            n_batch=32,  # Very small batch
            n_gpu_layers=0,  # CPU only for now
            verbose=False,
            n_threads=1,
            use_mmap=True,
            use_mlock=False,
        )
        
        logger.info("GGUF model loaded successfully on CPU")
        return model, "gguf"
        
    except Exception as e:
        logger.error(f"Model loading failed: {e}")
        return None, None

def load_transformers_model(model_path: str, use_gpu: bool = True):
    """Load model using transformers library with GPU support"""
    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM
        
        device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        logger.info(f"Loading Transformers model from {model_path} on {device}")
        
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            device_map="auto" if device == "cuda" else None,
            trust_remote_code=True
        )
        
        if device == "cpu":
            model = model.to(device)
            
        logger.info(f"Transformers model loaded successfully on {device}")
        return model, tokenizer, "transformers"
        
    except Exception as e:
        logger.error(f"Failed to load Transformers model: {e}")
        return None, None, None

def initialize_model():
    """Initialize the best available model with CPU-only for stability"""
    global model, tokenizer, model_type, model_path
    
    logger.info("Starting simplified model initialization...")
    
    # Skip GPU checks for now to avoid crashes
    logger.info("Skipping GPU checks, using CPU-only mode for stability")
    
    # Discover available models
    available_models = discover_models()
    
    if not available_models:
        logger.error("No models found in the specified paths")
        return False
    
    # Try to load the smaller model first (8X4B is smaller than 8X3B)
    for model_path_candidate, size in available_models:
        logger.info(f"Attempting to load model: {model_path_candidate} ({size:.1f}GB)")
        
        # Only try GGUF for now
        if model_path_candidate.endswith('.gguf'):
            try:
                logger.info("Loading GGUF model in CPU-only mode...")
                loaded_model, loaded_type = load_gguf_model(model_path_candidate, False)  # Force CPU
                if loaded_model:
                    model = loaded_model
                    model_type = loaded_type
                    model_path = model_path_candidate
                    logger.info(f"Successfully loaded GGUF model: {model_path}")
                    logger.info("Model initialization completed successfully!")
                    return True
                else:
                    logger.warning("GGUF model loading returned None")
            except Exception as e:
                logger.error(f"Exception during GGUF loading: {e}")
                continue  # Try next model
    
    logger.error("Failed to load any model")
    return False

def get_personality_prompt(personality: str) -> str:
    """Get system prompt for different AI personalities"""
    personalities = {
        "default": "You are a helpful AI assistant. Provide clear, accurate, and helpful responses.",
        "creative": "You are a creative AI assistant specializing in storytelling, creative writing, and imaginative content. Be expressive and innovative in your responses.",
        "professional": "You are a professional AI assistant. Provide formal, structured, and business-appropriate responses with clear reasoning.",
        "casual": "You are a friendly and casual AI assistant. Use a relaxed, conversational tone while being helpful and approachable.",
        "technical": "You are a technical AI assistant specializing in programming, technology, and engineering topics. Provide detailed technical explanations and code examples when relevant.",
        "chinese": "你是一个中文AI助手。请用中文回答问题，提供准确、有用的信息。"
    }
    return personalities.get(personality, personalities["default"])

def format_llama_prompt(prompt: str, personality: str = "default") -> str:
    """Format prompt for Llama 3.2 model"""
    system_prompt = get_personality_prompt(personality)
    
    formatted_prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>

{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""
    return formatted_prompt

def generate_response(prompt: str, personality: str = "default") -> str:
    """Generate response using the loaded model"""
    global model, tokenizer, model_type
    
    if not model:
        return "Error: Model not loaded"
    
    try:
        formatted_prompt = format_llama_prompt(prompt, personality)
        logger.info(f"Generating response with {model_type} model, personality: {personality}")
        
        if model_type == "gguf":
            # Use llama-cpp-python
            response = model(
                formatted_prompt,
                max_tokens=512,
                temperature=0.7,
                top_p=0.9,
                echo=False,
                stop=["<|eot_id|>", "<|end_of_text|>"]
            )
            return response['choices'][0]['text'].strip()
            
        elif model_type == "transformers":
            # Use transformers
            import torch
            
            inputs = tokenizer.encode(formatted_prompt, return_tensors="pt")
            if torch.cuda.is_available():
                inputs = inputs.to("cuda")
            
            with torch.no_grad():
                outputs = model.generate(
                    inputs,
                    max_new_tokens=512,
                    temperature=0.7,
                    top_p=0.9,
                    do_sample=True,
                    pad_token_id=tokenizer.eos_token_id
                )
            
            response = tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True)
            return response.strip()
        
        else:
            return "Error: Unknown model type"
            
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return f"Error generating response: {str(e)}"

def handler(event):
    """Main handler function for RunPod"""
    try:
        # Get input data
        input_data = event.get("input", {})
        prompt = input_data.get("prompt", "Hello")
        personality = input_data.get("personality", "default")
        
        logger.info(f"Processing request - Prompt: {prompt[:50]}..., Personality: {personality}")
        
        # Initialize model if not already loaded
        if not model:
            logger.info("Model not loaded, initializing...")
            if not initialize_model():
                return {"error": "Failed to initialize model"}
        
        # Generate response
        start_time = time.time()
        response = generate_response(prompt, personality)
        end_time = time.time()
        
        logger.info(f"Response generated in {end_time - start_time:.2f} seconds")
        
        return {
            "output": response,
            "model_info": {
                "model_path": model_path,
                "model_type": model_type,
                "processing_time": round(end_time - start_time, 2)
            }
        }
        
    except Exception as e:
        logger.error(f"Handler error: {e}")
        return {"error": f"Handler error: {str(e)}"}

# Initialize model on startup
logger.info("Starting model initialization...")
if not initialize_model():
    logger.error("Failed to initialize model on startup")

# Start the RunPod serverless handler
runpod.serverless.start({"handler": handler})