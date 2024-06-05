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

def create_single_rm_file_from_single_pdf(pdf_path, out_file_path, outfile_name, scale=0.7):
    # echo image aliasing.pdf 0 0 0 0.7 | drawj2d -Trmdoc
    drawj2d_cmd = f"echo image {pdf_path} 0 0 0 {scale} | drawj2d -Trmdoc -o {outfile_name}"
    process = subprocess.run(drawj2d_cmd, shell=True, text=True, capture_output=True, cwd=out_file_path)
    if process.returncode == 0:
        print("Command executed successfully!")
        print("Output:\n", process.stdout)
    else:
        raise RuntimeError(f"Error in drawj2d call:\n{process.stderr}")

def create_rmdoc_file(notebook_dir, output_path):
    with zipfile.ZipFile(output_path, 'w') as rmdoc_zip:
        for root, _, files in os.walk(notebook_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rmdoc_zip.write(file_path, os.path.relpath(file_path, notebook_dir))

def create_metadata(directory, page_uuid, visible_name):
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('template.metadata.j2')

    rendered_template = template.render({"visibleName": visible_name})
        
    with open(os.path.join(directory, f"{page_uuid}.metadata"), 'w') as metadata_file:
        metadata_file.write(rendered_template)




def split_pdf_pages(source_pdf_path):
    # Create a PDF reader object
    reader = PdfReader(source_pdf_path)
    num_pages = len(reader.pages)
    
    # Make sure the output folder exists
    if not os.path.exists(OUTPUT_TEMP):
        os.makedirs(OUTPUT_TEMP)

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

    return OUTPUT_TEMP

def main():
    parser = argparse.ArgumentParser(description="Build multi-page reMarkable Notebook rmdoc file from PDF file")
    parser.add_argument('-v', action='store_true', help='Produce more messages to stdout')
    parser.add_argument('-n', type=str, help='Set the rmdoc Notebook Display Name')
    parser.add_argument('-o', type=str, help='Set the output filename')
    parser.add_argument('-s', type=float, default=0.75, help='Set the scale value (default: 0.75)')
    parser.add_argument('files', nargs='+', help='PDF files to convert')

    args = parser.parse_args()

    rmdoc_file_name = args.o if args.o else f"Notebook-{datetime.now().strftime('%Y%m%d_%H%M.%S')}.rmdoc"
    out_file_path = "output"
    uuid_filename = uuid.uuid4()
    out_file_name = f"{uuid_filename}.rm"
    scale = args.s

    for pdf_file in args.files:
        print(f"Working on file: {pdf_file}")
        if not os.path.isfile(pdf_file):
            print(f"{pdf_file}: No such file or directory.")
            usage()
        for pdf_page in split_pdf_pages(pdf_file):
            create_single_rm_file_from_single_pdf(pdf_file, out_file_path, uuid, scale)
    create_metadata()
    create_rmdoc_file()

if __name__ == "__main__":
    main()
