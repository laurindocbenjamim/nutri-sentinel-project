import os
import sys
import asyncio
import re
import json
import subprocess

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.shared.database import get_collection, close_client

async def seed_db():
    md_path = "/Users/fetiwaetika/agents-projects/nutri-sentinel-project/SMARTurinalysis-main/backend/tests/create_list_of_ingredients.md"
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    match = re.search(r"```python\n(.*?)\n```", content, re.DOTALL)
    if not match:
        print("Could not find python code block")
        return
    
    code = match.group(1)
    
    # Remove everything after `# FastAPI Setup` since we don't need the API server code
    code = re.sub(r'# FastAPI Setup.*', '', code, flags=re.DOTALL)
    
    # Append code to dump the ingredients to JSON
    code += """
import json
db = IngredientDatabase()
results = db.get_all_ingredients()
print("JSON_START")
print(json.dumps(results))
print("JSON_END")
"""

    # Run this code in a separate process
    process = subprocess.run(["python", "-c", code], capture_output=True, text=True)
    if process.returncode != 0:
        print("Error running extraction code:")
        print(process.stderr)
        return
        
    out = process.stdout
    if "JSON_START" not in out:
        print("Failed to find JSON output")
        print(out)
        return
        
    json_str = out.split("JSON_START")[1].split("JSON_END")[0].strip()
    results = json.loads(json_str)
    
    ingredients = []
    
    # results format: tuple(ID_Alimento, Nome, Refeicao_Tipo, Calorias_100g, Is_Gluten_Free, Is_Diabetic_Sal)
    for row in results:
        ingredients.append({
            'ID_Alimento': row[0],
            'Nome': row[1],
            'Refeicao_Tipo': row[2],
            'Calorias_100g': row[3],
            'Is_Gluten_Free': bool(row[4]),
            'Is_Diabetic_Sal': row[5],
            'Preco_Medio': "3.00€" # Default value needed by our system
        })

    print(f"Extracted {len(ingredients)} ingredients. Seeding to MongoDB...")
    
    col = get_collection("ingredients")
    
    # clear existing
    await col.delete_many({})
    
    # insert
    await col.insert_many(ingredients)
    print("Seed complete.")
    
    close_client()

if __name__ == "__main__":
    asyncio.run(seed_db())
