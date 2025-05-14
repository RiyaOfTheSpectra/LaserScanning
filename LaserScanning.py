import numpy as np
import matplotlib.pyplot as plt
import nidaqmx as ni
from nidaqmx.constants import AcquisitionType

def GenerateGrid(
        ampl,
        step = 0.2
        ):
    """
    Generates a grid of samples to write to the mirror setups.  Each sample is
    generated thrice, so that the acquisition can occur on the middle step. This
    way, a data race, wherein acquisition is done before the mirrors have moved,
    is avoided.
    """

    ampl = ampl / 0.8
    step = step / 0.8

    a = np.arange(
            -ampl,
            ampl + step,
            step,
            )

    x, y = np.meshgrid(a, a)

    return (np.repeat(x, 3), np.repeat(y, 3))

def Scan(
        box,
        aq_time, # time spent on each sample in milliseconds
        ):
    """
    Scans and returns the filtered scanning data.
    """

    x, y = box
    z = np.zeros(np.shape(x))

    samps = len(x) // 3
    rate = 1e3 / aq_time
    l = int(np.sqrt(samps))

    with (
            ni.Task() as ao,
            ni.Task() as ai
            ):

        ao.ao_channels.add_ao_voltage_chan("Dev1/ao0")
        ao.ao_channels.add_ao_voltage_chan("Dev1/ao1")

        ai.ai_channels.add_ai_voltage_chan("Dev1/ai0")

        ao.timing.cfg_samp_clk_timing(
                rate,
                sample_mode = AcquisitionType.FINITE,
                samps_per_chan = samps
                )

        ai.timing.cfg_samp_clk_timing(
                rate,
                sample_mode = AcquisitionType.FINITE,
                samps_per_chan = samps
                )
        ai.triggers.cfg_dig_edge_start_trig("/Dev1/ao0")

        ao.write([x, y])
        z = ai.read()

        ai.start()
        ao.start()

    return np.reshape(z, (l, l, 3))[:, :, 1]
