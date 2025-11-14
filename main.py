import os
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from bson import ObjectId

# Database helpers
from database import create_document, get_documents, db

app = FastAPI(title="NovaStudio AI - Video Creation Platform", version="0.1.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------
# Schemas (Collections)
# --------------------

class Brand(BaseModel):
    name: str
    logo_url: Optional[str] = None
    primary_color: Optional[str] = "#6d28d9"
    secondary_color: Optional[str] = "#0ea5e9"
    font_family: Optional[str] = "Inter"

class Template(BaseModel):
    title: str
    category: str = Field(..., description="marketing | education | training | entertainment")
    thumbnail_url: Optional[str] = None
    description: Optional[str] = None
    timeline: Optional[Dict[str, Any]] = None

class Media(BaseModel):
    kind: str = Field(..., description="video|image|audio|subtitle|avatar|voice")
    source_url: Optional[str] = None
    filename: Optional[str] = None
    transcript: Optional[str] = None
    language: Optional[str] = "en"
    metadata: Optional[Dict[str, Any]] = None

class Project(BaseModel):
    title: str
    description: Optional[str] = None
    brand_id: Optional[str] = None
    template_id: Optional[str] = None
    timeline: Optional[Dict[str, Any]] = None
    media_ids: List[str] = []
    settings: Dict[str, Any] = Field(default_factory=lambda: {
        "resolution": "1080p",
        "fps": 30,
        "aspect": "16:9",
        "platforms": ["youtube", "tiktok", "instagram"],
    })

class RenderJob(BaseModel):
    project_id: str
    job_type: str = Field(..., description="render | dub | subtitles | translate | edit | avatar")
    status: str = Field(default="queued")
    progress: int = 0
    params: Optional[Dict[str, Any]] = None
    output_url: Optional[str] = None
    error: Optional[str] = None

class ScriptToVideoRequest(BaseModel):
    title: str
    script: str
    language: str = "en"
    platform: str = "youtube"  # youtube | tiktok | instagram
    voice_style: Optional[str] = "neutral"
    include_subtitles: bool = True

class EditCommandRequest(BaseModel):
    project_id: str
    command: str  # e.g., "cut from 00:10 to 00:14, add b-roll of city skyline, auto color correct"
    language: Optional[str] = "en"

class VoiceCloneRequest(BaseModel):
    name: str
    sample_url: Optional[str] = None
    language: Optional[str] = "en"

class AvatarGenerateRequest(BaseModel):
    name: str
    image_url: Optional[str] = None
    style: Optional[str] = "ultra-realistic"  # ultra-realistic | toon | photoreal
    emotions: List[str] = ["neutral", "happy", "confident"]


# --------------------
# Helper functions
# --------------------

def to_str_id(doc: Dict[str, Any]) -> Dict[str, Any]:
    if doc is None:
        return doc
    d = dict(doc)
    _id = d.get("_id")
    if isinstance(_id, ObjectId):
        d["id"] = str(_id)
        del d["_id"]
    return d


# --------------------
# Root & health
# --------------------

@app.get("/")
def read_root():
    return {
        "name": "NovaStudio AI",
        "message": "Backend running",
        "features": [
            "command-editing",
            "subtitles-120+",
            "ai-dubbing-voice-clone",
            "avatars-talking-photo",
            "text-image-audio-to-video",
            "translation-localization",
            "templates-branding",
            "analytics",
            "developer-api"
        ]
    }


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "❌ Not Set",
        "database_name": "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set"
            response["database_name"] = getattr(db, "name", "✅ Connected")
            try:
                response["collections"] = db.list_collection_names()[:10]
                response["database"] = "✅ Connected & Working"
                response["connection_status"] = "Connected"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:120]}"
    # env
    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


# --------------------
# Brands & Templates
# --------------------

@app.post("/api/brands")
def create_brand(brand: Brand):
    brand_id = create_document("brand", brand)
    return {"id": brand_id}

@app.get("/api/brands")
def list_brands(limit: int = 50):
    items = get_documents("brand", {}, limit)
    return [to_str_id(i) for i in items]

@app.post("/api/templates")
def create_template(tpl: Template):
    tpl_id = create_document("template", tpl)
    return {"id": tpl_id}

@app.get("/api/templates")
def list_templates(limit: int = 50):
    items = get_documents("template", {}, limit)
    return [to_str_id(i) for i in items]


# --------------------
# Media
# --------------------

@app.post("/api/media")
def add_media(media: Media):
    media_id = create_document("media", media)
    return {"id": media_id}

@app.get("/api/media")
def list_media(limit: int = 100):
    items = get_documents("media", {}, limit)
    return [to_str_id(i) for i in items]


# --------------------
# Projects
# --------------------

@app.post("/api/projects")
def create_project(project: Project):
    project_id = create_document("project", project)
    return {"id": project_id}

@app.get("/api/projects")
def list_projects(limit: int = 100):
    items = get_documents("project", {}, limit)
    return [to_str_id(i) for i in items]

@app.get("/api/projects/{project_id}")
def get_project(project_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    try:
        doc = db["project"].find_one({"_id": ObjectId(project_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid project id")
    if not doc:
        raise HTTPException(status_code=404, detail="Project not found")
    return to_str_id(doc)


# --------------------
# AI Workflows (MVP stubs)
# --------------------

@app.post("/api/scripts-to-video")
def script_to_video(req: ScriptToVideoRequest):
    # Create project
    project = Project(
        title=req.title,
        description=f"Auto-generated from script for {req.platform}",
        timeline={
            "tracks": [
                {"type": "voiceover", "language": req.language, "style": req.voice_style},
                {"type": "subtitles", "enabled": req.include_subtitles},
                {"type": "visuals", "source": "stock+ai"}
            ],
            "script_excerpt": req.script[:400]
        },
        settings={"resolution": "1080p", "fps": 30, "aspect": "9:16" if req.platform=="tiktok" else "16:9", "platforms": [req.platform]}
    )
    project_id = create_document("project", project)

    # Create a render job (simulated)
    job = RenderJob(
        project_id=project_id,
        job_type="render",
        status="completed",
        progress=100,
        params={"language": req.language, "platform": req.platform},
        output_url="https://storage.googleapis.com/vr-demo-assets/sample-output.mp4"
    )
    job_id = create_document("renderjob", job)

    return {
        "project_id": project_id,
        "job_id": job_id,
        "status": "completed",
        "output_url": job.output_url
    }


@app.post("/api/ai/edit")
def ai_edit(req: EditCommandRequest):
    # In a real system, we would parse the command, modify timeline, create job
    # Here, we simulate a diff and create a quick job record
    simulated_diff = {
        "actions": [
            {"op": "cut", "from": "00:10", "to": "00:14"},
            {"op": "add_broll", "query": "city skyline"},
            {"op": "color", "mode": "auto-correct"}
        ]
    }
    job = RenderJob(project_id=req.project_id, job_type="edit", status="completed", progress=100,
                    params={"command": req.command, "language": req.language},
                    output_url="https://storage.googleapis.com/vr-demo-assets/edited-preview.mp4")
    job_id = create_document("renderjob", job)
    return {"job_id": job_id, "status": "completed", "diff": simulated_diff, "preview_url": job.output_url}


@app.post("/api/voices/clone")
def voice_clone(req: VoiceCloneRequest):
    media = Media(kind="voice", source_url=req.sample_url, language=req.language, metadata={"name": req.name, "clone": True})
    media_id = create_document("media", media)
    return {"voice_id": media_id, "status": "ready"}


@app.post("/api/avatars/generate")
def avatar_generate(req: AvatarGenerateRequest):
    media = Media(kind="avatar", source_url=req.image_url, metadata={"name": req.name, "style": req.style, "emotions": req.emotions})
    media_id = create_document("media", media)
    return {"avatar_id": media_id, "preview_url": "https://storage.googleapis.com/vr-demo-assets/avatar-preview.gif"}


# --------------------
# Render Jobs (lookup)
# --------------------

@app.get("/api/renderjobs/{job_id}")
def get_render_job(job_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    try:
        doc = db["renderjob"].find_one({"_id": ObjectId(job_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid job id")
    if not doc:
        raise HTTPException(status_code=404, detail="Job not found")
    return to_str_id(doc)


# --------------------
# Analytics (mocked)
# --------------------

@app.get("/api/analytics")
def analytics():
    return {
        "views": 12840,
        "avg_watch_time": 42.6,
        "engagement_rate": 0.37,
        "top_platforms": [
            {"name": "YouTube", "views": 7400},
            {"name": "TikTok", "views": 3820},
            {"name": "Instagram", "views": 1620}
        ],
        "languages": {"en": 0.72, "es": 0.14, "fr": 0.06, "de": 0.08}
    }


# --------------------
# Developer API helper
# --------------------

@app.get("/api/hello")
def hello():
    return {"message": "Hello from NovaStudio AI backend!"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
