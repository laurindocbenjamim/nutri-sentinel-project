import os
import sys
import asyncio
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.shared.database import get_collection, close_client

async def seed_db():
    md_path = "/Users/fetiwaetika/agents-projects/nutri-sentinel-project/SMARTurinalysis-main/backend/tests/create_list_of_ingredients.md"
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract the python code block
    match = re.search(r"```python\n(.*?)\n```", content, re.DOTALL)
    if not match:
        print("Could not find python code block")
        return
    
    code = match.group(1)
    
    # We want to execute the code but only to extract the all_categories array
    # Let's extract everything between "breakfast_items = [" and "all_categories ="
    categories_match = re.search(r"(breakfast_items = \[.*? fat_items = \[.*?\])", code, re.DOTALL)
    if not categories_match:
        print("Could not find categories")
        return
        
    cats_code = categories_match.group(1)
    
    # Execute this code in a local dict
    local_env = {}
    exec(cats_code, {}, local_env)
    
    all_categories = [
        local_env.get("breakfast_items", []),
        local_env.get("fruit_items", []),
        local_env.get("dried_fruit_items", []),
        local_env.get("tuber_items", []),
        local_env.get("drink_items", []),
        local_env.get("protein_items", []),
        local_env.get("vegetable_items", []),
        local_env.get("grain_items", []),
        local_env.get("nut_items", []),
        local_env.get("legume_items", []),
        local_env.get("fat_items", [])
    ]
    
    ingredients = []
    current_id = 1
    
    for category in all_categories:
        for nome, calorias, gluten_free, diabetic_sal in category:
            if any(term in str(nome).lower() for term in ['aveia', 'granola', 'iogurte', 'leite', 'panqueca', 'waffle']):
                refeicao = "Pequeno-Almoço / Lanche"
            elif any(term in str(nome).lower() for term in ['frango', 'peru', 'vaca', 'porco', 'salmão', 'atum', 'bacalhau', 'tofu', 'seitan', 'tempeh', 'queijo', 'ovo']):
                refeicao = "Almoço / Jantar"
            elif any(term in str(nome).lower() for term in ['brócolos', 'couve', 'espinafres', 'alface', 'cenoura', 'tomate']):
                refeicao = "Almoço / Jantar / Lanche"
            elif any(term in str(nome).lower() for term in ['arroz', 'massa', 'batata', 'quinoa', 'milho']):
                refeicao = "Almoço / Jantar"
            elif any(term in str(nome).lower() for term in ['suco', 'chá', 'café', 'água', 'kombucha', 'smoothie']):
                refeicao = "Bebida / Lanche"
            elif any(term in str(nome).lower() for term in ['fruta', 'ameixa', 'banana', 'maçã', 'pêra', 'uva', 'melão']):
                refeicao = "Lanche / Sobremesa"
            elif any(term in str(nome).lower() for term in ['seca', 'passa', 'tâmara', 'coco', 'desidratada']):
                refeicao = "Lanche / Energético"
            elif any(term in str(nome).lower() for term in ['batata', 'mandioca', 'inhame', 'cará', 'taro']):
                refeicao = "Almoço / Jantar (Acompanhamento)"
            else:
                refeicao = "Todas as Refeições"
            
            # Use random average price for now
            ingredients.append({
                'ID_Alimento': f"{current_id:03d}",
                'Nome': nome,
                'Refeicao_Tipo': refeicao,
                'Calorias_100g': calorias,
                'Is_Gluten_Free': gluten_free,
                'Is_Diabetic_Sal': diabetic_sal,
                'Preco_Medio': "3.00€" # Added a default medium price
            })
            current_id += 1

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
