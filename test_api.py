"""
Standalone diagnostic script. Run this directly (not through Streamlit) to
see exactly what the Anthropic API returns, without any JSON parsing in
the way. Helps isolate whether the issue is the API key, the model name,
or something else.
"""

import os
import anthropic

api_key = os.environ.get("ANTHROPIC_API_KEY")
print("Key found in environment:", "yes" if api_key else "NO — this is the problem")
if api_key:
    print("Key starts with:", api_key[:15])
    print("Key length:", len(api_key))

client = anthropic.Anthropic(api_key=api_key)

try:
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=200,
        messages=[{"role": "user", "content": "Say hello in one sentence."}],
    )
    print("\n--- Raw response ---")
    print(response)
    print("\n--- Content blocks ---")
    for block in response.content:
        print("Block type:", block.type)
        if block.type == "text":
            print("Text:", block.text)
except Exception as e:
    print("\n--- ERROR ---")
    print(type(e).__name__, ":", e)
