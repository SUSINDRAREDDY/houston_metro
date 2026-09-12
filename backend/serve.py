"""Respect the port injected by Cloud Run, with the existing local default."""
import os
import uvicorn

if __name__ == '__main__':
    uvicorn.run('backend.main:app', host='0.0.0.0', port=int(os.getenv('PORT', '8000')))
