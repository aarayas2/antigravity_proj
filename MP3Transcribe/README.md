# MP3Transcribe

A Python CLI tool to transcribe audiobook MP3 files into a combined PDF and Text file using `faster-whisper`.

## Requirements
- Python 3.10+
- `ffmpeg` (must be installed on your system and in your PATH, as it is required by whisper)

## Installation

1. Install dependencies using pip:
   ```bash
   pip install -r requirements.txt
   ```

2. Ensure `ffmpeg` is installed. 
   - On Ubuntu/Debian: `sudo apt install ffmpeg`
   - On macOS: `brew install ffmpeg`
   - On Windows: Download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) or use `winget install ffmpeg`

## Usage

Run the script providing the source directory of MP3 files and the desired output directory. 

Example:

```bash
python MP3Transcribe/MP3Transcribe.py --srcDir "D:\MUSIC\T.J. Stiles\The First Tycoon- The Epic Life of Cornelius Vanderbilt" --outDir "./output"
```

### Additional Arguments

- `--model`: The Whisper model size to use. Default is `base`. You can specify others like `tiny`, `small`, `medium`, or `large-v2`.

Example:

```bash
python MP3Transcribe/MP3Transcribe.py --srcDir "./mp3_files" --outDir "./output" --model "small"
```

## How It Works
- The tool scans `--srcDir` for `.mp3` files matching the pattern `"{bookTitle} - Chapter {number}.mp3"`.
- It sorts them in ascending numerical order by chapter number.
- Each file is transcribed, showing progress via `tqdm`.
- A final `.pdf` (with chapter headers and page numbers) and a `.txt` file are saved in `--outDir` using the extracted book title.
