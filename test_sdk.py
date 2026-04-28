#!/usr/bin/env python3
"""Test script to verify Claude Agent SDK works."""

import asyncio
import os

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
from dotenv import load_dotenv

load_dotenv()


async def test():

    options = ClaudeAgentOptions(
        system_prompt="You are a helpful assistant.",
        max_turns=3,
        model="glm-5.1",
        allowed_tools=["Bash", "Read"],
    )

    try:
        async with ClaudeSDKClient(options=options) as client:
            print("Client created, sending query...")
            await client.query("Say hello in one word")

            print("Waiting for response...")
            count = 0
            async for message in client.receive_response():
                count += 1
                print(f"Message {count}: {type(message).__name__} - {message}")

            print(f"Total messages: {count}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(test())
