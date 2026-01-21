import google.genai as genai

# Test the new API structure
json_schema = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "message": {"type": "string"}
    },
    "required": ["title", "message"]
}

# Correct way for google-genai v1.56.0
config = genai.types.GenerateContentConfig(
    response_mime_type="application/json",
    response_schema=json_schema,
)

print("✓ Config created successfully!")
print(f"  Config type: {type(config)}")
print(f"  response_mime_type: {config.response_mime_type}")
print(f"  response_schema: {config.response_schema}")

