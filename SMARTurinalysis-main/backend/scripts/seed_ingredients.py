import asyncio
import os
import sys

# Add backend directory to sys.path to allow imports from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.shared.database import get_collection, close_client

INGREDIENTS_DATA = [
    {
        "ID_Alimento": "001",
        "Nome": "Aveia Certificada Sem Glúten",
        "Refeicao_Tipo": "Pequeno-Almoço / Lanche",
        "Calorias_100g": "389 kcal",
        "Is_Gluten_Free": True,
        "Is_Diabetic_Safe": "True (Moderado)",
        "Categoria_Custo": "Médio",
        "Preco_Medio": "2.50€"
    },
    {
        "ID_Alimento": "002",
        "Nome": "Peito de Frango Grelhado",
        "Refeicao_Tipo": "Almoço / Jantar",
        "Calorias_100g": "165 kcal",
        "Is_Gluten_Free": True,
        "Is_Diabetic_Safe": "True",
        "Categoria_Custo": "Médio",
        "Preco_Medio": "6.00€"
    },
    {
        "ID_Alimento": "003",
        "Nome": "Pão de Trigo Comum",
        "Refeicao_Tipo": "Pequeno-Almoço / Lanche",
        "Calorias_100g": "265 kcal",
        "Is_Gluten_Free": False,
        "Is_Diabetic_Safe": "False (Alto IG)",
        "Categoria_Custo": "Baixo",
        "Preco_Medio": "0.90€"
    },
    {
        "ID_Alimento": "004",
        "Nome": "Salmão Fresco",
        "Refeicao_Tipo": "Almoço / Jantar",
        "Calorias_100g": "208 kcal",
        "Is_Gluten_Free": True,
        "Is_Diabetic_Safe": "True",
        "Categoria_Custo": "Premium",
        "Preco_Medio": "15.00€"
    }
]

async def seed_ingredients():
    try:
        col = get_collection("ingredients")
        
        # Clear existing data for idempotency
        await col.delete_many({})
        print("Cleared existing ingredients.")
        
        # Insert new data
        result = await col.insert_many(INGREDIENTS_DATA)
        print(f"Successfully inserted {len(result.inserted_ids)} ingredients.")
        
    except Exception as e:
        print(f"Error seeding ingredients: {e}")
    finally:
        await close_client()

if __name__ == "__main__":
    asyncio.run(seed_ingredients())
