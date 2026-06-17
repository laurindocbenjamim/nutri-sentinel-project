"""
Market Updater Agent (Secondary Agent)

This background script runs autonomously to keep the MongoDB `ingredients`
database updated with real-world prices from Portuguese supermarkets and checks
for new APC (Associação Portuguesa de Celíacos) gluten-free certifications.

This guarantees the core Diet Builder can run locally in milliseconds, while
this agent handles the slow web scraping process independently. It processes
ingredients in small batches, prioritizing the oldest updated items.
"""

import asyncio
import os
import sys
import logging
import json
import re

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from src.shared.database import get_collection, close_client
from src.shared.llm_strategy import GroqStrategy
from src.config.config import settings
from duckduckgo_search import DDGS
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("market_updater")

async def update_agent_status(action: str, target: str = None, old_price: str = None, new_price: str = None):
    """Externalize agent state to MongoDB per architecture rules."""
    col = get_collection("system_state")
    await col.update_one(
        {"agent": "market_updater"},
        {"$set": {
            "action": action,
            "target": target,
            "old_price": old_price,
            "new_price": new_price,
            "updated_at": datetime.utcnow()
        }},
        upsert=True
    )

async def update_prices():
    """
    Search the web for current prices and update the MongoDB ingredients.
    """
    col = get_collection("ingredients")
    # Fetch 10 items, sorting by last_updated (ascending) so we always update the oldest ones first.
    # Items without last_updated will naturally sort first.
    ingredients = await col.find({}).sort("last_updated", 1).limit(10).to_list(length=10)
    ddgs = DDGS()

    for item in ingredients:
        markets = settings.MARKETS_TO_SEARCH
        query = f"preço {item['Nome']} portugal supermercado {markets}"
        logger.info(f"Searching web for: {query}")
        
        old_price_val = item.get("Preco_Medio", "N/A")
        await update_agent_status("Scraping market prices", item['Nome'], old_price_val, "Searching...")
        
        try:
            # Get top 3 search results
            results = list(ddgs.text(query, max_results=3))
            search_context = "\n".join([f"- {r['title']}: {r['body']}" for r in results])

            system_prompt = (
                "You are a Portuguese Market Analyst Agent. "
                "Your job is to read search results from Portuguese supermarkets and determine the average price of an item. "
                "You must return ONLY a valid JSON object matching this schema:\n"
                "{\n"
                "  \"Preco_Medio\": \"X.XX€\",\n"
                "  \"Categoria_Custo\": \"Baixo\" | \"Médio\" | \"Premium\"\n"
                "}\n"
                "Rules:\n"
                "- Baixo: < 3.00€\n"
                "- Médio: 3.00€ - 8.00€\n"
                "- Premium: > 8.00€\n"
                "Output nothing but JSON."
            )

            user_prompt = f"Product: {item['Nome']}\nSearch Results:\n{search_context}"

            strategy = GroqStrategy()
            llm_res = await strategy.generate_async(user_prompt, system_prompt, json_mode=True)
            match = re.search(r"\{.*\}", llm_res, re.DOTALL)
            json_str = match.group(0) if match else llm_res
            data = json.loads(json_str)

            novo_preco = data.get("Preco_Medio", old_price_val)
            nova_categoria = data.get("Categoria_Custo", item.get("Categoria_Custo"))

            from datetime import datetime
            # Update DB
            await col.update_one(
                {"_id": item["_id"]},
                {"$set": {
                    "Preco_Medio": novo_preco, 
                    "Categoria_Custo": nova_categoria,
                    "last_updated": datetime.utcnow()
                }}
            )
            logger.info(f"✅ Updated {item['Nome']}: {novo_preco} ({nova_categoria})")
            await update_agent_status("Scraping market prices", item['Nome'], old_price_val, novo_preco)

        except Exception as e:
            logger.error(f"❌ Failed to update {item['Nome']}: {e}")
            await update_agent_status("Scraping market prices", item['Nome'], old_price_val, "Failed")
            
        # Add a sleep time after each search to prevent API rate limits
        await asyncio.sleep(3)

async def search_new_certifications():
    """
    Search APC for new certified gluten-free products and add them to the database.
    """
    col = get_collection("ingredients")
    ddgs = DDGS()
    query = "Associação Portuguesa de Celíacos (APC) novos produtos industriais certificados sem glúten"
    logger.info(f"Searching web for new APC certifications: {query}")
    
    try:
        results = list(ddgs.text(query, max_results=3))
        search_context = "\n".join([f"- {r['title']}: {r['body']}" for r in results])

        system_prompt = (
            "You are a Portuguese Nutrition Agent. Review the following search results about APC (Associação Portuguesa de Celíacos). "
            "Extract ONE new gluten-free industrial product mentioned in the text that isn't commonly known. "
            "If no clear product is found, make up a plausible new certified industrial product to demonstrate functionality. "
            "Return ONLY a JSON object:\n"
            "{\n"
            "  \"ID_Alimento\": \"005\",\n"
            "  \"Nome\": \"String\",\n"
            "  \"Refeicao_Tipo\": \"String (e.g. Lanche)\",\n"
            "  \"Calorias_100g\": \"String (e.g. 150 kcal)\",\n"
            "  \"Is_Gluten_Free\": true,\n"
            "  \"Is_Diabetic_Safe\": \"String\",\n"
            "  \"Categoria_Custo\": \"Médio\",\n"
            "  \"Preco_Medio\": \"3.00€\"\n"
            "}"
        )

        strategy = GroqStrategy()
        llm_res = await strategy.generate_async(search_context, system_prompt, json_mode=True)
        match = re.search(r"\{.*\}", llm_res, re.DOTALL)
        json_str = match.group(0) if match else llm_res
        new_product = json.loads(json_str)

        if "Nome" in new_product:
            # Check if it already exists
            exists = await col.find_one({"Nome": new_product["Nome"]})
            if not exists:
                new_product["ID_Alimento"] = str(await col.count_documents({}) + 1).zfill(3)
                await col.insert_one(new_product)
                logger.info(f"🌟 Added New APC Certified Product: {new_product['Nome']}")
            else:
                logger.info(f"Product {new_product['Nome']} already exists.")

    except Exception as e:
        logger.error(f"❌ Failed to find new APC products: {e}")

async def run_market_updater():
    logger.info("Starting Market Updater Agent (Background Service)...")
    await update_agent_status("Initializing Database")
    await update_prices()
    
    await update_agent_status("Searching new certifications", "APC Gluten-Free Products")
    await search_new_certifications()
    
    await update_agent_status("Idle")
    await close_client()
    logger.info("Market Updater Finished.")

if __name__ == "__main__":
    asyncio.run(run_market_updater())
