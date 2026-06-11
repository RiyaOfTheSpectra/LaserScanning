import tkinter as tk
from tkinter import ttk
from tkinter.messagebox import showinfo, showwarning, showerror, askokcancel
from tkinter.filedialog import askopenfile, asksaveasfile
from tkinter.simpledialog import askinteger, askfloat

from multiprocessing.shared_memory import SharedMemory
from threading import Thread, Event

import json

import numpy as np

from matplotlib.backend_bases import key_press_handler
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                               NavigationToolbar2Tk)
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec

from cerberus import Validator

from scipy.fft import fft2
from scipy.signal import find_peaks
from skimage.feature import peak_local_max

from pyperclip import copy

from LaserScanning import AlignAPD, Scan, CleanUp, MirrorHold
from Config import LoadConf
from Schema import EXP_SETTINGS

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
        
        self.align_channel  = tk.StringVar(value=CHANNELS)
        self.align_ampl     = tk.DoubleVar()
        self.align_freq_hz  = tk.DoubleVar()

        self.loaded         = True

        self.scan_size_um.set(256)
        self.averaging.set(1)
        self.aq_time_ms.set(0.01)

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
        ttk.Button(self.menu_bar, text="Calibrate", command=self.calibrate)\
                .grid(row=0, column=9, sticky=(tk.N, tk.W, tk.E, tk.S))

        self.root.bind('r', lambda x : self.res_entry.focus())
        self.root.bind('t', lambda x : self.aqt_entry.focus())
        self.root.bind('L', lambda x : self.load())
        self.root.bind('A', lambda x : self.align())
        self.root.bind('<KeyPress-F5>', lambda x : self.scan())

        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.mainloop()

    def scan(self):
        self.data = Scan(
            self.config,
            float(self.scan_size_um.get() * 1e-6),
            int(self.res_entry.get()),
            aq_time_ms = self.aq_time_ms.get(),
            average = self.averaging.get()
            )
        self.volt_per_pixel = self.scan_size_um / (self.config['magnification'] * self.res_entry.get())

        CleanUp(self.config)
        self.loaded = False

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
        self.data = np.loadtxt(file, delimiter=',')
        self.loaded = True

        self.plot(self.data, int(self.scan_size_um.get()))
        return

    def align(self):
        AlignAPD(
                channel=self.chan_entry.get(),
                frequency=self.align_freq_hz.get(),
                amplitude=self.align_ampl.get())
        
        CleanUp(self.config)
        return

    def config(self):
        return

    def mirror_hold(self):
        if hasattr(self, 'coords'):
            term_sig = Event()
            term_sig.clear()
            hold_thread = Thread(
                target = MirrorHold,
                args = (
                    self.config,
                    self.coords * 1e-6,
                    term_sig))
            hold_thread.start()
            showinfo("Info", f"Mirror held.")
            # TODO: Display point at mirror held
            term_sig.set()
            showinfo("Info", f"Mirror returned to center.")
        else:
            showwarning("Warning", "No point selected.")
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

    def calibrate(self):
        if self.loaded:
            showwarning("Calibration", "Nothing has been scanned yet.")
            return

        if hasattr(self, "data"):
            if askokcancel("Calibration", "Do you want to calibrate using the current scan?"):
                fourier = np.abs(np.fft.fftshift(fft2(self.data)))
                length = np.shape(fourier)[0]
                # Set the centre of array to zero
                # major_k = find_peaks(fourier) # This doesn't work, need to use skimage.feature (see line below)
                major_k = peak_local_max(fourier) # Can also specify minimum spacing between peaks
                peak0 = major_k[0]
                peak1 = major_k[1]
                peak2 = major_k[2]
                kspc_dist1 = np.sqrt(np.sum((peak0 - peak1)**2))
                kspc_dist2 = np.sqrt(np.sum((peak0 - peak2)**2))
                avg_kspc_dist = 0.5*(kspc_dist1 + kspc_dist2)
                
                # Convert major_k to spacing
                micron = askfloat("Calibration", "Enter spacing between adjacent markings in microns.")
                volt_per_micron = self.volt_per_pixel * length / (micron * avg_kspc_dist)
                microns_per_volt = 1 / volt_per_micron
                askokcancel("Calibration", "Are you sure you want to erase the old calibration?")
                showinfo("Calibration", f"{microns_per_volt}")
                self.config['magnification'] = microns_per_volt
                # TODO: Save this to a file.
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

        smap = self.data_ax.imshow(np.flipud(data))

        dim = np.shape(data)[0]
        ticks_pos = np.linspace(0, dim, ticks)
        ticks_lab = np.linspace(-bounds_um * .5, bounds_um * .5, ticks)
        self.data_ax.set_xticks(ticks_pos, ticks_lab)
        self.data_ax.set_yticks(ticks_pos, np.flip(ticks_lab))
        self.data_ax.set_xlabel("um")
        self.data_ax.set_ylabel("um")

        self.fig.colorbar(smap, cax=self.cbar_ax, label="APD Voltage (V)")
        self.canvas.draw()

        self.canvas.callbacks.connect("button_press_event", self.on_click)

        size = self.scan_size_um.get()
        self.transform = lambda event: (np.array(self.data_ax.transAxes.inverted().transform((event.x, event.y))) - np.array([0.5, 0.5])) * size
        return

    def on_click(self, event):
        if event.inaxes == self.data_ax:
            self.coords = self.transform(event)
            copy(np.array2string(self.coords))
        return

    def close(self):
        CleanUp(self.config)
        self.root.destroy()
        return

if __name__ == "__main__":
    Display()
