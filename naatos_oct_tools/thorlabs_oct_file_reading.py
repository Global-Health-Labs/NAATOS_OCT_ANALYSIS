from pathlib import Path
import json
import configparser
import pprint
import time
import pprint
pp = pprint.PrettyPrinter(indent=4);
from dataclasses import dataclass

import addict

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
import vtk
from PIL import Image
import SimpleITK as sitk
import skimage
import vedo

from zipfile import ZipFile
import xml.etree.ElementTree as ET

import re




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
    vol_dimensions: np.ndarray
    vol_spacing_mm: np.ndarray

    def _make_sitkvol(self):
        scalars = self.scalars;
        vol_dimensions = self.vol_dimensions;
        vol_spacing_mm = self.vol_spacing_mm;

        sitkvol = sitk.GetImageFromArray( scalars.reshape(vol_dimensions,order='F').transpose((2,1,0)) , isVector=False); # sitk uses opposite indexing
        sitkvol.SetSpacing(vol_spacing_mm);

        return sitkvol;

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
        sitkvol = sitk.GetImageFromArrayView( scalars.reshape(vol_dimensions,order='F').transpose((2,1,0)) , isVector=False); # sitk uses opposite indexing
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
        vol_dimensions = vol_dimensions,
        vol_spacing_mm = vol_spacing_mm,
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
        return self.study_info['study_has_json_info_file'];

    @property
    def json_info_file(self):
        if(self.has_json_info_file):
            fname = list(self.folder_study.glob('info.json'))[0];
            with open(fname,mode='r') as file:
                return json.load(file);

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
    def openWindowsExplorerToProcessedFolder(self):
        import subprocess
        print('Opening explorer to',str(self.folder_study_processed));
        subprocess.Popen(r'explorer /select,"{:s}"'.format(str(self.folder_study_processed)));

    def resultsCheck(self):
        """Check what type of result output artifacts exist in the folder (these would be computationally intensive to regenerate)

        Returns:
            _type_: _description_
        """
        results = {};

        results['exist_data_extracted'] = (self.folder_study_processed/'data_extracted.npz').exists();
        # results['figoutmp4_stepA'] = any([re.match(r'figureoutput_.*_stepA\.mp4',l.name) is not None for l in self.folder_study_processed.iterdir()]);
        # results['figoutmp4_stepB'] = any([re.match(r'figureoutput_.*_stepB\.mp4',l.name) is not None for l in self.folder_study_processed.iterdir()]);
        results['figoutmp4_stepA'] = any([re.match(r'figout.*_stepA\.mp4',l.name) is not None for l in self.folder_study_processed.iterdir()]);
        #results['figoutmp4_stepB'] = any([re.match(r'figout.*_stepB\.mp4',l.name) is not None for l in self.folder_study_processed.iterdir()]);
        #results['figoutmp4_mazetest'] = any([re.match(r'figout_post_maze_test.mp4',l.name) is not None for l in self.folder_study_processed.iterdir()]);
        if( (self.folder_study_processed/'along_strip_data_extracted.hdf5').exists() ):
            with pd.HDFStore(self.folder_study_processed/'along_strip_data_extracted.hdf5',mode='r') as store:
                results['along_strip_data_extracted'] = store.keys()
        else:
            results['along_strip_data_extracted'] = False;

        return results;

    def load_all_octs(self,make_sitk_volume=False,make_pv_volume=False,idx : int = None):
        self.octdatalist = [];
        if(self.num_oct_files>=1):
            octfiles = list(self.folder_study.glob('{:s}*.oct'.format(self.name)))
            if(idx is not None):
                octfiles = [octfiles[0]];
            for octfile in octfiles:
                octdata = _read_oct(octfile,make_sitk_volume=make_sitk_volume,make_pv_volume=make_pv_volume);
                self.octdatalist.append(octdata);

    def load_first_oct(self,make_sitk_volume=False,make_pv_volume=False):
        self.load_all_octs(make_sitk_volume,make_pv_volume,idx=0)

    def unload_all_octdata(self):
        self.octdatalist = [];

        import gc
        # Force garbage collection
        gc.collect()

    def pv_stack_all_volumes_along_dimension(self,dimension=1):
        if(self.num_oct_files<=1):
            print('Nothing to merge');
            return None;
        else:
            # Prepare to Stack And Merge All OCT Data
            octdata = self.octdatalist[0]; # pick a single octdata
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

            # check rotation settings in the file
            rotation = float(octdata.cfg_oct_xml.Ocity.Image.Angle.etElem.text)
            if(rotation==0.0):
                pass;
            elif(rotation==-90.0):
                # 4/29/2025
                # this data will appear rotated, and each FOV needs to be both permutted and flipped
                print('rotation setting was {:} which differs from the expected 0.00. we will need to permute them flip some dimensions'.format(rotation))
            else:
                raise NotImplementedError(f'rotation={rotation} is not supported')
            
            print('SingleFOV --> Image Dims:{:s} PixelSpacing[mm]:{:s}'.format(str(vol_dimensions),str(vol_spacing_mm)))
            #print('Combined --> Image Dims:{:s} PixelSpacing[mm]:{:s}'.format(str(combined_vol_dimensions),str(vol_spacing_mm)))


            def getVtkAlg_PermuteAndFlip_PVImage(pvvol,order=(0,2,1)):
                alg = vtk.vtkImagePermute();
                alg.SetInputDataObject(pvvol);
                alg.SetFilteredAxes(*order);
                #alg.Update();
                #return alg;
                
                alg2 = vtk.vtkImageFlip();
                alg2.SetFilteredAxes(1);
                #alg2.SetInputDataObject(alg.GetOutput());
                alg2.SetInputConnection(alg.GetOutputPort());
                
                alg2.Update();
                return alg2;

                # alg3 = vtk.vtkImageFlip();
                # alg3.SetFilteredAxes(2);
                # alg3.SetInputDataObject(alg2.GetOutput());
                # alg3.Update();

                # return alg3;

            # start with first volume
            #octdata = self.octdatalist[0];

            # get a vtk image of the first field of view
            pvvol = pv.ImageData(dimensions=vol_dimensions,spacing=vol_spacing_mm);
            pvvol['OCTintensity'] = octdata.scalars;
            #print('octdata[0] = pvvol',pvvol);

            if(rotation==-90.0):
                # permute and rotate if necessary
                pvvol = pv.wrap(getVtkAlg_PermuteAndFlip_PVImage(pvvol).GetOutput());
            #print('octdata[0] = pvvol after permutting',pvvol);


            alg_appender = vtk.vtkImageAppend();
            alg_appender.SetAppendAxis(1);
            alg_appender.SetInputDataObject(pvvol);
            algs = [];
            pvvols = [];
            for count,octdata in enumerate(self.octdatalist[1:]):
                this_pvvol = pv.ImageData(dimensions=vol_dimensions,spacing=vol_spacing_mm);
                this_pvvol['OCTintensity'] = octdata.scalars;

                if(rotation==0.0):
                    pvvols.append(this_pvvol);
                    alg_appender.AddInputDataObject(this_pvvol);
                elif(rotation==-90.0):
                    alg = getVtkAlg_PermuteAndFlip_PVImage(this_pvvol);
                    
                    algs.append(alg);
                    pvvols.append(this_pvvol);
                    alg_appender.AddInputDataObject(alg.GetOutput());
            alg_appender.Update();
            mergedvol = pv.wrap(alg_appender.GetOutput());
            print('Combined --> Image Dims:{:s} PixelSpacing[mm]:{:s}'.format(str(mergedvol.dimensions),str(mergedvol.spacing)))

            return mergedvol;

    def generate_merged_vdvol_and_rescaled(self,oct_scalar_min,oct_scalar_max):
        # Merge strip OCT data into one big volume
        mergedvol = self.pv_stack_all_volumes_along_dimension();
        
        # Rescale and cast to unit8_t
        # make vedo volume
        vdvol = vedo.Volume(mergedvol);

        # calculate scaled within range and scale to 255, then cast to 1-byte value
        scalars_rescaled_as_int = skimage.util.img_as_ubyte( (np.clip(vdvol.dataset.active_scalars,a_min=oct_scalar_min,a_max=oct_scalar_max)-oct_scalar_min)/(oct_scalar_max-oct_scalar_min) )

        # replace the scalars
        vdvol.dataset['OCTintensity'] = scalars_rescaled_as_int;
        
        return vdvol;

    #---- METHODS FOR LOADING POSTPROCSESED DATA
    def load_previously_saved_merged_volume(self):
        #fname_merged_and_rescaled_volume = self.folder_study_processed/'{:s}_STACKED_RESCALED_{:}to{:}_uint8.vtk'.format(octstudy.name,oct_scalar_min,oct_scalar_max);
        #fname_merged_and_rescaled_volume = self.folder_study_processed/'{:s}_STACKED_RESCALED_{:}to{:}_uint8.vtk'.format(octstudy.name,oct_scalar_min,oct_scalar_max);
        #a = self.folder_study_processed.glob(''
                                             
        filematch = list(self.folder_study_processed.glob(r'{:s}_STACKED_RESCALED*uint8.vtk'.format(self.name)))[0];
        scalerange = re.findall(r'.*STACKED_RESCALED_+(\d*)to(\d*)',filematch.name)[0];

        #re.findall(r'.*STACKED_RESCALED_+(\d*)to(\d*)',list(octstudy.folder_study_processed.glob(r'{:s}_STACKED_RESCALED*uint8.vtk'.format(octstudy.name)))[0].name)
            #/'{:s}_STACKED_RESCALED_{:}to{:}_uint8.vtk'.format(octstudy.name,oct_scalar_min,oct_scalar_max);

        print(f'Loading {filematch.name}')
        #vdvol = vedo.read(fname_merged_and_rescaled_volume);
        vdvol = vedo.Volume(pv.read(filematch));
        self.vdvol = vdvol;
        self.vdvolscalerange = scalerange;

    def load_data_extracted(self):
        data = np.load(self.folder_study_processed/'data_extracted.npz',allow_pickle=True)['data_extracted'].item();
        #loaded_data_extracted = addict.Addict(  )
        return addict.Addict(data);

    def load_data_extracted_along_strip(self):
        dfs = [];
        try:
            with pd.HDFStore(self.folder_study_processed/'along_strip_data_extracted.hdf5',mode='r') as store:
                for storekey in store.keys():
                    print('Loading',storekey);
                    dfs.append(store[storekey]);
            return pd.concat(dfs,ignore_index=False,axis=1)
        except Exception as e:
            print('Couldnt open',self.folder_study_processed/'along_strip_data_extracted.hdf5');
            print(e)
            return False;
