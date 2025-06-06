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

    def __init__(self, studyname, **params):
        super().__init__(**params)
        #self.test_names = test_names;
        #self.dfloaded = dfloaded;
        #print('Loaded with {:d} tests:'.format(len(self.test_names)),self.test_names)
        self.octstudy = naatos_oct_tools.thorlabs_oct_file_reading.OCT_Study_Folder(studyname,folder_octexport_root);

    def _mkfig(self):
        octstudy = self.octstudy;

        # load data from oct study python class
        df = self.octstudy.load_data_extracted_along_strip();
        df = naatos_oct_tools.oct_linear_scan_processing.process_along_strip_data_frame(df);
        #df = df.reset_index(drop=False);    # put slice as a column

        nrows = len(metric_traces);
        fig = make_subplots(rows=nrows,shared_xaxes=True,vertical_spacing=0.02)

        myrow = 0;
        for legendgroup,ylabel,metric_columns in metric_traces:
            myrow += 1;

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
        #print("click datatype:{:s} data:{:s}", type(event), str(event));
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
        return self.plotpane;

        # #pn.bind(self._click_handling,self.plotpane.param.click_data);
        # iclicker_view = pn.bind(self._click_handling, self.plotpane.param.click_data);
        # return pn.Column(self.plotpane,iclicker_view);

        #return pn.pane.Str("Single String _mkfigure() ran")
    
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

    def __panel__(self):
        buttFolder = pn.widgets.Button(name='ExploreFolder');
        buttA = pn.widgets.Button(name='VideoA');
        buttA.on_click( lambda event: self._launch_study_vlc(filename='figout_stepA.mp4') );
        buttB = pn.widgets.Button(name='VideoB');
        buttB.on_click( lambda event: self._launch_study_vlc(filename='figout_stepB.mp4') );
        buttC = pn.widgets.Button(name='VideoMaze');
        buttC.on_click( lambda event: self._launch_study_vlc(filename='figout_post_maze_test.mp4') );
        return pn.Column(
            pn.Row(
                pn.pane.Str(f'OCT Study:<br>{self.octstudy.name}'),
                buttFolder,buttA,buttB,buttC,
                # self.param.plotstyle,
                # self.param.metrics,
                # self.param.scans,
            ),
            pn.Tabs(
                ('metricplot',self._mkfigure),
            ),
            #plotly_fig
            #pn.bind(self._mkfigure,self.param.plotstyle,self.param.metrics)
        )
    
#obj2 = OCTMultiStripMetricViewer(['GHL_pyapp_20250512T0947', 'GHL_pyapp_20250512T0951', 'GHL_pyapp_20250512T0955', 'GHL_pyapp_20250512T0959', 'GHL_pyapp_20250512T1002', 'GHL_pyapp_20250512T1117', 'GHL_pyapp_20250512T1121', 'GHL_pyapp_20250512T1125', 'GHL_pyapp_20250512T1130', 'GHL_pyapp_20250512T1133', 'GHL_pyapp_20250512T1137', 'GHL_pyapp_20250512T1140', 'GHL_pyapp_20250512T1144', 'GHL_pyapp_20250512T1149', 'GHL_pyapp_20250512T1152', 'GHL_pyapp_20250512T1158', 'GHL_pyapp_20250512T1201', 'GHL_pyapp_20250512T1204', 'GHL_pyapp_20250512T1208', 'GHL_pyapp_20250512T1211', 'GHL_pyapp_20250512T1215', 'GHL_pyapp_20250512T1218', 'GHL_pyapp_20250512T1222', 'GHL_pyapp_20250512T1225', 'GHL_pyapp_20250512T1230', 'GHL_pyapp_20250512T1238', 'GHL_pyapp_20250512T1241', 'GHL_pyapp_20250512T1245', 'GHL_pyapp_20250512T1248', 'GHL_pyapp_20250512T1251', 'GHL_pyapp_20250512T1254', 'GHL_pyapp_20250512T1258', 'GHL_pyapp_20250512T1303']);
# finpn = pn.Column(obj);
