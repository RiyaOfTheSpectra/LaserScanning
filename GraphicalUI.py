import tkinter as tk
from tkinter import ttk
from tkinter.messagebox import showwarning, showerror
from tkinter.filedialog import askopenfile, asksaveasfile
from tkinter.simpledialog import askinteger

from multiprocessing.shared_memory import SharedMemory
import json
from Schema import EXP_SETTINGS
from cerberus import Validator

import numpy as np

from matplotlib.backend_bases import key_press_handler
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                               NavigationToolbar2Tk)
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec

from LaserScanning import AlignAPD, Scan, CleanUp

from Config import LoadConf

RESOLUTIONS = (440, 720, 1080, 2160)
ADC_RANGES  = (0.2, 1, 5, 10)
CHANNELS    = ('0', '1')

class Display():
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Confocal Scanning Microscope")

        # Variables
        self.config = LoadConf()

        self.scan_size_um 	= tk.DoubleVar()
        self.averaging 	    = tk.IntVar()
        self.aq_time_ms 	= tk.DoubleVar()
        self.mirror_hold 	= tk.BooleanVar()
        
        self.align_channel  = tk.StringVar(value=CHANNELS)
        self.align_ampl     = tk.DoubleVar()
        self.align_freq_hz  = tk.DoubleVar()

        self.scan_size_um.set(256)
        self.averaging.set(1)
        self.aq_time_ms.set(0.01)
        self.mirror_hold.set(False)

        # Frames and subframes
        self.frame = ttk.Frame(self.root)
        self.frame.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))
        self.display        = ttk.Frame(self.frame, borderwidth=5)
        self.menu_bar       = ttk.Frame(self.frame, borderwidth=5)
        self.control_panel  = ttk.Frame(self.frame, borderwidth=5)
        self.align_panel    = ttk.Frame(self.frame, borderwidth=5)

        self.display.grid(column=3, row=1, columnspan=5, rowspan=5)
        self.menu_bar.grid(column=0, row=0, columnspan=8, rowspan=1)
        self.control_panel.grid(column=0, row=1, columnspan=3, rowspan=2)
        self.align_panel.grid(column=0, row=3, columnspan=3, rowspan=2)

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Populating the control panel
        ttk.Label(self.control_panel, text="Scan Settings").grid(column=0, row=0, columnspan=2, sticky=(tk.E, tk.W))

        ttk.Label(self.control_panel, text="ADC Range (V)").grid(column=0, row=1, sticky=tk.W)
        ttk.Label(self.control_panel, text="Resolution").grid(column=0, row=2, sticky=tk.W)
        ttk.Label(self.control_panel, text="Scan Size (micron)").grid(column=0, row=3, sticky=tk.W)
        ttk.Label(self.control_panel, text="Acquisition Time (ms)").grid(column=0, row=4, sticky=tk.W)
        ttk.Label(self.control_panel, text="Averaging").grid(column=0, row=5, sticky=tk.W)

        self.adc_entry = ttk.Combobox(self.control_panel)
        self.adc_entry['values'] = ADC_RANGES
        self.adc_entry.state(['readonly'])
        self.adc_entry.set('1')
        self.adc_entry.grid(column=1, row=1, sticky=tk.W)

        self.res_entry = ttk.Combobox(self.control_panel)
        self.res_entry['values'] = RESOLUTIONS
        self.res_entry.state(['readonly'])
        self.res_entry.set('440')
        self.res_entry.grid(column=1, row=2, sticky=tk.W)

        self.scz_entry = ttk.Entry(self.control_panel, textvariable=self.scan_size_um)
        self.scz_entry.grid(column=1, row=3, sticky=tk.W)

        self.aqt_entry = ttk.Entry(self.control_panel, textvariable=self.aq_time_ms)
        self.aqt_entry.grid(column=1, row=4, sticky=tk.W)

        self.avg_entry = ttk.Entry(self.control_panel, textvariable=self.averaging)
        self.avg_entry.grid(column=1, row=5, sticky=tk.W)

        # Populating the alignment panel
        ttk.Label(self.align_panel, text="Align Settings").grid(column=0, row=0, columnspan=2, sticky=(tk.E, tk.W))

        ttk.Label(self.align_panel, text="Channel").grid(column=0, row=1, sticky=tk.W)
        ttk.Label(self.align_panel, text="Frequency (Hz)").grid(column=0, row=2, sticky=tk.W)
        ttk.Label(self.align_panel, text="Amplitude (Degrees)").grid(column=0, row=3, sticky=tk.W)
        
        self.chan_entry = ttk.Combobox(self.align_panel)
        self.chan_entry['values'] = CHANNELS
        self.chan_entry.state(['readonly'])
        self.chan_entry.set('0')
        self.chan_entry.grid(column=1, row=1, sticky=tk.W)

        self.frq_entry = ttk.Entry(self.align_panel, textvariable=self.align_freq_hz)
        self.frq_entry.grid(column=1, row=2, sticky=tk.W)

        self.ampl_entry = ttk.Entry(self.align_panel, textvariable=self.align_ampl)
        self.ampl_entry.grid(column=1, row=3, sticky=tk.W)

        # Populating the menu bar
        ttk.Button(self.menu_bar, text="Scan", command=self.scan)\
                .grid(row=0, column=1, sticky=(tk.N, tk.W, tk.E, tk.S))
        ttk.Button(self.menu_bar, text="Save", command=self.save)\
                .grid(row=0, column=2, sticky=(tk.N, tk.W, tk.E, tk.S))
        ttk.Button(self.menu_bar, text="Load", command=self.load)\
                .grid(row=0, column=3, sticky=(tk.N, tk.W, tk.E, tk.S))
        ttk.Button(self.menu_bar, text="Align", command=self.align)\
                .grid(row=0, column=4, sticky=(tk.N, tk.W, tk.E, tk.S))
        ttk.Button(self.menu_bar, text="Save Settings", command=self.settings_save)\
                .grid(row=0, column=5, sticky=(tk.N, tk.W, tk.E, tk.S))
        ttk.Button(self.menu_bar, text="Load Settings", command=self.settings_load)\
                .grid(row=0, column=6, sticky=(tk.N, tk.W, tk.E, tk.S))
        ttk.Button(self.menu_bar, text="Mirror Hold", command=self.mirror_hold)\
                .grid(row=0, column=7, sticky=(tk.N, tk.W, tk.E, tk.S))
        ttk.Button(self.menu_bar, text="Config", command=self.config)\
                .grid(row=0, column=8, sticky=(tk.N, tk.W, tk.E, tk.S))

        self.root.bind('r', lambda x : self.res_entry.focus())
        self.root.bind('t', lambda x : self.aqt_entry.focus())
        self.root.bind('L', lambda x : self.load())
        self.root.bind('A', lambda x : self.align())
        self.root.bind('<KeyPress-F5>', lambda x : self.scan())

        self.root.mainloop()

    def scan(self):
        self.data = Scan(
            self.config,
            float(self.scan_size_um.get() * 1e-6),
            int(self.res_entry.get()),
            aq_time_ms = self.aq_time_ms.get(),
            average = self.averaging.get()
            )
        CleanUp()

        self.plot(self.data, float(self.scan_size_um.get()))
        return

    def save(self):
        output_file = asksaveasfile()
        np.savetxt(
            output_file,
            self.data,
            delimiter=",",
            header=\
            f"Size = {self.scan_size_um.get()}um,\nAcquisition time = {self.aq_time_ms.get()}ms\nResolution = {self.res_entry.get()}\nAverage = {self.averaging.get()}")
        return

    def load(self):
        file = askopenfile()
        data = np.loadtxt(file, delimiter=',')

        self.plot(data, int(self.scan_size_um.get()))
        return

    def align(self):
        AlignAPD(
                channel=self.chan_entry.get(),
                frequency=self.align_freq_hz.get(),
                amplitude=self.align_ampl.get())
        
        CleanUp()
        return

    def config(self):
        return

    def mirror_hold(self):
        return

    def settings_save(self):
        settings = {
            "scan_size_um"  : self.scan_size_um.get(),
            "aq_time_ms"    : self.aq_time_ms.get(),
            "averaging"     : self.averaging.get(),
            "adc_range"     : self.adc_entry.get(),
            "resolution"    : self.res_entry.get()
        }
        settings_string = json.dumps(settings, indent=4)
        file = asksaveasfile()
        file.write(settings_string)
        file.close()
        return

    def settings_load(self):
        file = askopenfile()
        data = file.read()
        file.close()
        settings_shjh = json.loads(data)
        if Validator(EXP_SETTINGS).validate(settings_shjh):
            self.scan_size_um.set(settings_shjh["scan_size_um"])
            self.aq_time_ms.set(settings_shjh["aq_time_ms"])
            self.averaging.set(settings_shjh["averaging"])
            self.adc_entry.set(settings_shjh["adc_range"])
            self.res_entry.set(settings_shjh["resolution"])
        else:
            print(Validator(EXP_SETTINGS).errors)
            raise ValueError("Bad settings file")
        return

    def plot(self, data, bounds_um, ticks=5):

        if hasattr(self, 'fig'):
            self.data_ax.clear()
            self.cbar_ax.clear()
        else:
            self.fig = Figure(figsize=(8.5,8), dpi=90)
            gs = GridSpec(1, 2, width_ratios=[16,1])

            self.data_ax = self.fig.add_subplot(gs[0])
            self.cbar_ax = self.fig.add_subplot(gs[1])
            self.canvas = FigureCanvasTkAgg(self.fig, master=self.display)
            self.canvas.get_tk_widget().grid(column=0, row=0)

        smap = self.data_ax.imshow(data)

        dim = np.shape(data)[0]
        ticks_pos = np.linspace(0, dim, ticks)
        ticks_lab = np.linspace(-bounds_um * .5, bounds_um * .5, ticks)
        self.data_ax.set_xticks(ticks_pos, ticks_lab)
        self.data_ax.set_yticks(ticks_pos, ticks_lab)
        self.data_ax.set_xlabel("um")
        self.data_ax.set_ylabel("um")

        self.fig.colorbar(smap, cax=self.cbar_ax, label="APD Voltage (V)")
        self.canvas.draw()
        return

if __name__ == "__main__":
    Display()
    CleanUp()
