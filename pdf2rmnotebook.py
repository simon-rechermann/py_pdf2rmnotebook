import os
import sys
import uuid
import argparse
from PyPDF2 import PdfReader, PdfWriter
import zipfile
import subprocess
from jinja2 import  Environment, FileSystemLoader
from pathlib import Path
from pdf2image import convert_from_path
import time
import logging
from termcolor import colored


class ColorizingStreamHandler(logging.StreamHandler):
    # Define a method to colorize messages based on log level
    def colorize_log(self, record):
        if record.levelno >= logging.CRITICAL:
            return colored(record.msg, 'red', attrs=['bold'])
        elif record.levelno >= logging.ERROR:
            return colored(record.msg, 'red')
        elif record.levelno >= logging.WARNING:
            return colored(record.msg, 'yellow')
        else:
            return record.msg  # Default no color for INFO and lower levels

    def emit(self, record):
        # Use the custom colorizing function
        record.msg = self.colorize_log(record)
        # Format the message
        message = self.format(record)
        # Stream the message
        self.stream.write(message + self.terminator)
        self.flush()

# Setup logging configuration
logging.basicConfig(level=logging.INFO, handlers=[ColorizingStreamHandler()], format='%(levelname)s: %(message)s' )

# Create logger
logger = logging.getLogger()

OUTPUT_TEMP = "output/temp"


def create_single_rm_file_from_single_pdf(pdf_path, out_file_path, scale):
    # echo image aliasing.pdf 0 0 0 0.7 | drawj2d -Trmdoc
    drawj2d_cmd = f"echo image {pdf_path} 0 0 0 {scale} | drawj2d -Trm -o {out_file_path}"
    process = subprocess.run(drawj2d_cmd, shell=True, text=True, capture_output=True) #cwd=out_file_path)
    if process.returncode == 0:
        logger.debug("drawj2d_cmd command executed successfully!")
        logger.debug(f"Output:\n {process.stdout}")
    else:
        logger.error(f"Error in drawj2d call:\n{process.stderr}")
        sys.exit()

def create_thumbnail(pdf_path, out_file_path):
    # Convert the first page of the PDF to an image
    images = convert_from_path(pdf_path, first_page=0, last_page=1)
    
    if images:
        # Save the first page as a PNG file
        images[0].save(out_file_path, 'PNG')
        logger.debug(f"Thumbnail created: {out_file_path}")
    else:
        logger.error(f"Failed to create thumbnail for: {pdf_path}")


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
    # After 'bz' we continue with 'ca'
    page_uuids_and_values = []
    for idx, page_uuid in enumerate(page_uuids):
        # Calculate the first letter
        first_letter_idx = idx // 26  # Dividing by 26 to shift to the next letter after 26 entries
        second_letter_idx = idx % 26  # Remainder will give the second letter index

        # Convert index to lowercase letters, first_letter starting from 'b' (98 in ASCII)
        first_letter = chr(98 + first_letter_idx)
        second_letter = chr(97 + second_letter_idx)

        page_uuids_and_values.append(
            {"uuid": str(page_uuid), "value": f"{first_letter}{second_letter}"}
        )
    return page_uuids_and_values

def _get_size_in_bytes():
    # TODO: get real size
    return 0


def split_pdf_pages(pdf_files):
    output_paths = []  # Initialize a list to store output file paths
    total_num_pages = 0
    for pdf_file in pdf_files:
        logger.info(f"Working on file: {pdf_file}")
        if not os.path.isfile(pdf_file):
            logger.error(f"{pdf_file}: No such file or directory.")
            sys.exit()
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
            
            logger.info(f"Created: {output_path}")
            output_paths.append(output_path)  # Append the path to the list
        total_num_pages += num_pages_single_pdf

    return output_paths  # Return the list of created PDF file paths

def check_size(file_path):
    # Constant for the maximum file size (100MB) supported by the remarkable web Interface
    MAX_SIZE_BYTES = 100 * 1024 * 1024  # 100MB in bytes
    TEN_MB_BYTES = 10 * 1024 * 1024  # 10MB in bytes
    
    # Check if the file exists
    if not os.path.exists(file_path):
        logger.error("File does not exist.")
        sys.exit()
    
    # Get the size of the file
    file_size = os.path.getsize(file_path)
    
    # Check if the file size is greater than the limit
    if file_size > MAX_SIZE_BYTES:
        logger.error(f'The file size is {file_size / (1024 * 1024):.2f} MB, which is greater than the allowed 100 MB. File transfer via the Web Interface will not work')
    elif file_size >= MAX_SIZE_BYTES - TEN_MB_BYTES:
        logger.warning(f'The file size is {file_size / (1024 * 1024):.2f} MB, which is close to the limit of 100MB. File transfer via the Web Interface might not work')
    else:
        logger.info(f'The file size is {file_size / (1024 * 1024):.2f} MB, which is within the limit.')


def main():
    parser = argparse.ArgumentParser(description="Build multi-page reMarkable Notebook rmdoc file from PDF file")
    parser.add_argument('-v', action='store_true', help='Produce more messages to stdout')
    parser.add_argument('-o', type=str, help='Set the output filename (default: pdf name of the first passed pdf_file')
    parser.add_argument('-s', type=float, default=0.75, help='Set the scale value (default: 0.75)')
    parser.add_argument('pdf_file', nargs='+', help='PDF file/files to convert')

    args = parser.parse_args()
    scale = args.s
    if args.v:
        logger.setLevel(logging.DEBUG)

    # Use name of the first pdf as name of the notebook
    file_path = Path(args.pdf_file[0])
    # Remove file extension and get rid of whitespace in file names
    notebook_name = args.o if args.o else file_path.name.strip(".pdf").replace(" ", "")

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
    pdf_pages = split_pdf_pages(args.pdf_file)
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
    check_size(rmdoc_file_name)

if __name__ == "__main__":
    main()
