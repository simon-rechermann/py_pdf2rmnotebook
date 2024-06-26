# py_pdf2rmnotebook
Creates a reMarkable2 rmdoc file from one or multiple PDFs having one or multipe pages. The rmdoc file can be moved to the reMarkable2 via drag and drop to the web Interface [Transferring files via web Interface](https://support.remarkable.com/s/article/Transferring-files-using-a-USB-cable) .
## General information
This project is still in development and only tested with python3.12 on ubuntu with a remarkable2 having Software verison 3.11.2.5 installed.
It should also work on windows and macOS with minor adaptions as python and java(draw2dj) are platform independent. However, I haven't tested it on other platforms so far. If you want to use it on windows raise a github issue, then I can add support for that.

**Please create a backup of your files before copying the generated rmdoc file to your reMarkable**. It should't break anything but just to be safe [How to backup your data](https://remarkable.guide/guide/access/backup.html). 

For question, improvement suggestions, bug reports etc. create a github issue.


## Setup the project on a ubuntu machine
- Install [draw2dj](https://sourceforge.net/projects/drawj2d/files/1.3.3) -> This requires java beeing installed on your machine
  [draw2dj installation](https://sourceforge.net/p/drawj2d/wiki/Home)
```bash
# Install java (jdk and jre)
# I used openjdk-21-jdk but older versions are fine as well
sudo apt install openjdk-21-jdk
# Verify that java is installed
╰─➤  java --version
openjdk 21.0.3 2024-04-16
OpenJDK Runtime Environment (build 21.0.3+9-Ubuntu-1ubuntu122.04.1)
OpenJDK 64-Bit Server VM (build 21.0.3+9-Ubuntu-1ubuntu122.04.1, mixed mode, sharing)
# Download draw2dj
# I used the debian package (drawj2d_1.3.3-4.1_all.deb), if you are on other operating systems, use the .zip file, download it, unzip it and add draw2dj to the PATH so you operating system finds it
cd ~/Downloads
sudo dkpg -i drawj2d_1.3.3-4.1_all.deb # the debian package get's installed to a location that part of the PATH so no further adjustments are necessary
# Verify the installation
╰─➤  drawj2d                                                                                                      130 ↵

            Welcome to Drawj2d
            Copyright (c) A. Vontobel, 2014-2024
            Version 1.3.3

Mode: Freehep
```

- Setup the python project
```bash
# Install python3, python3-venv and python3-pip
sudo apt install python3 python3-venv python3-pip
# Clone the repo and cd into it
git clone https://github.com/simon-rechermann/py_pdf2rmnotebook.git
cd py_pdf2rmnotebook
# Setup a python virtual environment
python3 -m venv venv
# Activate the venv. This has to be done each time you start a new shell!
source venv/bin/activate
# Install the requirements
pip install -r requirements.txt
```
## Usage
```bash
# Make sure you sourced the venv so python knows it's requirements/site-packages!
# Get help message that shows usage
python3 pdf2rmnotebook.py -h
```

## Example
I have two PDFs (document1.pdf and document2.pdf) with each of them having 3 pages stored at py_pdf2rmnotebook/pdfs.
```bash
# Execute pdf2rmnotebook.py with the two PDFs
python3 pdf2rmnotebook.py pdfs/document1.pdf pdfs/document2.pdf
```
The result is stored at py_pdf2rmnotebook/output.
To move the notebook to your reMarkable2 you have to drag and drop the file
**py_pdf2rmnotebook/output/document1.rmdoc** into the web Interface.
By default the rmdoc name and the name of the notebook that will appear on your reMarkable is the name of the first pdf you passed to the program (in this case document1).

## Limitations
The amout of pdf pages respectively the size of the rmdoc file you drag and drop is currently limited to a size of 100MB https://support.remarkable.com/s/article/Importing-files

This is approximately 16 PDF pages. Maybe this can be improved in the future by e.g. compressing the thumbnails of the pages in the created notebook.
