### Complete API Endpoints Reference

#### `POST /api/session/init`
**Description:** Init Session

**Expected Responses:**
- **200**: Successful Response

#### `GET /api/system/background-agents`
**Description:** Get Background Agents

**Expected Responses:**
- **200**: Successful Response

#### `POST /api/synthetic/generate`
**Description:** Generate Images

**Payload (application/json):**
```json
{
  "selections": "object",
  "eval_time": "any",
}
```

**Expected Responses:**
- **200**: Successful Response
- **422**: Validation Error
  ```json
  {
    "detail": "array",
  }
  ```

#### `GET /api/synthetic/templates/card`
**Description:** Get Ref Card

**Expected Responses:**
- **200**: Successful Response

#### `GET /api/synthetic/templates/stick`
**Description:** Get Urine Stick

**Expected Responses:**
- **200**: Successful Response

#### `POST /api/analysis/upload`
**Description:** Upload Image

**Payload (multipart/form-data):**
```json
{
  "file": "string",
}
```

**Expected Responses:**
- **200**: Successful Response
- **422**: Validation Error
  ```json
  {
    "detail": "array",
  }
  ```

#### `POST /api/blood-analysis/upload`
**Description:** Upload Blood Report

**Payload (multipart/form-data):**
```json
{
  "file": "string",
  "user_uuid": "string",
}
```

**Expected Responses:**
- **200**: Successful Response
  ```json
  {
    "patient_name": "any",
    "report_date": "any",
    "biomarkers": "array",
    "recommendations": "any",
  }
  ```
- **422**: Validation Error
  ```json
  {
    "detail": "array",
  }
  ```

#### `POST /api/nutrition/plan`
**Description:** Generate a personalized weekly nutrition plan

**Payload (application/json):**
```json
{
  "urinalysis_data": "any",
  "user_id": "string",
}
```

**Expected Responses:**
- **200**: Successful Response
  ```json
  {
    "success": "boolean",
    "plan": "any",
    "error": "any",
    "triage_alert": "any",
  }
  ```
- **422**: Validation Error
  ```json
  {
    "detail": "array",
  }
  ```

#### `GET /api/nutrition/status`
**Description:** Nutritional agents subsystem health check

**Expected Responses:**
- **200**: Successful Response

#### `GET /api/nutrition/profile/{user_id}`
**Description:** Get User Clinical Profile

**Expected Responses:**
- **200**: Successful Response
  ```json
  {
    "user_id": "string",
    "user_uuid": "any",
    "username": "any",
    "age": "integer",
    "sex": "string",
    "pathologies": "array",
    "allergies": "array",
    "medications": "array",
    "pregnancy": "boolean",
    "goal": "string",
    "budget_tier": "any",
    "activity_level": "string",
  }
  ```
- **422**: Validation Error
  ```json
  {
    "detail": "array",
  }
  ```

#### `GET /api/nutrition/shopping-list`
**Description:** Visualize a sample shopping list

**Expected Responses:**
- **200**: Successful Response

#### `GET /api/nutrition/ingredients`
**Description:** List all ingredients

**Expected Responses:**
- **200**: Successful Response
- **422**: Validation Error
  ```json
  {
    "detail": "array",
  }
  ```

