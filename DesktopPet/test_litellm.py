import litellm
import json

def test():
    messages = [{"role": "user", "content": "What's the weather in Tokyo? Use the tool."}]
    tools = [{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather",
            "parameters": {
                "type": "object",
                "properties": {"location": {"type": "string"}},
                "required": ["location"]
            }
        }
    }]
    
    # We will mock the stream to just see how litellm behaves? 
    # Actually we don't have api keys for testing. We can just check the syntax.
    print("litellm is available")

test()
