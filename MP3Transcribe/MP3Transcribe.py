import argparse
import os
import re
import sys
import logging
from pathlib import Path
from tqdm import tqdm

# Fix for silent native crashes on Windows with PyTorch/OpenMP and HuggingFace symlinks
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"

from faster_whisper import WhisperModel
from fpdf import FPDF

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def sanitize_text_for_pdf(text):
    replacements = {
        '’': "'", '‘': "'", '“': '"', '”': '"', '—': '-', '–': '-',
        '…': '...', '•': '*', '\u200b': '', '\xa0': ' '
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode('latin-1', 'replace').decode('latin-1')

class PDF(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

def parse_args():
    parser = argparse.ArgumentParser(description="Transcribe MP3 files to PDF and Text.")
    parser.add_argument("--srcDir", required=True, help="Path to source directory containing MP3 files")
    parser.add_argument("--outDir", required=True, help="Path to output directory where the final PDF will be saved")
    parser.add_argument("--model", default="base", help="Whisper model to use (default: base)")
    parser.add_argument("--device", default="cpu", help="Device to run inference on ('cpu', 'cuda', 'auto'). Default: cpu")
    parser.add_argument("--compute_type", default="int8", help="Compute type ('int8', 'float16', 'float32', 'default'). Default: int8")
    return parser.parse_args()

def get_mp3_files(src_dir):
    src_path = Path(src_dir)
    if not src_path.is_dir():
        logging.error(f"Source directory does not exist or is not a directory: {src_path}")
        sys.exit(1)

    mp3_files = []
    regex = re.compile(r' - Chapter (\d+)\.mp3$', re.IGNORECASE)
    
    for f in src_path.iterdir():
        if f.is_file():
            if f.suffix.lower() == '.mp3':
                match = regex.search(f.name)
                if match:
                    chapter_num = int(match.group(1))
                    mp3_files.append((chapter_num, f))
                else:
                    logging.warning(f"Skipping MP3 file with unrecognized name pattern: {f.name}")
            else:
                logging.warning(f"Skipping non-MP3 file: {f.name}")

    if not mp3_files:
        logging.error("No valid MP3 files found in the source directory.")
        sys.exit(1)

    mp3_files.sort(key=lambda x: x[0])
    return mp3_files

def extract_book_title(first_filename):
    regex = re.compile(r'(.*) - Chapter \d+\.mp3$', re.IGNORECASE)
    match = regex.match(first_filename)
    if match:
        return match.group(1).strip()
    return "Transcribed Book"

def main():
    args = parse_args()
    
    src_dir = args.srcDir
    out_dir = Path(args.outDir)
    model_size = args.model

    mp3_files = get_mp3_files(src_dir)

    book_title = extract_book_title(mp3_files[0][1].name)
    logging.info(f"Book Title Identified: {book_title}")

    out_dir.mkdir(parents=True, exist_ok=True)
    
    pdf_path = out_dir / f"{book_title}.pdf"
    txt_path = out_dir / f"{book_title}.txt"

    logging.info(f"Loading Whisper model '{model_size}' on '{args.device}' with compute_type='{args.compute_type}'...")
    try:
        model = WhisperModel(model_size, device=args.device, compute_type=args.compute_type)
    except Exception as e:
        logging.error(f"Failed to load Whisper model: {e}")
        sys.exit(1)

    transcriptions = []
    
    print(f"Starting transcription of {len(mp3_files)} chapters...")
    for chapter_num, file_path in tqdm(mp3_files, desc="Overall Progress"):
        try:
            segments, info = model.transcribe(str(file_path), beam_size=5)
            chapter_text = []
            
            with tqdm(total=info.duration, desc=f"Chapter {chapter_num}", unit="s", leave=False) as pbar:
                prev_end = 0
                for segment in segments:
                    chapter_text.append(segment.text)
                    pbar.update(segment.end - prev_end)
                    prev_end = segment.end
                    
                pbar.update(info.duration - prev_end)
                
            full_text = "".join(chapter_text).strip()
            transcriptions.append((chapter_num, full_text))
            
        except Exception as e:
            logging.error(f"Failed to transcribe chapter {chapter_num} ({file_path.name}): {e}")
            continue

    if not transcriptions:
        logging.error("No chapters were successfully transcribed.")
        sys.exit(1)

    # Write TXT
    try:
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(f"{book_title}\n\n")
            for chapter_num, text in transcriptions:
                f.write(f"Chapter {chapter_num}\n")
                f.write(text + "\n\n")
        logging.info(f"Text file saved to {txt_path}")
    except Exception as e:
        logging.error(f"Failed to write text file: {e}", exc_info=True)

    # Write PDF
    try:
        pdf = PDF()
        pdf.add_page()
        pdf.set_font("helvetica", "B", 24)
        
        # Title Page
        sanitized_title = sanitize_text_for_pdf(book_title)
        pdf.multi_cell(0, 20, sanitized_title, align="C")
        
        for chapter_num, text in transcriptions:
            pdf.add_page()
            pdf.set_font("helvetica", "B", 16)
            pdf.multi_cell(0, 10, f"Chapter {chapter_num}", align="L")
            pdf.ln(5)
            
            pdf.set_font("helvetica", "", 12)
            sanitized_text = sanitize_text_for_pdf(text)
            pdf.multi_cell(0, 8, sanitized_text)
            
        pdf.output(str(pdf_path))
        logging.info(f"PDF saved to {pdf_path}")
    except Exception as e:
        logging.error(f"Failed to write PDF file: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
