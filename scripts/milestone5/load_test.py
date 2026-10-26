"""Bounded HTTP load against MetroAI; no AI calls or database writes."""
import asyncio
import json
import os
import time
from collections import Counter
import httpx

async def main():
    url=os.getenv('TARGET_URL','http://metroai.metroai.svc.cluster.local/')
    seconds=min(240,max(1,int(os.getenv('DURATION_SECONDS','60'))))
    concurrency=min(96,max(1,int(os.getenv('CONCURRENCY','64'))))
    counts=Counter()
    started=time.monotonic(); end=started+seconds
    async with httpx.AsyncClient(timeout=10,limits=httpx.Limits(max_connections=concurrency,max_keepalive_connections=concurrency)) as client:
        async def worker():
            while time.monotonic()<end:
                try:
                    response=await client.get(url)
                    counts[str(response.status_code)]+=1
                except httpx.HTTPError:
                    counts['network_error']+=1
        await asyncio.gather(*(worker() for _ in range(concurrency)))
    print(json.dumps({'url':url,'duration_seconds':round(time.monotonic()-started,2),'concurrency':concurrency,'responses':dict(counts)},sort_keys=True),flush=True)

if __name__=='__main__':
    asyncio.run(main())
