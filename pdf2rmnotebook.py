import os
import sys
import uuid
import argparse
import tempfile
from PyPDF2 import PdfReader, PdfWriter
import zipfile
from datetime import datetime
import subprocess
from jinja2 import  Environment, FileSystemLoader
from pathlib import Path
from pdf2image import convert_from_path

OUTPUT_TEMP = "output/temp"

def usage():
    print(f"""py_pdf2rmnotebook
Usage:
  pdf2rmnotebook [options] file.pdf [...]

Create multi-page reMarkable Notebook file from PDF files
  * Creates .zip files by default for use with rmapi
  * Use -r option to create a reMarkable Notebook .rmn file for use with RCU
  * Use -d option to create a reMarkable Document .rmdoc file

Options:
  -h    Display this help and exit
  -n NAME    Set the rmn Notebook Display Name (default: Notebook-<yyyymmdd_hhmm.ss>)
             Only used with -r option
  -o FILE    Set the output filename (default: Notebook-<yyyymmdd_hhmm.ss>.zip)
  -s SCALE   Set the scale value (default: 0.75) - 0.75 is a good value for A4/Letter PDFs

Example:
  pdf2rmnotebook -n "My Notebook" -o mynotebook.zip -s 1.0 file.pdf
""")
    sys.exit(1)

def create_single_rm_file_from_single_pdf(pdf_path, out_file_path, scale=0.7):
    # echo image aliasing.pdf 0 0 0 0.7 | drawj2d -Trmdoc
    drawj2d_cmd = f"echo image {pdf_path} 0 0 0 {scale} | drawj2d -Trmdoc -o {out_file_path}"
    process = subprocess.run(drawj2d_cmd, shell=True, text=True, capture_output=True) #cwd=out_file_path)
    if process.returncode == 0:
        print("Command executed successfully!")
        print("Output:\n", process.stdout)
    else:
        raise RuntimeError(f"Error in drawj2d call:\n{process.stderr}")

def create_thumbnail(pdf_path, out_file_path):
    # Convert the first page of the PDF to an image
    images = convert_from_path(pdf_path, first_page=0, last_page=1)
    
    if images:
        # Save the first page as a PNG file
        images[0].save(out_file_path, 'PNG')
        print(f"Thumbnail created: {out_file_path}")
    else:
        print(f"Failed to create thumbnail for: {pdf_path}")


def create_rmdoc_file(notebook_dir, output_path):
    with zipfile.ZipFile(output_path, 'w') as rmdoc_zip:
        for root, _, files in os.walk(notebook_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rmdoc_zip.write(file_path, os.path.relpath(file_path, notebook_dir))

def create_metadata(directory, page_uuid, visible_name):
    _create_content_file()
    _create_local_file()
    _create_metadata_file()
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('template.metadata.j2')

    rendered_template = template.render({"visibleName": visible_name})
        
    with open(os.path.join(directory, f"{page_uuid}.metadata"), 'w') as metadata_file:
        metadata_file.write(rendered_template)


def _create_content_file():
    pass

def _create_local_file():
    pass

def _create_metadata_file():
    pass



def split_pdf_pages(source_pdf_path):
    # Create a PDF reader object
    reader = PdfReader(source_pdf_path)
    num_pages = len(reader.pages)
    
    # Make sure the output folder exists
    if not os.path.exists(OUTPUT_TEMP):
        os.makedirs(OUTPUT_TEMP)

    output_paths = []  # Initialize a list to store output file paths

    # Split each page into a separate PDF
    for i in range(num_pages):
        writer = PdfWriter()
        writer.add_page(reader.pages[i])

        output_filename = f"page_{i + 1}.pdf"
        output_path = os.path.join(OUTPUT_TEMP, output_filename)
        
        # Write out the new PDF
        with open(output_path, 'wb') as output_pdf:
            writer.write(output_pdf)
        
        print(f"Created: {output_path}")
        output_paths.append(output_path)  # Append the path to the list

    return output_paths  # Return the list of created PDF file paths

def main():
    parser = argparse.ArgumentParser(description="Build multi-page reMarkable Notebook rmdoc file from PDF file")
    parser.add_argument('-v', action='store_true', help='Produce more messages to stdout')
    parser.add_argument('-n', type=str, help='Set the rmdoc Notebook Display Name')
    parser.add_argument('-o', type=str, help='Set the output filename')
    parser.add_argument('-s', type=float, default=0.75, help='Set the scale value (default: 0.75)')
    parser.add_argument('files', nargs='+', help='PDF files to convert')

    args = parser.parse_args()
    scale = args.s
    rmdoc_folder_name = args.o if args.o else f"Notebook-{datetime.now().strftime('%Y%m%d_%H%M.%S')}"

    out_file_folder = "output"
    rmdoc_folder = Path(out_file_folder) / rmdoc_folder_name
    rmdoc_uuid = str(uuid.uuid4())
    rm_files_folder = rmdoc_folder / rmdoc_uuid
    thumbnails_folder = Path(str(rm_files_folder) + ".thumbnails")
    if not os.path.exists(rm_files_folder):
        os.makedirs(rm_files_folder)
    if not os.path.exists(thumbnails_folder):
        os.makedirs(thumbnails_folder)

    rm_files = []
    for pdf_file in args.files:
        print(f"Working on file: {pdf_file}")
        if not os.path.isfile(pdf_file):
            print(f"{pdf_file}: No such file or directory.")
            usage()
        pdf_pages = split_pdf_pages(pdf_file)  # Get the list of pages
        for pdf_page in pdf_pages:  # Iterate over each page
            page_uuid = uuid.uuid4()
            rm_out_file_name = f"{page_uuid}.rm"
            thumbnail_out_file_name = f"{page_uuid}.png"
            rm_files.append(rm_files)
            rm_out_file_path = rm_files_folder / rm_out_file_name
            thumbnail_out_file_path = thumbnails_folder / thumbnail_out_file_name
            create_single_rm_file_from_single_pdf(pdf_page, rm_out_file_path, scale)
            create_thumbnail(pdf_page, thumbnail_out_file_path)
    create_metadata(rmdoc_folder, rm_files)
    rmdoc_file_name = Path(str(rmdoc_folder) + ".rmdoc")
    create_rmdoc_file(rmdoc_file_name)

if __name__ == "__main__":
    main()
