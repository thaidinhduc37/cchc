#!/usr/bin/env python3
"""
PhoGPT API Server - Optimized for Legal RAG
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoConfig
import uvicorn
import os
import warnings
import time
import logging

warnings.filterwarnings("ignore")
os.environ["ATTN_IMPLEMENTATION"] = "eager"

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PhoGPT Legal API")

class GenerateRequest(BaseModel):
    prompt: str
    max_tokens: int = 150  # Increased default
    temperature: float = 0.7

model = None
tokenizer = None

@app.on_event("startup")
async def load_model():
    global model, tokenizer
    logger.info("🔄 Loading PhoGPT-4B-Chat for Legal AI...")
    
    model_path = "./PhoGPT-4B-Chat"
    
    try:
        # Load config
        config = AutoConfig.from_pretrained(model_path, trust_remote_code=True)
        config.attn_config['attn_impl'] = 'torch'
        
        # Load tokenizer
        logger.info("📋 Loading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        
        # Add special tokens if needed
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        # Load model with optimizations
        logger.info("🤖 Loading model (this may take a while)...")
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            config=config,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
            load_in_8bit=True,
            low_cpu_mem_usage=True  # Memory optimization
        )
        
        # Set to eval mode
        model.eval()
        
        logger.info("✅ PhoGPT ready for legal consultations on port 5000!")
        logger.info(f"📊 Model device: {model.device}")
        logger.info(f"📊 Model dtype: {model.dtype}")
        
    except Exception as e:
        logger.error(f"❌ Model loading failed: {e}")
        raise

@app.post("/generate")
async def generate(request: GenerateRequest):
    """Generate legal advice response"""
    start_time = time.time()
    
    try:
        logger.info(f"📝 Generation request - prompt: {len(request.prompt)} chars, max_tokens: {request.max_tokens}")
        
        if model is None or tokenizer is None:
            raise HTTPException(status_code=503, detail="Model not loaded")
        
        # Validate input
        if len(request.prompt.strip()) == 0:
            raise HTTPException(status_code=400, detail="Empty prompt")
        
        if request.max_tokens > 1000:  # Limit max tokens
            request.max_tokens = 1000
            logger.warning(f"⚠️ Max tokens limited to 1000")
        
        # Tokenize input
        logger.debug("🔄 Tokenizing input...")
        inputs = tokenizer(
            request.prompt, 
            return_tensors="pt", 
            truncation=True, 
            max_length=1500  # Limit input length
        ).to(model.device)
        
        input_length = inputs['input_ids'].shape[1]
        logger.debug(f"📊 Input tokens: {input_length}")
        
        # Generate response
        logger.debug("🤖 Generating response...")
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=request.max_tokens,  # Only new tokens
                temperature=request.temperature,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
                repetition_penalty=1.1,  # Reduce repetition
                no_repeat_ngram_size=3,  # Avoid 3-gram repetition
                early_stopping=True  # Stop early if complete
            )
        
        # Decode ONLY the new tokens (not including input)
        new_tokens = outputs[0][input_length:]  # Skip input tokens
        response = tokenizer.decode(new_tokens, skip_special_tokens=True)
        
        # Clean response
        response = response.strip()
        
        generation_time = time.time() - start_time
        logger.info(f"✅ Generation completed in {generation_time:.2f}s - response: {len(response)} chars")
        
        return {
            "success": True, 
            "response": response,
            "generation_time": round(generation_time, 2),
            "input_tokens": input_length,
            "output_tokens": len(new_tokens)
        }
        
    except torch.cuda.OutOfMemoryError:
        logger.error("❌ CUDA out of memory")
        raise HTTPException(status_code=507, detail="GPU memory insufficient")
    except Exception as e:
        generation_time = time.time() - start_time
        logger.error(f"❌ Generation failed after {generation_time:.2f}s: {e}")
        raise HTTPException(status_code=500, detail=f"Generation error: {str(e)}")

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "model_loaded": model is not None,
        "tokenizer_loaded": tokenizer is not None,
        "device": str(model.device) if model else "none",
        "ready": model is not None and tokenizer is not None
    }

@app.get("/stats")
async def stats():
    """Model statistics"""
    if model is None:
        return {"error": "Model not loaded"}
    
    return {
        "model_name": "PhoGPT-4B-Chat",
        "device": str(model.device),
        "dtype": str(model.dtype),
        "memory_usage": torch.cuda.memory_allocated() if torch.cuda.is_available() else 0,
        "vocab_size": tokenizer.vocab_size if tokenizer else 0
    }

if __name__ == "__main__":
    # Run with better settings
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=5000,
        log_level="info",
        access_log=True
    )