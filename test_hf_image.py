import os, sys, requests
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

token = os.getenv('HF_ACCESS_TOKEN')
url = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"

print(f"Token: {token[:20]}...")
print(f"Model: FLUX.1-schnell (free, no license required)")
print("Sending request (should be fast, 4 steps)...")

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
payload = {
    "inputs": "professional news photography, government building, editorial style, 4K",
    "parameters": {"width": 512, "height": 512, "num_inference_steps": 4},
    "options": {"wait_for_model": True, "use_cache": False}
}

r = requests.post(url, json=payload, headers=headers, timeout=120)
print(f"\nHTTP Status: {r.status_code}")
print(f"Content-Type: {r.headers.get('Content-Type')}")
print(f"Content-Length: {len(r.content)} bytes")

if r.status_code == 200 and len(r.content) > 1000:
    with open("test_flux_output.png", "wb") as f:
        f.write(r.content)
    print("\nSUCCESS - image saved as test_flux_output.png")
else:
    print(f"\nFAILED: {r.text[:400]}")
