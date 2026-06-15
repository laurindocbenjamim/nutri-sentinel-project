import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env")

async def update_user():
    uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGODB_DB_NAME")
    
    if not uri or not db_name:
        print("MongoDB environment variables not found.")
        return
        
    client = AsyncIOMotorClient(uri)
    db = client[db_name]
    collection = db["user_profiles"]
    
    user_id = "test_user_laurindo"
    
    update_data = {
        "$set": {
            "pathologies": ["Diabetes Tipo 2", "Hipertensão"],
            "allergies": ["Glúten", "Amendoins"],
            "medications": ["Metformina", "Lisinopril"]
        }
    }
    
    result = await collection.update_one({"user_id": user_id}, update_data)
    if result.matched_count == 0:
        print(f"User {user_id} not found. Inserting default user.")
        await collection.insert_one({
            "user_id": user_id,
            "age": 45,
            "sex": "masculino",
            "pregnancy": False,
            "goal": "perder_peso",
            "budget_tier": "Medio",
            "activity_level": "sedentario",
            "pathologies": ["Diabetes Tipo 2", "Hipertensão"],
            "allergies": ["Glúten", "Amendoins"],
            "medications": ["Metformina", "Lisinopril"]
        })
        print("User inserted.")
    else:
        print(f"User {user_id} updated successfully.")
        
    client.close()

if __name__ == "__main__":
    asyncio.run(update_user())
