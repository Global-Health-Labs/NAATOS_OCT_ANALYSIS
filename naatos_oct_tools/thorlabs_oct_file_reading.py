from pathlib import Path
import json
import configparser
import pprint
import time
import pprint
pp = pprint.PrettyPrinter(indent=4);
from dataclasses import dataclass

# pip install slicerio
import slicerio.server

# packages for 3d
#   # for OCT 3D stuff and using in jupyter
#   - trame-jupyter-extension
#   - trame
#   - trame-vtk
#   - trame-vuetify
#   - ipywidgets
#   - simpleitk
import numpy as np
import pandas as pd

import pyvista as pv
from PIL import Image
import SimpleITK as sitk

from zipfile import ZipFile
import xml.etree.ElementTree as ET




# helper to deal with XML reading
class GeeElem(object):
    """Wrapper around an ElementTree element. a['foo'] gets the
       attribute foo, a.foo gets the first subelement foo."""
    def __init__(self, elem):
        self.etElem = elem

    def __getitem__(self, name):
        res = self._getattr(name)
        if res is None:
            raise(AttributeError, "No attribute named '%s'" % name)
        return res

    def __getattr__(self, name):
        res = self._getelem(name)
        if res is None:
            raise(IndexError, "No element named '%s'" % name)
        return res

    def _getelem(self, name):
        res = self.etElem.find(name)
        if res is None:
            return None
        return GeeElem(res)

    def _getattr(self, name):
        return self.etElem.get(name)

class GeeTree(object):
    "Wrapper around an ElementTree."
    def __init__(self, fname):
        self.doc = ET.parse(fname)

    def __getattr__(self, name):
        if self.doc.getroot().tag != name:
            raise(IndexError, "No element named '%s'" % name)
        return GeeElem(self.doc.getroot())

    def getroot(self):
        return self.doc.getroot()
    





@dataclass
class OctFile:
    """Class for returning read-in information from a 3D .OCT file"""
    pvvol: pv.ImageData
    sitkvol: sitk.Image
    scalars: np.ndarray
    image: Image
    cfg_oct_xml: object
    cfg_oct_probe : dict

######
######
def _read_oct(file_oct,make_pv_volume=False,make_sitk_volume=False):
    # per thorlabs documentation, .oct files are just .zip files
    zip_file_path = file_oct;

    with ZipFile(zip_file_path, 'r') as zf:
        # for zf_file in zf.filelist:
        #     print(zf_file)
        
        # open and read Probe.ini file
        with zf.open('data/Probe.ini') as file:
            content = file.read().decode('utf-8')
            configprobe = configparser.ConfigParser();
            configprobe.read_string('[probe]\n'+content)
            cfg_oct_probe = {k:dict(v) for k,v in configprobe.items()};
            cfg_oct_probe = cfg_oct_probe['probe'];

        # open and read Header.xml file
        with zf.open('Header.xml') as file:
            cfg_oct_xml = GeeTree(file);
        
        # open and read the videoimage image
        cam_img_attribs = [e.attrib for e in cfg_oct_xml.Ocity.DataFiles.etElem if e.text=='data\\VideoImage.data'][0];
        with zf.open('data/VideoImage.data','r') as file:
            videodata = np.frombuffer(file.read(),dtype=np.uint8)
        videodata = videodata.reshape((
            int(cam_img_attribs['SizeX']),
            int(cam_img_attribs['SizeZ']),
            int(cam_img_attribs['BytesPerPixel']),
        ))
        # re-arrange to RGBA (Thorlabs format is BGRA)
        videodata = videodata[:,:,[2,1,0,3]]


        # open and parse the data/Intensity.data into a PyVista / VTK Image Data volume
        vol_img_attribs = [e.attrib for e in cfg_oct_xml.Ocity.DataFiles.etElem if e.text=='data\\Intensity.data'][0];
        vol_dimensions = (
            int(cfg_oct_xml.Ocity.Image.SizePixel.etElem[0].text),
            int(cfg_oct_xml.Ocity.Image.SizePixel.etElem[1].text),
            int(cfg_oct_xml.Ocity.Image.SizePixel.etElem[2].text),
        );
        vol_spacing_mm = (
            float(cfg_oct_xml.Ocity.Image.PixelSpacing.etElem[0].text),
            float(cfg_oct_xml.Ocity.Image.PixelSpacing.etElem[1].text),
            float(cfg_oct_xml.Ocity.Image.PixelSpacing.etElem[2].text),
        );
        with zf.open('data/Intensity.data','r') as file:
            scalars = np.frombuffer(file.read(),dtype=np.float32)

    print('Image Dims:{:s} PixelSpacing[mm]:{:s}'.format(str(vol_dimensions),str(vol_spacing_mm)))

    # make pyvista vtk volume image
    if(make_pv_volume):
        pvvol = pv.ImageData(dimensions=vol_dimensions,spacing=vol_spacing_mm);
        pvvol['OCTintensity'] = scalars;
    else:
        pvvol = None;
    
    # make simpleitk volume image
    if(make_sitk_volume):
        sitkvol = sitk.GetImageFromArray( scalars.reshape(vol_dimensions,order='F').transpose((2,1,0)) , isVector=False); # sitk uses opposite indexing
        sitkvol.SetSpacing(vol_spacing_mm);
    else:
        sitkvol = None;

    # make a PILLOW image from camera data
    newimg = Image.fromarray(videodata,mode='RGBA');

    return OctFile(
        pvvol = pvvol,
        sitkvol = sitkvol,
        scalars = scalars,
        image = newimg,
        cfg_oct_xml = cfg_oct_xml,
        cfg_oct_probe = cfg_oct_probe,
    );


class OCT_Study_Folder():
    
    def __init__(self, study_name : str, folder_octexport_root : Path = None):
        """_summary_
        Load OCT Study Information

        Args:
            study_name (str): _description_ Folder name of the study, in the root
            folder_octexport_root (Path, optional): _description_. Defaults to None.

        Raises:
            RuntimeError: _description_
        """
        if(folder_octexport_root is None):
            #folder_octexport_root = Path(r'\\file.corp.ghlabs.org\Shared\Projects\NAATOS\V1\NAATOS_OCT_WORK\OCTExport')
            folder_octexport_root = Path(r'D:\SGProjects\NAATOS\OCTlocal')
        
        folder_study = folder_octexport_root/study_name;
        folder_study_processed = folder_study/'processed';
        if not folder_study.exists:
            raise RuntimeError("Study not found")

        study_info = dict(
            study_has_yat_log = len(list(folder_study.glob('YAT*.log')))>0,
            study_num_oct_files = len(list(folder_study.glob('{:s}*.oct'.format(study_name)))),
            study_num_vtk_files = len(list(folder_study.glob('{:s}*.vtk'.format(study_name)))),
            study_num_jpg_files = len(list(folder_study.glob('{:s}*.jpg'.format(study_name)))),
            study_has_an_ini_file = len(list(folder_study.glob('{:s}*.ini'.format(study_name))))>0,
            study_has_json_info_file = len(list(folder_study.glob('info.json'.format(study_name))))>0,
        );
        print('STUDY:',study_name)
        pp.pprint(study_info);

        self.study_info = study_info;
        self.folder_octexport_root = folder_octexport_root;
        self.folder_study = folder_study;
        self.folder_study_processed = folder_study_processed;
        self.name = study_name;
        self.octdatalist = [];
    
    def __repr__(self):
        description_string=f"""<OCT_Study_Folder Object>
{self.name} in folder {self.folder_octexport_root.as_posix()}
""";
        description_string+=pp.pformat(self.study_info);
        return description_string;

    ###==== CLASS PROPERTIES
    # def get_has_yat_log(self):
        #     return self.study_info['study_has_yat_log'];
        # has_yat_log = property(get_has_yat_log);
    @property
    def has_yat_log(self):
        return self.study_info['study_has_yat_log'];

    @property
    def has_an_ini_file(self):
        return self.study_info['study_has_an_ini_file'];

    @property
    def has_json_info_file(self):
        return self.study_info['has_json_info_file'];

    @property
    def num_jpg_files(self):
        return self.study_info['study_num_jpg_files'];

    @property
    def num_oct_files(self):
        return self.study_info['study_num_oct_files'];

    @property
    def num_vtk_files(self):
        return self.study_info['study_num_vtk_files'];

    ###==== METHODS
    def load_all_octs(self,make_sitk_volume=False,make_pv_volume=False):
        self.octdatalist = [];
        if(self.num_oct_files>=1):
            octfiles = list(self.folder_study.glob('{:s}*.oct'.format(self.name)))
            for octfile in octfiles:
                octdata = _read_oct(octfile,make_sitk_volume=make_sitk_volume,make_pv_volume=make_pv_volume);
                self.octdatalist.append(octdata);

    def pv_stack_all_volumes_along_dimension(self,dimension=1):
        # Prepare to Stack And Merge All OCT Data
        octdata = self.octdatalist[-1]; # pick a single octdata
        vol_dimensions = (
            int(octdata.cfg_oct_xml.Ocity.Image.SizePixel.etElem[0].text),
            int(octdata.cfg_oct_xml.Ocity.Image.SizePixel.etElem[1].text),
            int(octdata.cfg_oct_xml.Ocity.Image.SizePixel.etElem[2].text),
        );
        vol_spacing_mm = (
            float(octdata.cfg_oct_xml.Ocity.Image.PixelSpacing.etElem[0].text),
            float(octdata.cfg_oct_xml.Ocity.Image.PixelSpacing.etElem[1].text),
            float(octdata.cfg_oct_xml.Ocity.Image.PixelSpacing.etElem[2].text),
        );
        print('SingleFOV --> Image Dims:{:s} PixelSpacing[mm]:{:s}'.format(str(vol_dimensions),str(vol_spacing_mm)))
        combined_vol_dimensions =(
            vol_dimensions[0],
            vol_dimensions[1]*len(self.octdatalist),
            vol_dimensions[2],
        )
        print('Combined --> Image Dims:{:s} PixelSpacing[mm]:{:s}'.format(str(combined_vol_dimensions),str(vol_spacing_mm)))


        if(self.num_oct_files>=1):
            mergedvol = pv.ImageData(dimensions=combined_vol_dimensions,spacing=vol_spacing_mm);
            
            merged_scalars = np.concatenate([octdata.scalars.reshape(vol_dimensions,order='F') for octdata in self.octdatalist],axis=dimension)

            # assign the scalar values which we will concatenate from all the oct data scalars
            #mergedvol['volume_scalars'] = np.concatenate([octdata.scalars for octdata in octdatalist], axis=0);
            #mergedvol['OCTintensity'] = np.concatenate([octdata.pvvol['OCTintensity'] for octdata in octdatalist],axis=0);
            mergedvol['OCTintensity'] = merged_scalars.ravel(order='F');

            return mergedvol;