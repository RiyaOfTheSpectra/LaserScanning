import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as anim
from datetime import datetime, timedelta
import nidaqmx as ni
from nidaqmx.constants import AcquisitionType, DigitalWidthUnits, TerminalConfiguration
from time import sleep, monotonic
from math import floor
import warnings

from multiprocessing import Pipe
from threading import Event
from threading import Thread as Process

def Scan(
    ampl,
    step = 0.2,
    aq_time_ms = 0.1, # time spent on each sample in milliseconds
    dry = False,
    average = 0,
):
    """
    Generates a grid of samples to write to the mirror setups.  Each sample is
    generated thrice, so that the acquisition can occur on the middle step. This
    way, a data race, wherein acquisition is done before the mirrors have moved,
    is avoided.

    Scans and returns the filtered scanning data.
    """
    # TODO: Multipliers are for a certain position of jumper J7 and gain of
    # the amplifier.  Need to encode that properly.
    ampl = ampl / 0.8
    step = step / 0.8

    a = np.arange(
            -ampl,
            ampl + step,
            step,
            )
    l = len(a)

    frames = 2 + average

    x, y = np.meshgrid(a, a)

    x, y = (np.repeat(x, 2, axis=0), np.repeat(y, 2, axis=0))
    print(np.shape(x))

    for i in range(l*2):
        x[i] = x[i] if i % 2 == 0 else np.flip(x[i])

    if dry:
        fig, axes = plt.subplots(ncols=2)
        axes[0].imshow(x)
        axes[0].set_title("x")
        axes[1].imshow(y)
        axes[1].set_title("y")
        plt.show()

    x, y = (np.repeat(x, frames), np.repeat(y, frames))

    if dry:
        z = x + y
        z = np.reshape(z, (2*l, l, 2))[:, :, 1]
        v = np.array([z[2*i] for i in range(l)])
        plt.imshow(v)
        plt.show()
        return

    samps = len(x)# // 3
    rate = 1e3 * frames / aq_time_ms
    scan_duration_ms = samps * aq_time_ms

    z = x + y

    trigger_name = "/Dev1/ao/StartTrigger"

    with (
            ni.Task() as ao,
            ni.Task() as ai
            ):

        ao.ao_channels.add_ao_voltage_chan("Dev1/ao0:1")

        ai.ai_channels.add_ai_voltage_chan("Dev1/ai0", terminal_config=TerminalConfiguration.DIFF)

        ai.ai_channels["Dev1/ai0"].ai_rng_high = 1
        ai.ai_channels["Dev1/ai0"].ai_rng_low = -1

        ao.timing.cfg_samp_clk_timing(
            rate,
            sample_mode = AcquisitionType.FINITE,
            samps_per_chan = samps
            )
        #ao.triggers.start_trigger.cfg_time_start_trig(now)

        ai.timing.cfg_samp_clk_timing(
            rate,
            sample_mode = AcquisitionType.FINITE,
            samps_per_chan = samps
            )
        ao.triggers.start_trigger.cfg_dig_edge_start_trig(ai.triggers.start_trigger.term)
        ai.triggers.start_trigger.delay_units = DigitalWidthUnits.SAMPLE_CLOCK_PERIODS
        ai.triggers.start_trigger.delay = 0.5

        ao.write(np.array([x, y]), auto_start=False)
        
        ao.start()
        z = ai.read(samps, timeout = scan_duration_ms / 1e3)
        ao.wait_until_done(timeout = scan_duration_ms / 1e3)

        ao.write([[0], [0]])

    # Each voltage is written thrice.  Only the middle reading can be considered accurate.
    # Hence, we get an array that is l x l x 3, and we choose the middle frame.
    print(np.shape(z))
    if average:
        z = np.reshape(z, (2*l, l, frames))[:, :, 1:]
        z = np.average(z, axis=2)
    else:
        z = np.reshape(z, (2*l, l, frames))[:, :, 1]
    v = np.array([z[2*i] for i in range(l)])
    return v

def generate_sine_wave(
    frequency: float,
    amplitude: float,
    sampling_rate: float,
    number_of_samples: int,
    phase_in: float = 0.0,
):
    """Generates a sine wave with a specified phase.

    Args:
        frequency: Specifies the frequency of the sine wave.
        amplitude: Specifies the amplitude of the sine wave.
        sampling_rate: Specifies the sampling rate of the sine wave.
        number_of_samples: Specifies the number of samples to generate.
        phase_in: Specifies the phase of the sine wave in radians.

    Returns:
        Indicates a tuple containing the generated data and the phase
        of the sine wave after generation.
    """

    ampl = amplitude / 0.8

    duration_time = number_of_samples / sampling_rate
    duration_radians = duration_time * 2 * np.pi
    phase_out = (phase_in + duration_radians) % (2 * np.pi)
    t = np.linspace(phase_in, phase_in + duration_radians, number_of_samples, endpoint=False)

    return (ampl * np.sin(frequency * t), phase_out)

def CleanUp():
    with ni.Task() as ao:
        ao.ao_channels.add_ao_voltage_chan("Dev1/ao0:1")
        ao.write([0, 0])
        ao.wait_until_done()
    return

def MirrorDance(sampling_rate, amplitude, frequency, kill_event, channel):
    # TODO: channel selection input sanitisation.
    with ni.Task() as task:
        number_of_samples = 1000
        task.ao_channels.add_ao_voltage_chan(f"Dev1/ao{channel}")
        task.timing.cfg_samp_clk_timing(sampling_rate, sample_mode=AcquisitionType.CONTINUOUS)

        actual_sampling_rate = task.timing.samp_clk_rate

        data, _ = generate_sine_wave(
            frequency,
            amplitude,
            sampling_rate=actual_sampling_rate,
            number_of_samples=number_of_samples,
        )
        task.write(data)
        task.start()
        
        kill_event.wait()

        task.stop()

def ReadAPD(trx_depth, kill_event, sndr, read_rate_hz):
    with ni.Task() as apd:
        data = np.zeros((2, trx_depth))
        data[0, -1] = 5000
        def callback(task_handle, every_n_samples_event_type, number_of_samples, callback_data):
            """Callback function for reading signals."""
            nonlocal data, sndr
            term_x = data[0, -1]

            xval = np.linspace(term_x + 1 / read_rate_hz, term_x + number_of_samples / read_rate_hz, number_of_samples) # Creates an extension to data[0].
            read = apd.read(number_of_samples_per_channel=number_of_samples)

            data = np.array([xval, read])
            sndr.send(data)
            return 0

        apd.ai_channels.add_ai_voltage_chan("Dev1/ai0", terminal_config=TerminalConfiguration.DIFF)

        apd.timing.cfg_samp_clk_timing(read_rate_hz, sample_mode=AcquisitionType.CONTINUOUS)
        apd.register_every_n_samples_acquired_into_buffer_event(trx_depth, callback)
        apd.start()

        kill_event.wait()
        sndr.close()

        apd.stop()
    return

def AlignAPD(channel='0', frequency=1, amplitude=0.2, step=0.002):
    read_rate_hz = 20
    disp_duration_sec = 6
    trx_depth = 100
    p = 1 / frequency

    disp_points = disp_duration_sec * read_rate_hz
    xlim = disp_duration_sec

    ampl = amplitude / 0.8
    step = step / 0.8

    with (
            ni.Task() as apd,
            ni.Task() as gal,
    ):
        apd.ai_channels.add_ai_voltage_chan("Dev1/ai0", terminal_config=TerminalConfiguration.DIFF)
        gal.ao_channels.add_ao_voltage_chan(f"Dev1/ao{channel}")

        fig, ax = plt.subplots()
        figManager = plt.get_current_fig_manager()
        figManager.full_screen_toggle()

        val = 0
        add = True
        t_zero = monotonic()

        line, = ax.plot([0], [0])

        ax.set_title("Live APD Readout")

        ax.set_xlim(0, xlim)
        ax.set_ylim(0, 1)

        ax.set_xlabel("Time (in seconds)")
        ax.set_ylabel("APD Output (in volts)")

        def update(frame):
            nonlocal line, gal, apd, val, add, t_zero
            t = monotonic() - t_zero

            val = ampl * ( abs( 2 * ( t / p - floor( t / p + 1/2 ) ) ) - 1/2 )

            try:
                gal.write(val)
                volt = apd.read()
            except EOFError:
                plt.close()

            x, y = line.get_data()

            x = np.append(x, [t])
            y = np.append(y, [volt])

            x = x[-round(disp_duration_sec*read_rate_hz*1.5):]
            y = y[-round(disp_duration_sec*read_rate_hz*1.5):]

            line.set_data(x, y)

            """
            bot, top = ax.get_ylim()
            if abs(volt) > top:
                ax.set_ylim(bot, volt + 0.1)
            elif abs(volt) > bot:
                ax.set_ylim(volt - 0.1, top)
            """

            left, right = ax.get_xlim()
            if t > right:
                left  += 1
                right += 1

                ax.set_xlim(left, right)

            return (line, )

        #kill_event = Event()
        #kill_event.clear()

        #read_proc = Process(target=ReadAPD, args=(trx_depth, kill_event, sndr, read_rate_hz))
        #dance_proc = Process(target=MirrorDance, args=(read_rate_hz, amplitude, frequency, kill_event, channel))

        #read_proc.start()
        #dance_proc.start()

        try:
            anne = anim.FuncAnimation(fig=fig, func=update, interval=10, blit=False)
            plt.show()
            #kill_event.set()

            #read_proc.join()
            #dance_proc.join()
        except KeyboardInterrupt:
            #kill_event.set()
            print("Goodbye")
            exit

    return

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", type=str, help="Select mode, scanning or APD alignment.")
    parser.add_argument('-a', "--amplitude", type=float, help="Amplitude of the beam, in degrees.")
    parser.add_argument('-t', "--time_step", type=float, help="Acquisition time for each pixel, in milliseconds.")
    parser.add_argument('-y', "--angl_step", type=float, help="Angular separation between pixels, in degrees.")
    parser.add_argument('-c', "--channel", type=str, help="Channel to align to APD.")
    parser.add_argument('-f', "--frequency", type=float, help="Frequency to vibrate mirror (in Hz).")
    parser.add_argument('-o', "--output", help="Filename to save data.")
    parser.add_argument('-s', "--show", help="Show map when done.", action="store_true")
    parser.add_argument('-v', "--average", type=int, default=0, help="Choose number of frames to average over.")

    args = parser.parse_args()

    try:
        match (args.mode):
            case ('scan'):
                if not ( args.show or (args.output==None) ):
                    #raise RuntimeError("The output will not be shown or saved, and will be forgotten, for ever…\nDon't.")
                    # TODO: Change to error.
                    input("The output will not be shown or saved, and will be forgotten, for ever…\nDon't.")

                z = Scan(args.amplitude, step=args.angl_step, aq_time_ms = args.time_step, average=args.average)
                """
                samps = len(z) // 3
                l = int(np.sqrt(samps))
                z = np.reshape(z, (l, l, 3))[:, :, 1]
                """
                CleanUp()

                # TODO: Axes labelling.
                if args.show:
                    plt.pcolormesh(z)
                    plt.colorbar()
                    plt.gca().set_aspect('equal')
                    plt.show()

                average = args.average + 1

                # TODO: Check validity of file.
                if args.output:
                    np.savetxt(
                            args.output,
                            z,
                            delimiter=",",
                            header=f"Amplitude = {args.amplitude}°,\nAcquisition time = {args.time_step}ms\nAngular Resolution = {args.angl_step}°\nAverage = {average}"
                            )

            case ('align'):
                AlignAPD(args.channel, args.frequency, args.amplitude)
                CleanUp()

            case ('dry'):
                Scan(args.amplitude, step=args.angl_step, dry=True)

    except Exception as E:
        print(E)
        CleanUp()
