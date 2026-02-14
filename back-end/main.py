from fastapi import FastAPI, HTTPException, Request, Depends, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os
import json
import asyncio

from db_helper_functions import (
    init_db, close_db, recordInsight, getLatestInsightRecordFromDB,
    createUser, getUserHash, getUserDetails, getUserByUsername,
    getAllUsers, updateUser, deleteUser, countAdmins,
)
from helper_classes import (
    LoginRequest, PromptRequest, InsightRequest, BaseSimulationRequest,
    RegistrationRequest, BatchUpdateRequest, SlackConnectRequest,
)
from hashing import hash_password, verify_hash
from token_cryptography import generateToken
from access_validation import admin_access_required, getUserFromToken

from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()
# Pre-flight check
if not os.getenv("GROQ_API_KEY"):
    print("ERROR: GROQ_API_KEY not found in .env")
    exit(1)

# LangGraph agent to process queries
from agent import enterprise_agent

# Set to true to have system get latest insights periodically from LLM
# instead of per request from frontend
PERIODIC_UPDATES = False

async def query_langgraph(messages, role, current_silo:str, is_simulation=False, simulation_inputs=[]):
    # Input format required by LangGraph
    inputs = {
        "messages": messages,
        "role": role,
        "is_simulation": is_simulation,
        "simulation_inputs": simulation_inputs,
        "current_silo": current_silo,
        "sql_results": {},
        "fact_sheet_history": []
    }

    try:
        final_state = await enterprise_agent.ainvoke(inputs)
        insight = final_state.get("final_insight")

        if insight is None or (isinstance(insight, dict) and len(insight) == 0):
            return {
                "status": "no_insight",
                "message": "No insight generated for this request.",
                "end_early": bool(final_state.get("end_early", False)),
                "needs_more_data": bool(final_state.get("needs_more_data", False)),
                "audit_summary": final_state.get("audit_summary")
            }

        if not isinstance(insight, dict):
            raise HTTPException(status_code=500, detail="LangGraph returned invalid final_insight format")
        
        return insight
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Function to periodically get the latest insights from LangGraph
# every 60 seconds and then insert it into the database
valid_domains = ["crm", "accounting", "hr", "operations", "sales"]
async def retrievePeriodicUpdatedInsights():
    while True:
        for domain in valid_domains:
            proactive_inputs = {
                "messages": [("user", "Perform a cross-domain health check. Look for anomalies.")],
                "role": "CEO", # Placeholder for now
                "is_simulation": False,
                "current_silo": domain # Initializing to avoid KeyErrors
            }
            
            json_result = await query_langgraph(**proactive_inputs)
            recordInsight(json_result, domain)
        
        await asyncio.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup function
    if PERIODIC_UPDATES:
        task = asyncio.create_task(retrievePeriodicUpdatedInsights())
    init_db()

    # Run teh app
    yield

    # Close database connection when no longer required
    close_db()

    if PERIODIC_UPDATES:
        # Cancel the task once the app closes
        task.cancel()

        try:
            # Trigger it one more time to cancel it.
            await task
        except asyncio.CancelledError: # Expectde
            pass

app = FastAPI(lifespan=lifespan)

async def retrieveSimulationResults(request: Request, set_fields: BaseSimulationRequest):
    try:
        extra_params = await request.json()
    except Exception as e:
        return HTTPException(status_code=500, detail="Could not parse JSON inpu")
    
    # Remove set fields (domain, role_context, and prompt) from this
    # to leave only extra parameters for the simulation
    for field in set_fields.model_dump().keys():
        if field in extra_params:
            del extra_params[field]
    
    if set_fields.prompt is None:
        set_fields.prompt = "Use simulation inputs to build a baseline query for revenue and latency trends."

    sim_inputs = {
        "messages": [(set_fields.role_context, set_fields.prompt)],
        "role": set_fields.role_context,
        "is_simulation": True,
        "simulation_inputs": extra_params,
        "current_silo": set_fields.domain
    }

    response = await query_langgraph(**sim_inputs)

    return response

@app.post("/simulation")
async def getSimulation(request: Request, set_fields: BaseSimulationRequest, current_user: str = Depends(getUserFromToken)):
    return await retrieveSimulationResults(request, set_fields)

# Function to get latest row from insights table in the database 
async def getLatestInsights(domain, role_context):
    if PERIODIC_UPDATES:
        insight_result = getLatestInsightRecordFromDB(domain)
    else:
        proactive_inputs = {
            "messages": [("user", "Perform a cross-domain health check. Look for anomalies.")],
            "role": role_context, # Placeholder for now
            "is_simulation": False,
            "current_silo": domain # Initializing to avoid KeyErrors
        }
        
        insight_result = await query_langgraph(**proactive_inputs)
    return insight_result

@app.post("/insights")
async def getInsights(data: InsightRequest, current_user: str = Depends(getUserFromToken)):
    domain = data.domain
    role_context = data.role_context

    return await getLatestInsights(domain, role_context)

@app.post("/prompt")
async def getPrompt(data: PromptRequest, current_user: str = Depends(getUserFromToken)):
    inputs = {
        "messages": [
            ("user", data.prompt),
        ],
        "role": data.role_context,
        "is_simulation": False,
        "current_silo": data.domain
    }

    json_result = await query_langgraph(**inputs)
    return json_result

@app.post("/auth/login")
async def login(data: LoginRequest):
    recorded_hash = getUserHash(data.username)
    if recorded_hash is None:
        raise HTTPException(status_code=401, detail="User does not exist")
    
    if verify_hash(data.password, recorded_hash[0]):
        token = generateToken(data.username)
        return {
            "token": token,
            "user": getUserDetails(data.username)
        }
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/admin/users")
async def addNewUser(data: RegistrationRequest, current_user: str = Depends(admin_access_required)):
    # Check if user already exists
    existing = getUserByUsername(data.username)
    if existing:
        raise HTTPException(status_code=409, detail=f"User '{data.username}' already exists")

    hashed = hash_password(data.password)
    data_dict = data.__dict__
    del data_dict['password']
    data_dict["hashed"] = hashed

    createUser(**data_dict)
    return {
        "detail": f"User {data.username} created",
        "user": getUserDetails(data.username)
    }


# ──────────────────────────────────────────────
#  Admin – list / search users
# ──────────────────────────────────────────────
@app.get("/admin/users")
async def listUsers(
    search_username: str | None = Query(None),
    current_user: str = Depends(admin_access_required),
):
    """Return all users, or filter by partial username match."""
    users = getAllUsers()
    if search_username:
        q = search_username.lower()
        users = [u for u in users if q in u["username"].lower()]
    return {"users": users}


# ──────────────────────────────────────────────
#  Admin – delete a single user
# ──────────────────────────────────────────────
@app.delete("/admin/users/{username}")
async def removeUser(username: str, current_user: str = Depends(admin_access_required)):
    target = getUserByUsername(username)
    if target is None:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")

    # Prevent deleting the last admin
    if target["mode"] == "admin" and countAdmins() <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last admin user")

    # Prevent self-deletion
    if target["username"].lower() == current_user.lower():
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    deleteUser(username)
    return {"detail": f"User '{username}' deleted"}


# ──────────────────────────────────────────────
#  Admin – batch update / delete users
# ──────────────────────────────────────────────
@app.patch("/admin/users/batch")
async def batchUpdateUsers(
    data: BatchUpdateRequest,
    current_user: str = Depends(admin_access_required),
):
    results = {"updated": [], "deleted": [], "errors": []}

    # --- updates ---
    for item in data.updates:
        target = getUserByUsername(item.username)
        if target is None:
            results["errors"].append(f"User '{item.username}' not found")
            continue

        fields = {}
        if item.display_name is not None:
            fields["display_name"] = item.display_name
        if item.mode is not None:
            # Prevent removing the last admin
            if target["mode"] == "admin" and item.mode != "admin" and countAdmins() <= 1:
                results["errors"].append(f"Cannot demote '{item.username}' – last admin")
                continue
            fields["mode"] = item.mode
        if item.department is not None:
            fields["department"] = item.department
        if item.role is not None:
            fields["role"] = item.role
        if item.password is not None:
            fields["hash"] = hash_password(item.password)

        if fields:
            updateUser(item.username, **fields)
            results["updated"].append(item.username)

    # --- deletes ---
    for uname in data.deletes:
        target = getUserByUsername(uname)
        if target is None:
            results["errors"].append(f"User '{uname}' not found (delete)")
            continue
        if target["mode"] == "admin" and countAdmins() <= 1:
            results["errors"].append(f"Cannot delete last admin '{uname}'")
            continue
        if uname.lower() == current_user.lower():
            results["errors"].append("Cannot delete yourself")
            continue
        deleteUser(uname)
        results["deleted"].append(uname)

    return results


# ──────────────────────────────────────────────
#  Chat – send message (with optional file)
# ──────────────────────────────────────────────
@app.post("/chat")
async def chat(
    message: str = Form(...),
    domain: str = Form("crm"),
    role_context: str = Form("Analyst"),
    file: UploadFile | None = File(None),
    current_user: str = Depends(getUserFromToken),
):
    """Process a chat message and optionally attach a file for context."""
    file_context = ""
    if file:
        content = await file.read()
        try:
            file_context = f"\n\n[Attached file: {file.filename}]\n{content.decode('utf-8', errors='replace')[:5000]}"
        except Exception:
            file_context = f"\n\n[Attached file: {file.filename} (binary, preview unavailable)]"

    prompt_text = message + file_context

    inputs = {
        "messages": [("user", prompt_text)],
        "role": role_context,
        "is_simulation": False,
        "current_silo": domain,
    }
    result = await query_langgraph(**inputs)
    return result


# ──────────────────────────────────────────────
#  Context – file upload for RAG / enrichment
# ──────────────────────────────────────────────
@app.post("/context/upload")
async def uploadContext(
    file: UploadFile = File(...),
    current_user: str = Depends(getUserFromToken),
):
    """Accept a file upload to enrich the AI context.
    For now, we acknowledge receipt; downstream RAG integration is TBD."""
    content = await file.read()
    size = len(content)
    return {
        "detail": f"File '{file.filename}' received ({size} bytes)",
        "filename": file.filename,
        "size": size,
    }


# ──────────────────────────────────────────────
#  Integrations – Slack webhook
# ──────────────────────────────────────────────
@app.post("/integrations/slack/connect")
async def connectSlack(
    data: SlackConnectRequest,
    current_user: str = Depends(admin_access_required),
):
    """Register a Slack webhook URL (stub — actual webhook posting is TBD)."""
    return {"detail": "Slack webhook registered", "webhook_url": data.webhook_url}