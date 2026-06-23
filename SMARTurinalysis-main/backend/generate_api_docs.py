import json
import sys

# Read the file and strip any non-JSON prefix
with open("openapi.json", "r") as f:
    lines = f.readlines()

json_str = ""
for line in lines:
    if line.startswith("{"):
        json_str += line
    elif json_str: # if we already started reading json
        json_str += line

try:
    schema = json.loads(json_str)
except Exception as e:
    print(f"Error parsing JSON: {e}")
    sys.exit(1)

markdown = "### Complete API Endpoints Reference\n\n"

paths = schema.get("paths", {})
for path, methods in paths.items():
    for method, details in methods.items():
        summary = details.get("summary", "")
        markdown += f"#### `{method.upper()} {path}`\n"
        if summary:
            markdown += f"**Description:** {summary}\n\n"
        
        # Request Body
        req_body = details.get("requestBody", {})
        if req_body:
            content = req_body.get("content", {})
            for content_type, content_details in content.items():
                schema_ref = content_details.get("schema", {})
                if "$ref" in schema_ref:
                    ref_name = schema_ref["$ref"].split("/")[-1]
                    markdown += f"**Payload ({content_type}):**\n"
                    model_schema = schema.get("components", {}).get("schemas", {}).get(ref_name, {})
                    props = model_schema.get("properties", {})
                    markdown += "```json\n{\n"
                    for prop, prop_details in props.items():
                        markdown += f'  "{prop}": "{prop_details.get("type", "any")}",\n'
                    markdown += "}\n```\n\n"
                elif content_type == "multipart/form-data":
                    markdown += f"**Payload ({content_type}):** `multipart/form-data` with required files/fields.\n\n"
                else:
                    markdown += f"**Payload ({content_type}):** (See schema for details)\n\n"
        
        # Responses
        responses = details.get("responses", {})
        markdown += "**Expected Responses:**\n"
        for code, resp in responses.items():
            markdown += f"- **{code}**: {resp.get('description', '')}\n"
            content = resp.get("content", {})
            for content_type, content_details in content.items():
                schema_ref = content_details.get("schema", {})
                if "$ref" in schema_ref:
                    ref_name = schema_ref["$ref"].split("/")[-1]
                    model_schema = schema.get("components", {}).get("schemas", {}).get(ref_name, {})
                    props = model_schema.get("properties", {})
                    if props:
                        markdown += "  ```json\n  {\n"
                        for prop, prop_details in props.items():
                            markdown += f'    "{prop}": "{prop_details.get("type", "any")}",\n'
                        markdown += "  }\n  ```\n"
        markdown += "\n"

with open("api_docs.md", "w") as f:
    f.write(markdown)
