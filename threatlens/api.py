"""
ThreatLens AI - CLI API Server Launcher
python -m threatlens.api
"""

import uvicorn

def main():
    print("=" * 60)
    print("STARTING THREATLENS AI FASTAPI BACKEND SERVER")
    print("Documentation: http://127.0.0.1:8000/docs")
    print("=" * 60)
    uvicorn.run("threatlens.backend.app:app", host="0.0.0.0", port=8000, reload=False)

if __name__ == "__main__":
    main()
