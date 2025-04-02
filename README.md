# NAATOS_OCT_ANALYSIS
NAATOS Analysis of data from Thorlabs OCT system

## Overview
This is no actual program or application, but a collection of python libraries and analysis scripts to work with OCT Data for Thorlabs for the purpose of analyzing NAATOS wax valves.

<ol start="1">
<li>Python Environment Setup</li>

1. Use miniconda (or conda or miniforger)

2. Setup environment using the environment.yml file

    To Create: `conda env create --name naatos_oct --file environment.yml`

    To Update: `conda env update --name naatos_oct --file environment.yml --prune`

<li>Libraries</li>

* The "naatos_oct_tools" folder is intended to be an importable module

<li>Recommended IDE/environment</li>

* Simon has started liking VScode (point it to this folder)

<li>Codes / Notebooks</li>

* Cell-based codes or notebooks from Simon are in sandbox_sg

* You can create your own sandbox folder

<li>Conventions</li>

* Any updates to the libraries/modules (i.e., the `naatos_oct_tools` folder) should be kept backards compatible

<li>Data Storage</li>

* We are storing raw data from oct system here:

        \\file.corp.ghlabs.org\Shared\Projects\NAATOS\V1\NAATOS_OCT_WORK\OCTExport

</ol>

## Important Other Utilities And Python Libraries

### Apps/Utilities
* Fiji / ImageJ (https://fiji.sc/)
* 3D Slicer (https://www.slicer.org/)

### Python Libraries
* Pyvista (VTK Interface)
    * https://pyvista.org/
* Vedo (another VTK Interface)
    * https://vedo.embl.es/
* Simple ITK (3D volume manipulation and processing)
    * https://simpleitk.org/

## OCT System
* Ours is "Telesto" model
* Thorlabs User Manual (Describeds .OCT format)
    * https://www.thorlabs.com/thorcat/GAN111/DOC-101131.pdf
