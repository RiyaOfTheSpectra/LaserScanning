import argparse
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
    rate = 3e3 / aq_time
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("amplitude", type=float, help="Amplitude of the beam, in degrees.")
    parser.add_argument("time_step", type=float, help="Acquisition time for each pixel, in milliseconds.")
    parser.add_argument("angl_step", type=float, help="Angular separation between pixels, in degrees.")
    parser.add_argument('-o', "--output", help="Filename to save data.")
    parser.add_argument('-s', "--show", help="Show map when done.", action="store_true")

    args = parser.parse_args()

    if not ( args.show & (args.output==None) ):
        raise RuntimeError("The output will not be shown or saved, and will be forgotten, for ever…\nDon't.")

    box = GenerateGrid(args.amplitude, step=args.angl_step)
    z = Scan(box, args.time_step)
    """
    samps = len(z) // 3
    l = int(np.sqrt(samps))
    z = np.reshape(z, (l, l, 3))[:, :, 1]
    """

    if args.show:
        plt.pcolormesh(z)
        plt.gca().set_aspect('equal')
        plt.show()
        # TODO: Axes labelling.

    if args.output:
        np.savetxt(
                args.output,
                z,
                delimiter=",",
                header=f"# Amplitude = {args.amplitude}°,\n# Acquisition time = {args.time_step}s\n# Angular Resolution = {args.angl_step}°\n# "
                )
        # TODO: Check validity of file.
