import argparse
import concurrent.futures
import json
import pathlib
import re
import sys
import time
import httpx

# FIXME: pinterest sometimes returns 403 for some user-agents, need rotation list if this becomes common

def extract_pins_from_html(html_content: str) -> list[str]:
    """Extract high-resolution pin URLs from the board HTML."""
    match = re.search(r'<script id="__PWS_DATA__" type="application/json">(.*?)</script>', html_content)
    if not match:
        match = re.search(r'<script id="initial-state" type="application/json">(.*?)</script>', html_content)
    if not match:
        # Fallback if scripts are assigned directly to window
        match = re.search(r'window\.__PWS_DATA__\s*=\s*(\{.*?\});', html_content)
    
    if not match:
        return []
    
    # print(f"DEBUG: extracted state block size: {len(match.group(1))} bytes")
    
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []
    
    urls = set()
    def find_originals(obj):
        if isinstance(obj, dict):
            if "originals" in obj and isinstance(obj["originals"], dict):
                val = obj["originals"].get("url")
                if val and isinstance(val, str):
                    urls.add(val)
            for v in obj.values():
                find_originals(v)
        elif isinstance(obj, list):
            for item in obj:
                find_originals(item)
                
    find_originals(data)
    return sorted(list(urls))

def download_image(client: httpx.Client, url: str, dest_dir: pathlib.Path) -> bool:
    filename = url.split("/")[-1]
    out_path = dest_dir / filename
    if out_path.exists():
        return False
        
    retries = 3
    backoff = 2.0
    for attempt in range(retries):
        try: 
            resp = client.get(url, timeout=15.0)
            if resp.status_code == 429:
                time.sleep(backoff)
                backoff *= 2
                continue
            resp.raise_for_status()
            out_path.write_bytes(resp.content)
            return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                break
            if attempt == retries - 1:
                raise
        except httpx.RequestError:
            if attempt == retries - 1:
                raise
            time.sleep(backoff)
            backoff *= 2
    return False

def download_board(boardUrl: str, output_path: pathlib.Path, max_workers: int):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    try:
        with httpx.Client(headers=headers, follow_redirects=True) as client:
            r = client.get(boardUrl, timeout=20.0)
            r.raise_for_status()
            html = r.text
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        print(f"Error fetching the board page: {e}", file=sys.stderr)
        sys.exit(1)
        
    urls = extract_pins_from_html(html)
    if not urls:
        print("No high-resolution images found on this board. The board may be private or format changed.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Found {len(urls)} images. Starting download...")
    output_path.mkdir(parents=True, exist_ok=True)
    
    success_count = 0
    skipped_count = 0
    
    with httpx.Client(headers=headers, follow_redirects=True) as dl_client:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(download_image, dl_client, url, output_path): url for url in urls}
            for fut in concurrent.futures.as_completed(futures):
                url = futures[fut]
                try:
                    was_downloaded = fut.result()
                    if was_downloaded:
                        success_count += 1
                        print(f"Downloaded: {url.split('/')[-1]}")
                    else:
                        skipped_count += 1
                except Exception as e:
                    print(f"Failed to download {url}: {e}", file=sys.stderr)
                    
    print(f"\nFinished. New downloads: {success_count}, Skipped (already exist): {skipped_count}")

def main():
    parser = argparse.ArgumentParser(
        description="Download original high-res images from a Pinterest board.",
        epilog="Example: python pinterest_dl.py https://www.pinterest.com/username/board-name/ -o downloads"
    )
    parser.add_argument("url", help="Pinterest board URL")
    parser.add_argument("-o", "--output", default="downloads", help="Directory to save images")
    parser.add_argument("-w", "--workers", type=int, default=5, help="Number of concurrent downloads")
    
    args = parser.parse_args()
    
    dest = pathlib.Path(args.output)
    download_board(args.url, dest, args.workers)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted by user.")
        sys.exit(1)
