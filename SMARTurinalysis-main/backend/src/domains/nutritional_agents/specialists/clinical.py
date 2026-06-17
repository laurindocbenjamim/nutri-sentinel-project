"""
Agent 3.D — Clinical Nutrition Agent (Diet Builder).

Consolidates all specialist directives and generates a 7-day personalized
meal plan. Applies budget constraints and caloric density adjustments.
"""

from __future__ import annotations
from decimal import Decimal
from datetime import datetime, timezone

from src.domains.nutritional_agents.models import (
    UserProfile, UrinalysisData, Meal, DailyPlan,
    WeeklyPlanPayload, DietSummary, MacroDistribution,
    FinancialMetrics, AuditorEvaluation, BudgetTier, BudgetStatus, GlycemicLoad, FastingProtocol
)
from src.domains.blood_analysis.agents import call_groq
import json
import logging
import re
import os
from google import genai
from google.genai import types
from src.shared.database import get_collection
from src.config.config import settings
from src.shared.database import get_collection

logger = logging.getLogger("nutri-sentinel")

# Cost weight table for budget gate (used by calculate_recipe_budget)
_PRICE_WEIGHTS: dict[str, int] = {
    "student": {
        "low": ["arroz", "batata-doce", "frango", "ovos", "alface", "banana",
                "maçã", "feijão", "atum em lata", "cenoura", "cebola"],
        "medium": ["aveia sem glúten", "quinoa", "azeite", "bebida de amêndoa", "iogurte"],
        "high": ["salmão fresco", "abacate", "nozes", "manteiga de amêndoa", "carne de vaca premium"],
    }
}
_BUDGET_THRESHOLDS = {BudgetTier.STUDENT: 7, BudgetTier.MEDIUM: 14, BudgetTier.PREMIUM: 999}
_WEEKLY_COST_ESTIMATES = {BudgetTier.STUDENT: Decimal("42.00"), BudgetTier.MEDIUM: Decimal("70.00"), BudgetTier.PREMIUM: Decimal("120.00")}

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _build_base_menu(directives: dict, profile: UserProfile) -> dict[str, DailyPlan]:
    """
    Generate a 7-day meal structure using safe, directive-compliant ingredients.
    Uses rotation logic to vary meals across the week.
    """
    gluten_free = directives.get("autoimmune", {}).get("zero_tolerance_gluten", False)
    oat_label = "aveia certificada sem glúten" if gluten_free else "aveia"
    bread_label = "pão sem glúten" if gluten_free else "pão integral"

    # Two rotating daily templates to ensure meal variety across 7 days
    template_a = DailyPlan(
        pequeno_almoco=Meal(
            description=f"Papas de {oat_label} com bebida de amêndoa, banana e sementes de girassol.",
            ingredients=[oat_label, "bebida de amêndoa", "banana", "sementes de girassol"],
            allergens_checked=["glúten", "lactose"],
            glycemic_load=GlycemicLoad.MEDIUM,
        ),
        almoco=Meal(
            description="Peito de frango grelhado com arroz basmati, brócolos e azeite.",
            ingredients=["peito de frango", "arroz basmati", "brócolos", "azeite"],
            allergens_checked=["glúten"],
            glycemic_load=GlycemicLoad.LOW,
        ),
        lanche=Meal(
            description="Iogurte sem lactose com nozes e morangos.",
            ingredients=["iogurte sem lactose", "nozes", "morangos"],
            allergens_checked=["lactose", "frutos de casca rija"],
            glycemic_load=GlycemicLoad.LOW,
        ),
        jantar=Meal(
            description="Posta de salmão assado com batata-doce e salada de pepino.",
            ingredients=["salmão", "batata-doce", "pepino", "alface", "azeite"],
            allergens_checked=["glúten", "peixe"],
            glycemic_load=GlycemicLoad.MEDIUM,
        ),
    )
    template_b = DailyPlan(
        pequeno_almoco=Meal(
            description=f"Ovos mexidos com {bread_label} e sumo de laranja natural.",
            ingredients=["ovos", bread_label, "laranja"],
            allergens_checked=["glúten", "ovos"],
            glycemic_load=GlycemicLoad.LOW,
        ),
        almoco=Meal(
            description="Feijão preto com arroz, couve refogada em azeite e frango desfiado.",
            ingredients=["feijão preto", "arroz", "couve", "azeite", "frango"],
            allergens_checked=["glúten"],
            glycemic_load=GlycemicLoad.MEDIUM,
        ),
        lanche=Meal(
            description="Banana com manteiga de amendoim e bebida de aveia sem glúten.",
            ingredients=["banana", "manteiga de amendoim", oat_label],
            allergens_checked=["glúten", "amendoins"],
            glycemic_load=GlycemicLoad.LOW,
        ),
        jantar=Meal(
            description="Bacalhau assado com batatas e legumes grelhados.",
            ingredients=["bacalhau", "batata", "pimento", "azeite", "alho"],
            allergens_checked=["glúten", "peixe"],
            glycemic_load=GlycemicLoad.LOW,
        ),
    )

    # Alternate templates across week days
    return {day: (template_a if i % 2 == 0 else template_b) for i, day in enumerate(DAYS)}


class ClinicalNutritionAgent:
    """
    Agent 3.D — Clinical Nutrition Agent.
    Assembles the full 7-day meal plan from specialist directives.
    """

    def calculate_recipe_budget(self, ingredients: list[str], tier: BudgetTier) -> str:
        """
        Score ingredients by cost weight and reject premium items for budget users.
        Returns 'APPROVED_BY_BUDGET' or 'REJECTED_BY_BUDGET'.
        """
        score = 0
        low = _PRICE_WEIGHTS["student"]["low"]
        medium = _PRICE_WEIGHTS["student"]["medium"]
        high = _PRICE_WEIGHTS["student"]["high"]

        for ing in ingredients:
            lower = ing.lower()
            if any(h in lower for h in high):
                score += 3
            elif any(m in lower for m in medium):
                score += 2
            else:
                score += 1

        threshold = _BUDGET_THRESHOLDS.get(tier, 14)
        return "APPROVED_BY_BUDGET" if score <= threshold else "REJECTED_BY_BUDGET"

    def adjust_caloric_density(self, goal: str, base_macros: dict) -> dict:
        """
        Apply a caloric surplus for weight-gain goals by increasing
        fat and carbohydrate targets proportionally.
        """
        if goal == "ganhar_peso":
            return {
                "carbohydrates_g": int(base_macros["carbohydrates_g"] * 1.15),
                "proteins_g": int(base_macros["proteins_g"] * 1.10),
                "fats_g": int(base_macros["fats_g"] * 1.15),
                "target_calories_kcal": int(base_macros["target_calories_kcal"] * 1.12),
            }
        return base_macros

    async def structure_weekly_menu(
        self,
        urinalysis_data: UrinalysisData,
        profile: UserProfile,
        directives: dict,
        loop_attempt: int = 1,
        blood_data: list[dict] | None = None,
        notes: str = "",
        fasting_protocol: FastingProtocol = FastingProtocol.NONE,
        language: str = "English"
    ) -> WeeklyPlanPayload:
        """
        Build and return the full WeeklyPlanPayload incorporating all directives.
        """
        # Fetch approved ingredients from DB
        try:
            ingredients_col = get_collection("ingredients")
            db_ingredients = await ingredients_col.find({}).to_list(length=100)
            if db_ingredients:
                ingredients_text = "\n".join([
                    f"- {i.get('Nome')} (For: {i.get('Refeicao_Tipo')}) - {i.get('Calorias_100g')}, "
                    f"Gluten Free: {i.get('Is_Gluten_Free')}, Diabetic Safe: {i.get('Is_Diabetic_Safe')}, "
                    f"Cost Category: {i.get('Categoria_Custo', 'N/A')} (Avg Price: {i.get('Preco_Medio', 'N/A')})"
                    for i in db_ingredients
                ])
            else:
                ingredients_text = "No specific ingredients registered in DB."
        except Exception as e:
            logger.warning(f"Failed to fetch ingredients from DB: {e}")
            ingredients_text = "No specific ingredients registered in DB."
        # Determine macro targets and apply goal-specific caloric adjustments
        from src.domains.nutritional_agents.router_agent import RouterAgent
        base_macros = RouterAgent().calculate_metabolic_goals(profile)
        adjusted = self.adjust_caloric_density(profile.goal, base_macros)

        diet_type = "Isenta de Glúten" if directives.get("autoimmune") else "Equilibrada"
        if profile.goal == "ganhar_peso":
            diet_type = f"Hipercalórica / {diet_type}"

        system_prompt = (
            f"You are an advanced clinical nutritionist AI following international dietary guidelines (e.g., WHO). "
            f"Your task is to generate a personalized 7-day meal plan based on the user's clinical profile, "
            f"blood/urinalysis tests, pathologies, allergies, and specific preferences (notes). "
            f"You MUST return the output strictly as a JSON object following this EXACT structure for the `weekly_plan`:\n"
            "{\n"
            "  'clinical_summary': 'A concise clinical summary (in the requested language) analyzing the patient\\'s blood and urinalysis results, highlighting any concerns before prescribing the diet.',\n"
            "  'notes_explanation': 'A clear explanation (in the requested language) of why certain user notes (e.g. food requests) were included or rejected based on clinical rules/allergies.',\n"
            "  'weekly_plan': {\n"
            "    'monday': {\n"
            "      'explanation': 'A detailed explanation (in the requested language) of why this specific day\\'s meals are good for the patient. Make it unique and comprehensive.',\n"
            "      'pequeno_almoco': { 'description': '...', 'ingredients': ['...'], 'allergens_checked': ['...'], 'glycemic_load': 'Baixa'|'Média'|'Alta' },\n"
            "      'almoco': { ... },\n"
            "      'lanche': { ... },\n"
            "      'jantar': { ... }\n"
            "    },\n"
            "    'tuesday': { ... },\n"
            "    'wednesday': { ... },\n"
            "    'thursday': { ... },\n"
            "    'friday': { ... },\n"
            "    'saturday': { ... },\n"
            "    'sunday': { ... }\n"
            "  }\n"
            "}\n"
            "CRITICAL RULES:\n"
            "1. Output ONLY valid JSON, no markdown, no explanation outside the JSON.\n"
            "2. All JSON keys must be exactly as shown in english (notes_explanation, weekly_plan, monday, pequeno_almoco, etc.).\n"
            f"3. All text VALUES (descriptions, ingredients, notes_explanation, clinical_summary, explanation) MUST be in the requested language: {language}.\n"
            "4. Respect all allergies and pathologies! Ensure meals are safe and nutritionally balanced.\n"
            "5. FASTING: If a fasting protocol is active (e.g. 16/8), adjust the meals (e.g., make 'pequeno_almoco' just 'Water, black coffee/tea', and distribute calories in the remaining meals).\n"
            "6. APPROVED INGREDIENTS: Use the following approved ingredients from our database where possible to avoid hallucinations:\n"
            f"   {ingredients_text}\n"
            "7. NOTES EXPLANATION: If the user requests foods like 'peas' or 'bread' in their notes, and you choose to omit them due to allergies or diet constraints, you MUST explain why in the `notes_explanation` field.\n"
            "8. COMPLETENESS: You MUST generate all 7 days of the week completely. DO NOT skip Saturday or Sunday. Ensure breakfasts and meals are highly varied across the week."
        )

        user_prompt = (
            "Generate a 7-day meal plan for the following user:\n\n"
            f"- Age: {profile.age}\n"
            f"- Sex: {profile.sex}\n"
            f"- Goal: {profile.goal}\n"
            f"- Budget Tier: {profile.budget_tier.value}\n"
            f"- Pathologies: {', '.join(profile.pathologies) if profile.pathologies else 'None'}\n"
            f"- Allergies: {', '.join(profile.allergies) if profile.allergies else 'None'}\n"
            f"- Medications: {', '.join(profile.medications) if profile.medications else 'None'}\n"
            f"- Target Calories: {adjusted['target_calories_kcal']} kcal/day\n"
            f"\nSpecialist Directives: {json.dumps(directives)}\n"
            f"Urinalysis Data: {urinalysis_data.model_dump_json()}\n"
            f"Blood Data: {json.dumps(blood_data) if blood_data else 'None'}\n"
            f"Fasting Protocol: {fasting_protocol.value}\n"
            f"\nUser Dietary Notes / Preferences: {notes if notes else 'None'}\n"
        )

        try:
            # Use the configured LLM_MODEL instead of hardcoding, as more powerful models handle massive JSON schemas better.
            res = call_groq(user_prompt, system_prompt, json_mode=True, model=settings.LLM_MODEL, max_tokens=6000)
            
            # Safely extract JSON using regex to handle potential markdown wrappers like ```json ... ```
            match = re.search(r"\{.*\}", res, re.DOTALL)
            if match:
                res_json_str = match.group(0)
            else:
                res_json_str = res
                
            res_dict = json.loads(res_json_str)
            weekly_plan_dict = res_dict.get("weekly_plan", res_dict) # Fallback if LLM forgets wrapper
            notes_explanation = res_dict.get("notes_explanation", "")
            clinical_summary = res_dict.get("clinical_summary", "")
            
            weekly = {}
            for day in DAYS:
                day_data = weekly_plan_dict.get(day, {})
                weekly[day] = DailyPlan(
                    pequeno_almoco=Meal(**day_data.get("pequeno_almoco", {"description": "Refeição não gerada", "ingredients": [], "allergens_checked": [], "glycemic_load": GlycemicLoad.MEDIUM})),
                    almoco=Meal(**day_data.get("almoco", {"description": "Refeição não gerada", "ingredients": [], "allergens_checked": [], "glycemic_load": GlycemicLoad.MEDIUM})),
                    lanche=Meal(**day_data.get("lanche", {"description": "Refeição não gerada", "ingredients": [], "allergens_checked": [], "glycemic_load": GlycemicLoad.MEDIUM})),
                    jantar=Meal(**day_data.get("jantar", {"description": "Refeição não gerada", "ingredients": [], "allergens_checked": [], "glycemic_load": GlycemicLoad.MEDIUM})),
                    explanation=day_data.get("explanation", "")
                )
        except Exception as e:
            logger.error(f"LLM Diet Generation failed: {e}. Falling back to default templates.")
            weekly = _build_base_menu(directives, profile)
            notes_explanation = f"Erro Técnico (Fallback ativado): A inteligência artificial não conseguiu gerar o plano. Motivo: {str(e)[:150]}"
            clinical_summary = ""

        estimated_cost = _WEEKLY_COST_ESTIMATES.get(profile.budget_tier, Decimal("70.00"))

        return WeeklyPlanPayload(
            metadata={
                "user_id": profile.user_id,
                "loop_attempt": loop_attempt,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            diet_summary=DietSummary(
                diet_type=diet_type,
                target_calories_kcal=adjusted["target_calories_kcal"],
                clinical_summary=clinical_summary,
                macro_distribution=MacroDistribution(
                    carbohydrates_g=adjusted["carbohydrates_g"],
                    proteins_g=adjusted["proteins_g"],
                    fats_g=adjusted["fats_g"],
                ),
                notes_explanation=notes_explanation,
            ),
            financial_metrics=FinancialMetrics(
                user_budget_tier=profile.budget_tier,
                estimated_weekly_cost_eur=estimated_cost,
                budget_status=BudgetStatus.COMPLIANT,
            ),
            weekly_plan=weekly,
            auditor_evaluation=AuditorEvaluation(),
        )

    async def generate_shopping_list_and_prices(self, plan: WeeklyPlanPayload, language: str = "English") -> WeeklyPlanPayload:
        """
        Takes an approved WeeklyPlanPayload, extracts unique ingredients,
        and uses Gemini 2.5 Flash to generate a categorized shopping list and price matrix.
        Fallback to local DB if Gemini fails.
        """
        ingredients_col = get_collection("ingredients")
        db_ingredients = await ingredients_col.find({}).to_list(length=200)
        
        # Build local reference for fallback and context
        local_prices = {}
        ref_str = ""
        for i in db_ingredients:
            nome = i.get('Nome')
            preco = i.get('Preco_Medio', 'N/A')
            if nome:
                local_prices[nome.lower()] = preco
                ref_str += f"- {nome} | {preco}\n"

        # Extract meals to pass to LLM
        meals_dump = ""
        for day, dplan in plan.weekly_plan.items():
            for m in [dplan.pequeno_almoco, dplan.almoco, dplan.lanche, dplan.jantar]:
                meals_dump += f"{', '.join(m.ingredients)}\n"

        prompt_sistema = """
        Atuas como o Agente de Pesquisa de Mercado de Portugal. O teu objetivo é enriquecer uma lista de compras com preços reais.
        Deves usar a tua ferramenta de Google Search integrada para extrair os preços dos sites ou folhetos ativos do Continente, Lidl, Mercadona e Celeiro.
        
        REGRAS ESTRITAS:
        1. Procura sempre as versões de marca própria (Marca branca) "Sem Glúten" ou "Isento de Glúten" para utilizadores celíacos.
        2. Se não encontrares o preço exato, faz uma estimativa com base no histórico de mercado de Portugal e no histórico fornecido, e altera o campo 'is_estimated' para true.
        3. O teu output deve ser EXCLUSIVAMENTE um JSON válido. Não adiciones texto explicativo antes ou depois do JSON.
        
        Esquema esperado:
        {
          "shopping_list": [
            { "item_name": "...", "quantity": "...", "category": "Talho, Peixaria e Ovos" | "Mercearia (Secção Sem Glúten)" | "Frutaria e Legumes" }
          ],
          "price_comparison": {
            "items": [
              { "ingredient": "...", "continente_price": "...", "lidl_price": "...", "mercadona_price": "...", "celeiro_price": "..." }
            ],
            "total_continente": "...", "total_lidl": "...", "total_mercadona": "...", "total_celeiro": "...",
            "auditor_note": "..."
          }
        }
        """

        try:
            client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))
            config = types.GenerateContentConfig(
                system_instruction=prompt_sistema,
                temperature=0.2,
                response_mime_type="application/json",
                tools=[{"google_search": {}}]
            )

            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=f"Pesquisa os preços em Portugal para este cabaz: {meals_dump}\n\nPreços de Referência Locais:\n{ref_str}",
                config=config
            )
            
            res_text = response.text
            match = re.search(r"\{.*\}", res_text, re.DOTALL)
            json_str = match.group(0) if match else res_text
            data = json.loads(json_str)
            
            # Validation Rule: Se JSON incompleto ou preco == 0 -> Fallback
            if not data.get("shopping_list") or not data.get("price_comparison"):
                raise ValueError("JSON Incompleto devolvido pelo Gemini.")
            
            # Additional validation: check if prices look like '0' or '0.00'
            for item in data["price_comparison"].get("items", []):
                for p_key in ["continente_price", "lidl_price", "mercadona_price", "celeiro_price"]:
                    val = str(item.get(p_key, "")).replace("€", "").replace(",", ".").strip()
                    try:
                        if float(val) == 0:
                            raise ValueError(f"Preço 0 detectado em {item['ingredient']}")
                    except ValueError:
                        pass # if not a number, skip this check
                        
            # If all is well, apply it
            from src.domains.nutritional_agents.models import ShoppingListItem, PriceComparisonMatrix
            plan.shopping_list = [ShoppingListItem(**item) for item in data["shopping_list"]]
            plan.price_comparison = PriceComparisonMatrix(**data["price_comparison"])
            logger.info("Gemini 2.5 Flash succeeded in generating shopping list with Google Grounding.")

        except Exception as e:
            logger.warning(f"Gemini pricing failed or validation error: {e}. Executing Fallback to Local DB.")
            # Fallback to local static prices
            from src.domains.nutritional_agents.models import ShoppingListItem, PriceComparisonMatrix, PriceComparisonItem, ShoppingCategory
            
            # Simple unique ingredients extraction
            import collections
            ingredients_counter = collections.Counter()
            for day, dplan in plan.weekly_plan.items():
                for m in [dplan.pequeno_almoco, dplan.almoco, dplan.lanche, dplan.jantar]:
                    for ing in m.ingredients:
                        ingredients_counter[ing] += 1
                        
            sl = []
            pc_items = []
            total = 0.0
            
            for ing, count in ingredients_counter.items():
                # Default category logic if we don't know
                cat = ShoppingCategory.GROCERY
                if any(x in ing.lower() for x in ["frango", "peru", "ovo", "atum", "peixe", "pescada", "bife"]):
                    cat = ShoppingCategory.MEAT_FISH
                elif any(x in ing.lower() for x in ["maçã", "banana", "batata", "espinafre", "alface", "brócolo", "courgette", "cenoura", "tomate"]):
                    cat = ShoppingCategory.PRODUCE

                sl.append(ShoppingListItem(item_name=ing, quantity=str(count), category=cat))
                
                # Get price from local DB or default with fuzzy matching
                preco_db = local_prices.get(ing.lower())
                if not preco_db:
                    for db_name, price in local_prices.items():
                        if db_name in ing.lower() or ing.lower() in db_name:
                            preco_db = price
                            break
                if not preco_db:
                    preco_db = "3.00€"
                    
                pc_items.append(PriceComparisonItem(
                    ingredient=ing,
                    continente_price=preco_db,
                    lidl_price=preco_db,
                    mercadona_price=preco_db,
                    celeiro_price=preco_db
                ))
                try:
                    total += float(preco_db.replace("€", "").replace(",", ".").strip()) * count
                except:
                    pass

            plan.shopping_list = sl
            plan.price_comparison = PriceComparisonMatrix(
                items=pc_items,
                total_continente=f"{total:.2f}€",
                total_lidl=f"{total:.2f}€",
                total_mercadona=f"{total:.2f}€",
                total_celeiro=f"{total:.2f}€",
                auditor_note="FALLBACK ATIVADO: Preços gerados através da base de dados local devido a falha na pesquisa web em tempo real."
            )
            
        return plan
