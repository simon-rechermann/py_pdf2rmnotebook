# General information
This project is still in development and only tests with with python3.12 on ubuntu with a remarkable2 having Software verison 3.11.2.5 installed.
For question, improvement suggestions, bug reports etc. create a github issue.

# Setup the project on a linux machine
- Install [draw2dj](https://sourceforge.net/projects/drawj2d) -> This requires java beeing installed on your machine
- Setup the python project
```bash
# Install python3, python3-venv and python3-pip
sudo apt install python3 python3-venv python3-pip
# Clone the repo and cd into it
git clone ...
cd pdfs_for_remarkable
# Setup a python virtual environment
python3 -m venv venv
# Activate the venv. This has to be done each time you start a new shell!
source venv/bin/activate
# Install the requirements
pip install -r requirements.txt
```
# Usage
```bash
# Make sure you sourced the venv so python knows it's requirements
python3 pdf2rmnotebook.py
```
