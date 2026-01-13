#!/usr/bin/env python
"""Check if required environment variables are set."""

import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

print("=" * 60)
print("Environment Variables Check")
print("=" * 60)
print()

# Check for .env file
env_file = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_file):
    print(f"✓ .env file found: {env_file}")
else:
    print(f"✗ .env file NOT found: {env_file}")
    print("  Create it from .env.example: cp .env.example .env")
    print()

# Required variables
required = {
    "OPENAI_API_KEY": "Required for LLM-based draft replies"
}

# Optional variables
optional = {
    "LANGCHAIN_TRACING_V2": "Optional: Enable LangSmith tracing",
    "LANGCHAIN_API_KEY": "Optional: LangSmith API key",
    "LANGCHAIN_PROJECT": "Optional: LangSmith project name"
}

print("Required Variables:")
print("-" * 60)
all_ok = True
for var, desc in required.items():
    value = os.getenv(var)
    if value:
        # Mask the key for security
        masked = value[:7] + "..." + value[-4:] if len(value) > 11 else "***"
        print(f"✓ {var}: {masked} ({desc})")
    else:
        print(f"✗ {var}: NOT SET ({desc})")
        all_ok = False

print()
print("Optional Variables:")
print("-" * 60)
for var, desc in optional.items():
    value = os.getenv(var)
    if value:
        print(f"✓ {var}: {value} ({desc})")
    else:
        print(f"○ {var}: Not set ({desc})")

print()
print("=" * 60)
if all_ok:
    print("✓ All required environment variables are set!")
    print("  You can now run: uvicorn app.main:app --reload")
else:
    print("✗ Missing required environment variables!")
    print("  Please set them in your .env file")
print("=" * 60)
