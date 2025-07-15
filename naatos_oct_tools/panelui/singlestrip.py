import panel as pn
import param

import plotly.express as px

import plotly.graph_objects as go
from plotly.subplots import make_subplots

import itertools
import numpy as np

import naatos_oct_tools.thorlabs_oct_file_reading
import naatos_oct_tools.oct_linear_scan_processing
import naatos_oct_tools.panelui.metricdefs as metricdefs
metrics = metricdefs.metrics;
metric_traces = metricdefs.metric_traces;

from naatos_oct_tools.paths import folder_octexport_root

from decord import VideoReader
from decord import cpu, gpu
import holoviews as hv

class _VIEWER_images_base(pn.viewable.Viewer):
    filelist = param.Selector(objects=[]);

    def _populate_parameters(self):
        #self.param.filelist.objects = sorted([x.name for x in list(self.octstudy.folder_study_processed.glob('processing_step1*.jpg'))],reverse=True);
        #self.filelist = self.param.filelist.objects[0];
        raise NotImplementedError;

    def __init__(self, octstudy : naatos_oct_tools.thorlabs_oct_file_reading.OCT_Study_Folder, **params):
        super().__init__(**params);
        self.octstudy = octstudy;
    
        # populate filelist selector
        self._populate_parameters();
    
    @param.depends('filelist')
    def showimage_from_dropdown(self):
        if(self.filelist is not None):
            return pn.pane.JPG(self.octstudy.folder_study_processed / self.filelist);
        #return pn.pane.Str(self.filelist);

    def showimage_all_in_column(self):
        pncol = pn.layout.Column()
        for imgname in self.param.filelist.objects:
            fname = self.octstudy.folder_study_processed / imgname;
            pncol.append(
                pn.layout.Row(
                    pn.pane.Str(imgname),
                    pn.pane.JPG(fname)
                )
            )
        return pncol;


class _VIEWER_images_bounds(_VIEWER_images_base):
    def _populate_parameters(self):
        self.param.filelist.objects = sorted([x.name for x in list(self.octstudy.folder_study_processed.glob('processing_step1*.jpg'))],reverse=True);
        self.filelist = self.param.filelist.objects[0];

    def __panel__(self):
        return pn.Column(
            #pn.pane.Str(f'Images'),
            pn.Row(
                #self.param.filelist,
                #self.showimage_from_dropdown,
                self.showimage_all_in_column,
            ),
        )

class _VIEWER_images_crossovers(_VIEWER_images_base):
    def _populate_parameters(self):
        self.param.filelist.objects = [x.name for x in list(self.octstudy.folder_study_processed.glob('processing_stepA_connection*.jpg'))];
        self.filelist = self.param.filelist.objects[0];

    def __panel__(self):
        return pn.Column(
            #pn.pane.Str(f'Images'),
            pn.Row(
                self.param.filelist,
                self.showimage_from_dropdown,
                #self.showimage_all_in_column,
            ),
        )


class OCTSingleStripMetricViewer(pn.viewable.Viewer):
    # follow https://panel.holoviz.org/tutorials/intermediate/interactivity.html
    # from   the "with pn.rx" class
    test_names = [];
    #dfloaded = param.DataFrame();

    #plotstyle = param.Selector(objects=['scatterVsLength','boxplotOfStrip'],default='scatterVsLength');

    # metrics = param.ListSelector(
    #     default=['wax_width_px','seg_area_to_areafilled','num_paths'],
    #     objects=list(metrics.keys())
    # );

    # scans = param.ListSelector(
    #     default=[],
    #     objects=[],
    # );

    plotpane = pn.pane.Plotly(sizing_mode='stretch_both', width_policy='max');
    #videopane = pn.pane.Placeholder("Select a time point to show video frame");
    videopane = pn.pane.Plotly(sizing_mode='stretch_both', width_policy='max');

    def __init__(self, studyname, **params):
        super().__init__(**params)
        #self.test_names = test_names;
        #self.dfloaded = dfloaded;
        #print('Loaded with {:d} tests:'.format(len(self.test_names)),self.test_names)
        self.octstudy = naatos_oct_tools.thorlabs_oct_file_reading.OCT_Study_Folder(studyname,folder_octexport_root);
        self.pane_img_bounds = _VIEWER_images_bounds(self.octstudy);
        self.pane_img_xovers = _VIEWER_images_crossovers(self.octstudy);
    
        # video frame extraction tool
        videopath = (self.octstudy.folder_study_processed/'figout_stepA.mp4').as_posix();
        videoreader = VideoReader(videopath, ctx=cpu(0));
        print('video frames:', len(videoreader))
        self.videoreader = videoreader;

    def _mkfig(self,use_millimeters=False):
        octstudy = self.octstudy;

        # load data from oct study python class
        df = self.octstudy.load_data_extracted_along_strip();
        df = naatos_oct_tools.oct_linear_scan_processing.process_along_strip_data_frame(df);
        #df = df.reset_index(drop=False);    # put slice as a column
        
        if use_millimeters:
            if(len(octstudy.octdatalist)==0):
                octstudy.load_first_oct();
            octdata = octstudy.octdatalist[0];
            spacing_mm_per_pixel = octdata.vol_spacing_mm[1]; # dimension 1 is the one along the strip
            self.spacing_mm_per_pixel = spacing_mm_per_pixel;
            print('mm per pixel along strip length',self.spacing_mm_per_pixel)

        nrows = len(metric_traces);
        fig = make_subplots(rows=nrows,shared_xaxes=True,vertical_spacing=0.02)

        myrow = 0;
        for legendgroup,ylabel,metric_columns in metric_traces:
            myrow += 1;

            if use_millimeters:
                datax = df['slice']*spacing_mm_per_pixel;
            else:
                datax = df['slice'];
            for metric_col in metric_columns:
                datay = df[metric_col];

                if(ylabel!='counts'):
                    fig.add_trace(
                        go.Scattergl(
                            x = datax,
                            y = datay,
                            mode='markers',
                            #type = 'heatmap',
                            #colorscale = 'jet'
                            name=metric_col,
                            #marker_color=this_trace_info['tracecolor'],
                            legendgroup=legendgroup,
                            legendgrouptitle={'text': legendgroup},
                            #showlegend=myrow==1,
                            #hoverinfo='name',
                            #visible='legendonly',
                        ),
                        row=myrow,col=1,
                    )
                else:
                    fig.add_trace(
                        go.Bar(
                            x = datax,
                            y = datay,
                            #mode='markers',
                            #type = 'heatmap',
                            #colorscale = 'jet'
                            name=metric_col,
                            #marker_color=this_trace_info['tracecolor'],
                            legendgroup=legendgroup,
                            legendgrouptitle={'text': legendgroup},
                            #showlegend=myrow==1,
                            #hoverinfo='name',
                            #visible='legendonly',
                        ),
                        row=myrow,col=1,
                    )

            
            fig.update_yaxes(title=ylabel,row=myrow);
            if(ylabel=='counts'):
                fig.update_yaxes(type='log',row=myrow);

        # setup legends per row
        for i, yaxis in enumerate(fig.select_yaxes(col=1), 1):
            legend_name = f"legend{i}"
            fig.update_layout({legend_name: dict(y=yaxis.domain[1], yanchor="top")}, showlegend=True)
            fig.update_traces(row=i, legend=legend_name)

        if use_millimeters:
            fig.update_xaxes(title='distance along strip (mm from left edge)',row=nrows,col=1);
        else:
            fig.update_xaxes(title='distance along strip (px)',row=nrows,col=1);


        fig.update_traces(xaxis='x{:}'.format(nrows))
        fig.update_layout(hovermode='x unified',spikedistance=-1,hoverdistance=5);\
        fig.update_layout(legend_groupclick='toggleitem');  # hide individual metrics, not groups
        fig.update_layout(
            title='OCT Study {:s}'.format(octstudy.name)
        )
        #fig.update_yaxes(title='pixels',row=1);
        #fig.show(renderer='browser')
        return fig;

    #@pn.depends(plotpane.param.click_data, watch=True)
    def _click_handling(self,event):
        print("click datatype:{:s} data:{:s}", type(event), str(event));
        if not event:
            return "No point clicked"
        try:
            point = event["points"][0]
            curvenumber = point['curveNumber'];
            index = point['pointIndex']
            x = point['x']
            y = point['y']
            if(type(x) is not str):
                # x was a number
                # so.... find the name
                scanname = self.plotpane.object.data[curvenumber].name;
            else:
                scanname = x;
        except Exception as ex:
            return f"You clicked the Plotly Chart! I could not determine the point: {ex}"
        
        return f"**You clicked point index {index} at ({x}, {y}) on curve ({scanname}) in the Plotly Chart!**"

    def _mkfigure(self):
        fig = self._mkfig();
        fig.layout.autosize = True;

        # self.plotpane = pn.pane.Plotly(
        #     fig,sizing_mode='stretch_both', width_policy='max',
        # );
        self.plotpane.object=fig;
        #return self.plotpane;

        #pn.bind(self._click_handling,self.plotpane.param.click_data);
        iclicker_view = pn.bind(self._click_handling, self.plotpane.param.click_data);
        return pn.Column( iclicker_view , self.plotpane);

        #return pn.pane.Str("Single String _mkfigure() ran")

    def _click_handling1_video(self,event):
        print("click1 video datatype:{:s} data:{:s}", type(event), str(event));
        if not event:
            return "No point clicked"
        try:
            point = event["points"][0]
            curvenumber = point['curveNumber'];
            index = point['pointIndex']
            x = point['x']
            y = point['y']
            if(type(x) is not str):
                # x was a number
                # so.... find the name
                scanname = self.plotpane.object.data[curvenumber].name;
            else:
                scanname = x;
        except Exception as ex:
            return f"You clicked the Plotly Chart! I could not determine the point: {ex}"
        
        frame_to_find = index;
        if(self.videoreader is not None):
            frame = self.videoreader[frame_to_find]; # get frame
            #im = hv.RGB(np.array(frame));
            #self.videopane = pn.pane.HoloViews(im);
            #fig = plt.figure
            fig = px.imshow(frame.asnumpy());
            fig.update_layout(
                scene = dict(
                    xaxis = dict(visible=False),
                    yaxis = dict(visible=False),
                    zaxis = dict(visible=False),
                )
            );
            #self.videopane = pn.pane.Plotly(fig);
            self.videopane.object = fig;

        return f"**You clicked point index {index} at ({x}, {y}) on curve ({scanname}) in the Plotly Chart!**"

    def _mkfigure_with_video(self):
        fig = self._mkfig();
        fig.layout.autosize = True;

        plotlypane = pn.pane.Plotly(
            fig,sizing_mode='stretch_both', width_policy='max',
        );
        iclicker_view = pn.bind(self._click_handling1_video, plotlypane.param.click_data);
        
        return pn.Row(
            pn.Column( iclicker_view , plotlypane),
            self.videopane
        );

    def _mkfigure2(self):
        fig = self._mkfig(use_millimeters=True);
        fig.layout.autosize = True;

        # add slice lines
        xvals = fig.data[0]['x'];
        #interval = 5; # mm
        interval = 4.91; # mm
        for count in range(int(xvals.max()/interval)+1):
            #print(count)
            fig.add_shape(
                type="line",
                yref="paper",
                xref="x",
                x0=count*interval,
                y0=0,
                x1=count*interval,
                y1=1,
                #line=dict(color="RoyalBlue", width=3)
                line=dict(color="Black", width=3)
            ,row=4,col=1)

            fig.add_annotation(
                text="{:}".format(count+1),
                yref="paper",
                x=(count*interval)+interval/2,
                y=0.5,
                showarrow=True,
                #arrowhead=1,
                font=dict(size=14, color="blue"),
                row=4,col=1
            )
            #fig.add_vline(x=count*interval,row='all');
        #self.plotpane2.object = fig;
        #fig = self.plotpane.object;
        for shape in fig.layout.shapes:
            shape["yref"]="paper"

        fig.layout.title.text = '{:s}<br>slice_interval:{:}mm'.format(fig.layout.title.text,interval)
        return fig;

    def _click_handling2(self,event):
        #print("click2 datatype:{:s} data:{:s}".format(type(event), str(event)));
        if not event:
            return "No point clicked"
        try:
            point = event["points"][0]
            curvenumber = point['curveNumber'];
            index = point['pointIndex']
            x = point['x']
            y = point['y']
            if(type(x) is not str):
                # x was a number
                # so.... find the name
                scanname = self.plotpane.object.data[curvenumber].name;
            else:
                scanname = x;
        except Exception as ex:
            return f"You clicked the Plotly Chart! I could not determine the point: {ex}"
        
        # graph is mm position
        # calculate the pixel cooresponding to this point
        pixel_x_position = x/self.spacing_mm_per_pixel;

        return f"**You clicked point index {index} at ({x}, {y}) on curve ({scanname}) in the Plotly Chart!** This corresponds to pixel-space of {pixel_x_position} (assuming {self.spacing_mm_per_pixel} mm/pixel)"

    def _mkpane2(self):
        fig = self._mkfigure2();
        plotpane = pn.pane.Plotly(fig);
        #return fig;
        
        iclicker_view = pn.bind(self._click_handling2, plotpane.param.click_data);
        return pn.Column( iclicker_view , plotpane);
    
    def _launch_study_vlc(self,xpospx=None,filename='figout_stepA.mp4'):
        import subprocess
        #octstudy = naatos_oct_tools.thorlabs_oct_file_reading.OCT_Study_Folder(studyname,folder_octexport_root);
        octstudy = self.octstudy;
        args = [
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            str((octstudy.folder_study_processed/filename)),
        ];
        print(args);
        subprocess.Popen( args );
    
    def _open_explorer_window(self):
        self.octstudy.openWindowsExplorerToProcessedFolder();

    def __panel__(self):
        buttFolder = pn.widgets.Button(name='ExploreFolder');
        buttFolder.on_click( lambda event: self._open_explorer_window() );
        possible_video_link_files = ['figout_stepA.mp4','figout_stepB.mp4','figout_post_maze_test.mp4']
        video_buttons = [];
        for filename in possible_video_link_files:
            if((self.octstudy.folder_study_processed/filename).exists()):
                button = pn.widgets.Button(name=filename);
                button.on_click( lambda event: self._launch_study_vlc(filename=filename) );
                video_buttons.append(button);
        # buttA = pn.widgets.Button(name='VideoA');
        # buttA.on_click( lambda event: self._launch_study_vlc(filename='figout_stepA.mp4') );
        # buttB = pn.widgets.Button(name='VideoB');
        # buttB.on_click( lambda event: self._launch_study_vlc(filename='figout_stepB.mp4') );
        # buttC = pn.widgets.Button(name='VideoMaze');
        # buttC.on_click( lambda event: self._launch_study_vlc(filename='figout_post_maze_test.mp4') );
        return pn.Column(
            pn.Row(
                pn.pane.Str(f'OCT Study:<br>{self.octstudy.name}'),
                buttFolder,*video_buttons
                # self.param.plotstyle,
                # self.param.metrics,
                # self.param.scans,
            ),
            pn.Tabs(
                ('metricplot',self._mkfigure),
                ('metricplot video',self._mkfigure_with_video),
                ('metricplot_lfa_sliced',self._mkpane2),
                ('imgs bounds',self.pane_img_bounds),
                ('imgs paths',self.pane_img_xovers),
                dynamic=True,
                #active=2
            ),
        )
