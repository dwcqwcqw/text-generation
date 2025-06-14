#!/usr/bin/env python3
import os
import sys
import time

print("=== Model Loading Test ===")
print(f"Python version: {sys.version}")
print(f"Working directory: {os.getcwd()}")

# Test 1: Check if model files exist
model_paths = [
    "/runpod-volume/text_models/L3.2-8X4B.gguf",
    "/runpod-volume/text_models/L3.2-8X3B.gguf"
]

for path in model_paths:
    if os.path.exists(path):
        size = os.path.getsize(path) / (1024**3)
        print(f"✓ Found: {path} ({size:.1f}GB)")
    else:
        print(f"✗ Missing: {path}")

# Test 2: Try to import llama-cpp-python
try:
    import llama_cpp
    print(f"✓ llama-cpp-python version: {llama_cpp.__version__}")
except Exception as e:
    print(f"✗ Failed to import llama-cpp-python: {e}")
    sys.exit(1)

# Test 3: Try to load a tiny test
print("\nTesting minimal model loading...")
try:
    from llama_cpp import Llama
    
    # Create a minimal test
    print("Creating Llama instance with minimal settings...")
    start_time = time.time()
    
    # Use the smaller model with absolute minimal settings
    model = Llama(
        model_path="/runpod-volume/text_models/L3.2-8X4B.gguf",
        n_ctx=32,      # Extremely small
        n_batch=1,     # Single batch
        n_gpu_layers=0,  # CPU only
        verbose=True,    # Enable verbose to see what's happening
        n_threads=1,
        use_mmap=False,  # Disable mmap
        use_mlock=False,
    )
    
    elapsed = time.time() - start_time
    print(f"✓ Model loaded successfully in {elapsed:.1f} seconds!")
    
    # Test generation
    print("\nTesting generation...")
    output = model("Hello", max_tokens=5)
    print(f"✓ Generation successful: {output}")
    
except Exception as e:
    print(f"✗ Model loading failed: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Test Complete ===") 