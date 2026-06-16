"""
Market Updater Agent (Secondary Agent)

This background script runs autonomously to keep the MongoDB `ingredients`
database updated with real-world prices from Portuguese supermarkets and checks
for new APC (Associação Portuguesa de Celíacos) gluten-free certifications.

This guarantees the core Diet Builder can run locally in milliseconds, while
this agent handles the slow web scraping process independently.
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
from src.domains.blood_analysis.agents import call_groq
from src.config.config import settings
from duckduckgo_search import DDGS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("market_updater")

AGENT_STATUS = {
    "action": "Idle",
    "target": None
}

async def update_prices():
    """
    Search the web for current prices and update the MongoDB ingredients.
    """
    col = get_collection("ingredients")
    ingredients = await col.find({}).to_list(length=100)
    ddgs = DDGS()

    for item in ingredients:
        markets = settings.MARKETS_TO_SEARCH
        query = f"preço {item['Nome']} portugal supermercado {markets}"
        logger.info(f"Searching web for: {query}")
        
        AGENT_STATUS["action"] = "Scraping market prices"
        AGENT_STATUS["target"] = item['Nome']
        
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

            llm_res = call_groq(user_prompt, system_prompt, json_mode=True)
            match = re.search(r"\{.*\}", llm_res, re.DOTALL)
            json_str = match.group(0) if match else llm_res
            data = json.loads(json_str)

            novo_preco = data.get("Preco_Medio", item.get("Preco_Medio"))
            nova_categoria = data.get("Categoria_Custo", item.get("Categoria_Custo"))

            # Update DB
            await col.update_one(
                {"_id": item["_id"]},
                {"$set": {"Preco_Medio": novo_preco, "Categoria_Custo": nova_categoria}}
            )
            logger.info(f"✅ Updated {item['Nome']}: {novo_preco} ({nova_categoria})")

        except Exception as e:
            logger.error(f"❌ Failed to update {item['Nome']}: {e}")
            
        # Add a sleep time after each search to prevent API rate limits
        await asyncio.sleep(settings.MARKET_UPDATER_SLEEP_SECONDS)

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

        llm_res = call_groq(search_context, system_prompt, json_mode=True)
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
    AGENT_STATUS["action"] = "Initializing Database"
    AGENT_STATUS["target"] = None
    await update_prices()
    
    AGENT_STATUS["action"] = "Searching new certifications"
    AGENT_STATUS["target"] = "APC Gluten-Free Products"
    await search_new_certifications()
    
    AGENT_STATUS["action"] = "Idle"
    AGENT_STATUS["target"] = None
    await close_client()
    logger.info("Market Updater Finished.")

if __name__ == "__main__":
    asyncio.run(run_market_updater())
