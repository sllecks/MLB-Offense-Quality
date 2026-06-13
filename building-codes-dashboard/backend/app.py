import json
import os
import re
from typing import Optional

import anthropic
import httpx
from codes_data import CODE_CATEGORIES, build_upcodes_url, get_codes_for_jurisdiction
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="Building Codes Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_HEADERS = {"User-Agent": "BuildingCodesDashboard/1.0 (educational tool)"}


class LookupRequest(BaseModel):
    address: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    question: str
    jurisdiction: dict
    codes: dict
    history: list[ChatMessage] = []


async def geocode_address(address: str) -> Optional[dict]:
    """Geocode an address using Nominatim and return jurisdiction details."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            NOMINATIM_URL,
            params={"q": address, "format": "json", "addressdetails": 1, "limit": 1, "countrycodes": "us"},
            headers=NOMINATIM_HEADERS,
            timeout=10.0,
        )
        resp.raise_for_status()
        results = resp.json()

    if not results:
        return None

    result = results[0]
    addr = result.get("address", {})

    state_abbr = addr.get("ISO3166-2-lvl4", "").replace("US-", "")
    city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("municipality") or ""
    county = addr.get("county", "")
    state_name = addr.get("state", "")
    display_name = result.get("display_name", address)

    return {
        "display_name": display_name,
        "city": city,
        "county": county,
        "state": state_name,
        "state_abbr": state_abbr,
        "lat": result.get("lat"),
        "lon": result.get("lon"),
    }


def build_codes_response(jurisdiction_data: dict, codes_info: dict) -> dict:
    """Build the structured codes response for the frontend."""
    codes_list = []
    upcodes_slug = codes_info.get("upcodes_slug", jurisdiction_data.get("state_abbr", "").lower())

    for cat in CODE_CATEGORIES:
        key = cat["key"]
        code = codes_info.get(key)
        if code:
            codes_list.append({
                "category": cat["label"],
                "icon": cat["icon"],
                "color": cat["color"],
                "name": code["name"],
                "based_on": code["based_on"],
                "year": code.get("year"),
                "url": build_upcodes_url(upcodes_slug),
            })

    return {
        "jurisdiction": {
            "display": jurisdiction_data.get("display_name", ""),
            "city": jurisdiction_data.get("city", ""),
            "county": jurisdiction_data.get("county", ""),
            "state": jurisdiction_data.get("state", ""),
            "state_abbr": jurisdiction_data.get("state_abbr", ""),
            "jurisdiction_type": codes_info.get("jurisdiction_type", "state"),
        },
        "codes": codes_list,
        "notes": codes_info.get("notes"),
        "upcodes_slug": upcodes_slug,
    }


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/lookup")
async def lookup_codes(req: LookupRequest):
    if not req.address.strip():
        raise HTTPException(status_code=400, detail="Address is required")

    jurisdiction_data = await geocode_address(req.address)
    if not jurisdiction_data:
        raise HTTPException(status_code=404, detail="Address not found. Please try a more specific US address.")

    state_abbr = jurisdiction_data.get("state_abbr", "")
    city = jurisdiction_data.get("city", "")

    codes_info = get_codes_for_jurisdiction(state_abbr, city)
    if not codes_info:
        raise HTTPException(
            status_code=404,
            detail=f"Building codes not found for state: {jurisdiction_data.get('state', state_abbr)}. "
                   "This tool currently covers all 50 US states.",
        )

    return build_codes_response(jurisdiction_data, codes_info)


@app.post("/api/chat")
async def chat(req: ChatRequest):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY is not configured. Please add it to your .env file.",
        )

    jurisdiction = req.jurisdiction
    codes = req.codes

    codes_summary = "\n".join(
        f"- {c['category']}: {c['name']} (based on {c['based_on']})"
        for c in codes.get("codes", [])
    )

    system_prompt = f"""You are an expert building codes consultant with deep knowledge of US building codes, \
including the International Building Code (IBC), International Residential Code (IRC), \
International Energy Conservation Code (IECC), International Mechanical Code (IMC), \
International Plumbing Code (IPC), International Fire Code (IFC), NFPA standards, \
and all state/local amendments.

The user is asking about building codes for:
Location: {jurisdiction.get('display', 'Unknown location')}
City: {jurisdiction.get('city', 'N/A')}
County: {jurisdiction.get('county', 'N/A')}
State: {jurisdiction.get('state', 'N/A')}

Applicable codes for this jurisdiction:
{codes_summary}

{f"Important local notes: {codes.get('notes')}" if codes.get('notes') else ""}

Instructions:
1. Answer questions accurately based on the applicable codes listed above
2. Always cite specific code sections (e.g., "IBC 2021 Section 1208.2" or "IRC R302.1")
3. Note any jurisdiction-specific requirements or amendments when relevant
4. If a question falls outside typical building code scope, say so clearly
5. Be precise — incorrect code information can have serious safety and legal implications

You MUST respond with valid JSON only in this exact format (no markdown, no text outside JSON):
{{
  "answer": "Your detailed answer here. Use markdown for formatting (bold, lists, etc.).",
  "sources": [
    {{
      "code": "Code name (e.g., IBC 2021)",
      "section": "Section number (e.g., Section 1208.2)",
      "title": "Section title (e.g., Ceiling Height)",
      "excerpt": "Brief relevant excerpt or description from this section",
      "url": "https://up.codes/viewer/{codes.get('upcodes_slug', 'us')}"
    }}
  ]
}}

Include 1-5 sources. Only include sources that are directly relevant to the answer."""

    messages = [{"role": m.role, "content": m.content} for m in req.history]
    messages.append({"role": "user", "content": req.question})

    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=system_prompt,
        messages=messages,
    )

    raw = response.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {
            "answer": raw,
            "sources": [],
        }

    return parsed
