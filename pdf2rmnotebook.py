import os
import sys
import uuid
import argparse
import tempfile
import zipfile
import tarfile
import shutil
import json
from datetime import datetime
from pdf2image import convert_from_path
from PIL import Image

VERSION = "2.2.0"

def usage():
    print(f"""pdf2rmnotebook: {VERSION}
Usage:
  pdf2rmnotebook [options] file.pdf [...]

Create multi-page reMarkable Notebook file from PDF files
  * Creates .zip files by default for use with rmapi
  * Use -r option to create a reMarkable Notebook .rmn file for use with RCU
  * Use -d option to create a reMarkable Document .rmdoc file

Options:
  -h    Display this help and exit
  -q    Produce fewer messages to stdout
  -r    Create a reMarkable Notebook .rmn file (default: zip)
  -d    Create a reMarkable Document .rmdoc file
  -v    Produce more messages to stdout
  -V    Display version information and exit
  -n NAME    Set the rmn Notebook Display Name (default: Notebook-<yyyymmdd_hhmm.ss>)
             Only used with -r option
  -o FILE    Set the output filename (default: Notebook-<yyyymmdd_hhmm.ss>.zip)
  -s SCALE   Set the scale value (default: 0.75) - 0.75 is a good value for A4/Letter PDFs

Example:
  pdf2rmnotebook -n "My Notebook" -o mynotebook.zip -s 1.0 file.pdf
""")
    sys.exit(1)

def create_notebook_from_pdf(pdf_path, output_path, scale, verbose, create_rmn, create_rmdoc, display_name):
    temp_dir = tempfile.mkdtemp()
    notebook_dir = os.path.join(temp_dir, "Notebook")
    os.makedirs(notebook_dir)

    notebook_uuid = str(uuid.uuid4())
    notebook_subdir = os.path.join(notebook_dir, notebook_uuid)
    os.makedirs(notebook_subdir)

    images = convert_from_path(pdf_path)
    page_uuids = []

    for page_num, img in enumerate(images):
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.Resampling.LANCZOS)
        page_uuid = str(uuid.uuid4())
        img_path = os.path.join(notebook_subdir, f"{page_uuid}.rm")
        img.save(img_path, "PNG")
        create_page_metadata(notebook_subdir, page_uuid)
        page_uuids.append(page_uuid)

    if create_rmn:
        create_rmn_file(notebook_dir, notebook_uuid, display_name, output_path, verbose, page_uuids)
    elif create_rmdoc:
        create_rmdoc_file(notebook_dir, notebook_uuid, display_name, output_path, verbose, page_uuids)
    else:
        create_zip_file(notebook_dir, output_path, verbose)

    shutil.rmtree(temp_dir)
    if verbose:
        print(f"Output written to {output_path}")

def create_page_metadata(directory, page_uuid):
    metadata = {
        "layers": [
            {
                "name": "Layer 1",
                "annotations": []
            }
        ],
        "dimensions": {
            "height": 1404,
            "width": 1872
        }
    }
    with open(os.path.join(directory, f"{page_uuid}-metadata.json"), 'w') as metadata_file:
        json.dump(metadata, metadata_file)

def create_zip_file(notebook_dir, output_path, verbose):
    with zipfile.ZipFile(output_path, 'w') as notebook_zip:
        for root, _, files in os.walk(notebook_dir):
            for file in files:
                file_path = os.path.join(root, file)
                notebook_zip.write(file_path, os.path.relpath(file_path, notebook_dir))

def create_rmn_file(notebook_dir, notebook_uuid, display_name, output_path, verbose, page_uuids):
    content = []
    for page_uuid in page_uuids:
        content.append({"type": "page", "parent": notebook_uuid, "id": page_uuid})
    notebook_metadata = {
        "visibleName": display_name or f"Notebook-{datetime.now().strftime('%Y%m%d_%H%M.%S')}",
        "lastOpenedPage": 0,
        "type": "DocumentType",
        "version": 1
    }
    with open(os.path.join(notebook_dir, f"{notebook_uuid}.content"), 'w') as content_file:
        json.dump(content, content_file)
    with open(os.path.join(notebook_dir, f"{notebook_uuid}.metadata"), 'w') as metadata_file:
        json.dump(notebook_metadata, metadata_file)

    with tarfile.open(output_path, "w") as tar:
        tar.add(notebook_dir, arcname=os.path.basename(notebook_dir))

def create_rmdoc_file(notebook_dir, notebook_uuid, display_name, output_path, verbose, page_uuids):
    document_metadata = {
        "visibleName": display_name or f"Document-{datetime.now().strftime('%Y%m%d_%H%M.%S')}",
        "lastOpenedPage": 0,
        "type": "DocumentType",
        "version": 1
    }
    content = []
    for page_uuid in page_uuids:
        content.append({"type": "page", "parent": notebook_uuid, "id": page_uuid})
    with open(os.path.join(notebook_dir, f"{notebook_uuid}.content"), 'w') as content_file:
        json.dump(content, content_file)
    with open(os.path.join(notebook_dir, f"{notebook_uuid}.metadata"), 'w') as metadata_file:
        json.dump(document_metadata, metadata_file)

    with zipfile.ZipFile(output_path, 'w') as rmdoc_zip:
        for root, _, files in os.walk(notebook_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rmdoc_zip.write(file_path, os.path.relpath(file_path, notebook_dir))

def main():
    parser = argparse.ArgumentParser(description="Build multi-page reMarkable Notebook from PDF Files")
    parser.add_argument('-q', action='store_true', help='Produce fewer messages to stdout')
    parser.add_argument('-r', action='store_true', help='Create a reMarkable Notebook .rmn file (default: zip)')
    parser.add_argument('-d', action='store_true', help='Create a reMarkable Document .rmdoc file')
    parser.add_argument('-v', action='store_true', help='Produce more messages to stdout')
    parser.add_argument('-V', action='store_true', help='Display version information and exit')
    parser.add_argument('-n', type=str, help='Set the rmn Notebook Display Name')
    parser.add_argument('-o', type=str, help='Set the output filename')
    parser.add_argument('-s', type=float, default=0.75, help='Set the scale value (default: 0.75)')
    parser.add_argument('files', nargs='+', help='PDF files to convert')

    args = parser.parse_args()

    if args.V:
        print(f"pdf2rmnotebook: {VERSION}")
        sys.exit(0)

    out_file_type = "zip"
    if args.r:
        out_file_type = "rmn"
    elif args.d:
        out_file_type = "rmdoc"

    output_file = args.o if args.o else f"Notebook-{datetime.now().strftime('%Y%m%d_%H%M.%S')}.{out_file_type}"
    scale = args.s
    verbose = args.v

    for pdf_file in args.files:
        if verbose:
            print(f"Working on file: {pdf_file}")
        if not os.path.isfile(pdf_file):
            print(f"{pdf_file}: No such file or directory.")
            usage()
        create_notebook_from_pdf(pdf_file, output_file, scale, verbose, args.r, args.d, args.n)

if __name__ == "__main__":
    main()
