import runpod

def handler(event):
    job_input = event["input"]
    prompt = job_input.get("prompt", "Hello")
    return {"output": f"Echo: {prompt}"}

runpod.serverless.start({"handler": handler}) 