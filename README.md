# pinterest-bulk-downloader

This is a simple command-line tool I built to back up my Pinterest boards. It scrapes board pages, extracts the high-resolution original image URLs from the page state, and downloads them concurrently. No API keys or developer accounts required.

## Installation

Clone the repo and install the dependencies:

```cmd
pip install -r requirements.txt
```

## Usage

Pass the URL of the board you want to download. By default, it will save images to a folder named after the board under `downloads/` in your current directory.

```cmd
python pinterest_dl.py https://www.pinterest.com/username/my-board-name/
```

Options:
* `-o`, `--output`: Specify a custom output directory.
* `-w`, `--workers`: Number of concurrent download workers (default is 8).
* `-l`, `--limit`: Limit the maximum number of images to download.

```cmd
python pinterest_dl.py https://www.pinterest.com/username/my-board-name/ -o D:\Media\Pinterest -w 16 --limit 100
```

<!-- checked: 2026-09-26 -->
