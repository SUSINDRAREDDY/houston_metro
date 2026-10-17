"""Private object uploads authenticated by the attached VM service account."""
import asyncio
import hashlib
import io
import os
import uuid
from urllib.parse import unquote
from fastapi import APIRouter, HTTPException, Request, Response
from . import database

router = APIRouter(prefix='/api/uploads', tags=['uploads'])
LIMIT = 5 * 1024 * 1024


def bucket():
    from google.cloud import storage
    name = os.getenv('UPLOAD_BUCKET')
    if not name or not database.managed():
        raise HTTPException(503, 'Cloud uploads are not configured.')
    # No key path and no from_service_account_json: ADC uses the VM metadata identity.
    return storage.Client().bucket(name)


@router.get('')
def list_uploads():
    if not database.managed():
        return []
    with database.connect() as db:
        return [dict(r) for r in db.execute('SELECT id,filename,content_type,size_bytes,sha256,created_at FROM uploads ORDER BY created_at DESC LIMIT 100')]


def save(data, filename, content_type):
    identifier = str(uuid.uuid4())
    target = bucket().blob('uploads/' + identifier + '/' + filename)
    target.metadata = {'sha256': hashlib.sha256(data).hexdigest()}
    target.upload_from_string(data, content_type=content_type, if_generation_match=0, timeout=60)
    try:
        with database.connect() as db:
            row = db.execute('''INSERT INTO uploads(id,filename,content_type,size_bytes,sha256,bucket_name,object_name,generation)
                VALUES (?,?,?,?,?,?,?,?) RETURNING id,filename,content_type,size_bytes,sha256,created_at''',
                (identifier,filename,content_type,len(data),target.metadata['sha256'],target.bucket.name,target.name,str(target.generation))).fetchone()
            db.commit()
            return dict(row)
    except Exception:
        target.delete(if_generation_match=target.generation, timeout=30)
        raise


@router.post('', status_code=201)
async def upload(request: Request):
    name = unquote(request.headers.get('X-Filename', '')).replace('\\', '/').split('/')[-1]
    if not name or len(name) > 120 or any(ord(c) < 32 for c in name) or name in ('.', '..'):
        raise HTTPException(422, 'Choose a filename of 1 to 120 characters.')
    body = io.BytesIO()
    async for chunk in request.stream():
        if body.tell() + len(chunk) > LIMIT:
            raise HTTPException(413, 'Maximum file size is 5 MB.')
        body.write(chunk)
    if not body.tell():
        raise HTTPException(422, 'The selected file is empty.')
    return await asyncio.to_thread(save, body.getvalue(), name, request.headers.get('Content-Type', 'application/octet-stream'))


@router.get('/{identifier}')
def download(identifier: uuid.UUID):
    with database.connect() as db:
        row = db.execute('SELECT * FROM uploads WHERE id=?', (str(identifier),)).fetchone()
    if not row:
        raise HTTPException(404, 'File not found.')
    target = bucket().blob(row['object_name'], generation=int(row['generation']))
    data = target.download_as_bytes(if_generation_match=int(row['generation']), timeout=60)
    return Response(data, media_type='application/octet-stream', headers={
        'Content-Disposition': "attachment; filename*=UTF-8''" + __import__('urllib.parse',fromlist=['quote']).quote(row['filename']),
        'X-Content-Type-Options': 'nosniff',
    })
