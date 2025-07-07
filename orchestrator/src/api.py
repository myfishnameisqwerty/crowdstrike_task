from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import glob
from workflow import Workflow

app = FastAPI(title="Orchestrator Service")

# Get service URLs from environment variables
data_scraper_url = os.getenv('DATA_SCRAPER_URL', 'http://data-scraper-service:9001')
image_downloader_url = os.getenv('IMAGE_DOWNLOADER_URL', 'http://image-downloader:9002')

# Create workflow instance
workflow = Workflow(data_scraper_url, image_downloader_url)

class TriggerRequest(BaseModel):
    trigger: str

@app.post("/trigger")
def trigger_workflow(req: TriggerRequest):
    try:
        print(f"🚀 Starting workflow for trigger: {req.trigger}")
        
        # Run the workflow
        result = workflow.run(req.trigger)
        
        if result["status"] == "success":
            return {
                "status": "completed",
                "trigger": req.trigger,
                "html_file": result["html_file"],
                "html_url": result["html_url"],
                "message": f"Workflow completed successfully! HTML available at: {result['html_url']}"
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except Exception as e:
        print(f"❌ Workflow failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/status")
def get_status():
    """Get orchestrator status."""
    try:
        is_running = workflow.is_running()
        services_healthy = workflow.service_client.check_services_health()
        
        return {
            "status": "running" if is_running else "idle",
            "services_healthy": services_healthy,
            "data_scraper_url": data_scraper_url,
            "image_downloader_url": image_downloader_url
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/html")
def list_html_files():
    """List all available HTML files."""
    try:
        html_files = glob.glob("/tmp/*_gallery.html")
        files = []
        for file_path in html_files:
            filename = os.path.basename(file_path)
            files.append({
                "filename": filename,
                "path": file_path,
                "size": os.path.getsize(file_path),
                "url": f"http://localhost:9003/html/{filename}"
            })
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/html/{filename}")
def get_html_file(filename: str):
    """Download a specific HTML file."""
    try:
        file_path = f"/tmp/{filename}"
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="text/html"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 