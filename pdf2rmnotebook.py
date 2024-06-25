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
import time

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
    drawj2d_cmd = f"echo image {pdf_path} 0 0 0 {scale} | drawj2d -Trm -o {out_file_path}"
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


def create_rmdoc_file(rmdoc_files_folder, rmdoc_file_name):
    with zipfile.ZipFile(rmdoc_file_name, 'w') as rmdoc_zip:
        for root, _, files in os.walk(rmdoc_files_folder):
            for file in files:
                file_path = os.path.join(root, file)
                rmdoc_zip.write(file_path, os.path.relpath(file_path, rmdoc_files_folder))


def create_metadata(output_path, rmdoc_uuid, page_uuids, notebook_name):
    env = Environment(loader=FileSystemLoader('templates'))
    _create_local_file(output_path, env, rmdoc_uuid)
    _create_metadata_file(output_path, env, rmdoc_uuid, notebook_name)
    _create_content_file(output_path, env, rmdoc_uuid, page_uuids)



def _create_local_file(output_path, env, rmdoc_uuid):
    template = env.get_template('template.local.j2')
    rendered_template = template.render({"contentFormatVersion": 2})
    with open(os.path.join(output_path, f"{rmdoc_uuid}.local"), 'w') as local_file:
        local_file.write(rendered_template)

def _create_metadata_file(output_path, env, rmdoc_uuid, notebook_name):
    template = env.get_template('template.metadata.j2')
    current_unix_millies = _get_current_unix_time_millis()
    rendered_template = template.render(
        {
        "visibleName": notebook_name, 
        "current_unix_time_milliseconds": current_unix_millies
        }
    )
    with open(os.path.join(output_path, f"{rmdoc_uuid}.metadata"), 'w') as metadata_file:
        metadata_file.write(rendered_template)

def _get_current_unix_time_millis():
    current_time_seconds = time.time()
    return int(current_time_seconds * 1000)

def _create_content_file(output_path, env, rmdoc_uuid, page_uuids):
    template = env.get_template('template.content.j2')
    page_uuids_and_values = _get_page_uuids_and_values(page_uuids)
    size_in_bytes = _get_size_in_bytes()
    # page_uuids_and_values = [
    #     {"uuid": "first_page_uuid", "value": "ba"},
    #     {"uuid": "second_page_uuid", "value": "bb"},
    #     # ...
    # ]
    rendered_template = template.render(
        {
            "page_uuids_and_values": page_uuids_and_values,
            "size_in_bytes": size_in_bytes,
            "page_count": len(page_uuids)
        }
    )
    with open(os.path.join(output_path, f"{rmdoc_uuid}.content"), 'w') as metadata_file:
        metadata_file.write(rendered_template)

def _get_page_uuids_and_values(page_uuids):
    # TODO: What happens and should happen after 'z' so by -> bz -> b?
    page_uuids_and_values = []
    for idx, page_uuid in enumerate(page_uuids):
        # Convert index to lowercase letters starting from 'a'
        letter = chr(97 + idx)
        page_uuids_and_values.append(
            {"uuid": str(page_uuid), "value": f"b{letter}"}
        )
    return page_uuids_and_values

def _get_size_in_bytes():
    # TODO: get real size
    return 0  


def split_pdf_pages(pdf_files):
    output_paths = []  # Initialize a list to store output file paths
    total_num_pages = 0
    for pdf_file in pdf_files:
        print(f"Working on file: {pdf_file}")
        if not os.path.isfile(pdf_file):
            print(f"{pdf_file}: No such file or irectory.")
        # Create a PDF reader object
        reader = PdfReader(pdf_file)
        num_pages_single_pdf = len(reader.pages)

        # Make sure the output folder exists
        if not os.path.exists(OUTPUT_TEMP):
            os.makedirs(OUTPUT_TEMP)


        # Split each page into a separate PDF
        for i in range(num_pages_single_pdf):
            writer = PdfWriter()
            writer.add_page(reader.pages[i])

            output_filename = f"page_{total_num_pages + i + 1}.pdf"
            output_path = os.path.join(OUTPUT_TEMP, output_filename)
            
            # Write out the new PDF
            with open(output_path, 'wb') as output_pdf:
                writer.write(output_pdf)
            
            print(f"Created: {output_path}")
            output_paths.append(output_path)  # Append the path to the list
        total_num_pages += num_pages_single_pdf

    return output_paths  # Return the list of created PDF file paths

def main():
    parser = argparse.ArgumentParser(description="Build multi-page reMarkable Notebook rmdoc file from PDF file")
    parser.add_argument('-v', action='store_true', help='Produce more messages to stdout')
    parser.add_argument('-n', type=str, help='Set the rmdoc Notebook Display Name')
    parser.add_argument('-o', type=str, help='Set the output filename, default is the pdf name of the first passed pdf')
    parser.add_argument('-s', type=float, default=0.75, help='Set the scale value (default: 0.75)')
    parser.add_argument('files', nargs='+', help='PDF files to convert')

    args = parser.parse_args()
    scale = args.s
    notebook_name = args.o if args.o else f"Notebook-{datetime.now().strftime('%Y%m%d_%H%M.%S')}"

    out_file_folder = Path("output")
    rmdoc_files_folder = out_file_folder / notebook_name
    rmdoc_uuid = str(uuid.uuid4())
    rm_files_folder = rmdoc_files_folder / rmdoc_uuid
    thumbnails_folder = Path(str(rm_files_folder) + ".thumbnails")
    if not os.path.exists(rm_files_folder):
        os.makedirs(rm_files_folder)
    if not os.path.exists(thumbnails_folder):
        os.makedirs(thumbnails_folder)

    page_uuids = []
    # Get the list of single pdf pages from one or multiple pdf files
    pdf_pages = split_pdf_pages(args.files)
    for pdf_page in pdf_pages:
        page_uuid = uuid.uuid4()
        rm_out_file_name = f"{page_uuid}.rm"
        thumbnail_out_file_name = f"{page_uuid}.png"
        page_uuids.append(page_uuid)
        rm_out_file_path = rm_files_folder / rm_out_file_name
        thumbnail_out_file_path = thumbnails_folder / thumbnail_out_file_name
        create_single_rm_file_from_single_pdf(pdf_page, rm_out_file_path, scale)
        create_thumbnail(pdf_page, thumbnail_out_file_path)
    create_metadata(rmdoc_files_folder, rmdoc_uuid, page_uuids, notebook_name)
    rmdoc_file_name = str(rmdoc_files_folder) + ".rmdoc"
    create_rmdoc_file(rmdoc_files_folder, rmdoc_file_name)

if __name__ == "__main__":
    main()
