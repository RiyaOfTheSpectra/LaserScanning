import tkinter as tk
from tkinter import ttk

RESOLUTIONS = [440, 720, 1080, 2160]
ADC_RANGES = [1, 2, 5, 10]

class Display():
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Confocal Scanning Microscope")

        # Variables
        self.resolution     = tk.IntVar(value=RESOLUTIONS)
        self.scan_size_um 	= tk.DoubleVar()
        self.averaging 	    = tk.IntVar()
        self.aq_time_ms 	= tk.DoubleVar()
        self.adc_ranges 	= tk.IntVar(value=ADC_RANGES)
        self.mirror_hold 	= tk.BooleanVar()

        #self.resolution.set(440)
        self.scan_size_um.set(256)
        self.averaging.set(1)
        self.aq_time_ms.set(0.1)
        #self.adc_ranges.set(1)
        #self.mirror_hold.set(False)

        # Frames and subframes
        self.frame = ttk.Frame(self.root)
        self.frame.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))
        self.display        = ttk.Frame(self.frame, borderwidth=5)
        self.menu_bar       = ttk.Frame(self.frame, borderwidth=5)
        self.control_panel  = ttk.Frame(self.frame, borderwidth=5)

        self.display.grid(column=3, row=1, columnspan=5, rowspan=5)
        self.menu_bar.grid(column=0, row=0, columnspan=8, rowspan=1)
        self.control_panel.grid(column=0, row=1, columnspan=3, rowspan=5)

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Populating the control panel
        ttk.Label(self.control_panel, text="ADC Range (in V)").grid(column=0, row=0, sticky=tk.W)
        ttk.Label(self.control_panel, text="Resolution").grid(column=0, row=1, sticky=tk.W)
        ttk.Label(self.control_panel, text="Scan Size (in micron)").grid(column=0, row=2, sticky=tk.W)
        ttk.Label(self.control_panel, text="Acquisition Time (in ms)").grid(column=0, row=3, sticky=tk.W)
        ttk.Label(self.control_panel, text="Averaging").grid(column=0, row=4, sticky=tk.W)

        self.adc_entry = tk.Listbox(self.control_panel, listvariable=self.adc_ranges)
        self.adc_entry.grid(column=1, row=0, sticky=tk.W)
        self.res_entry = tk.Listbox(self.control_panel, listvariable=self.resolution)
        self.res_entry.grid(column=1, row=1, sticky=tk.W)
        self.scz_entry = ttk.Entry(self.control_panel, textvariable=self.scan_size_um)
        self.scz_entry.grid(column=1, row=2, sticky=tk.W)
        self.aqt_entry = ttk.Entry(self.control_panel, textvariable=self.aq_time_ms)
        self.aqt_entry.grid(column=1, row=3, sticky=tk.W)
        self.avg_entry = ttk.Entry(self.control_panel, textvariable=self.averaging)
        self.avg_entry.grid(column=1, row=4, sticky=tk.W)

        self.root.bind('Q', lambda x : print(x))
        self.root.bind('r', lambda x : self.res_entry.focus)
        self.root.bind('t', lambda x : self.aqt_entry.focus)

        self.root.mainloop()

if __name__ == "__main__":
    Display()
