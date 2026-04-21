import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as anim
import nidaqmx as ni
from nidaqmx.constants import AcquisitionType, DigitalWidthUnits, TerminalConfiguration
from time import monotonic
from math import floor


def Scan(
    ampl,
    step=0.2,
    aq_time_ms=0.1,  # time spent on each sample in milliseconds
    dry=False,
    average=0,
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

    for i in range(l * 2):
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
        z = np.reshape(z, (2 * l, l, 2))[:, :, 1]
        v = np.array([z[2 * i] for i in range(l)])
        plt.imshow(v)
        plt.show()
        return

    samps = len(x)  # // 3
    rate = 1e3 * frames / aq_time_ms
    scan_duration_ms = samps * aq_time_ms

    z = x + y

    with ni.Task() as ao, ni.Task() as ai:
        ao.ao_channels.add_ao_voltage_chan("Dev1/ao0:1")

        ai.ai_channels.add_ai_voltage_chan(
            "Dev1/ai0", terminal_config=TerminalConfiguration.DIFF
        )

        ai.ai_channels["Dev1/ai0"].ai_rng_high = 1
        ai.ai_channels["Dev1/ai0"].ai_rng_low = -1

        ao.timing.cfg_samp_clk_timing(
            rate, sample_mode=AcquisitionType.FINITE, samps_per_chan=samps
        )

        ai.timing.cfg_samp_clk_timing(
            rate, sample_mode=AcquisitionType.FINITE, samps_per_chan=samps
        )
        ao.triggers.start_trigger.cfg_dig_edge_start_trig(
            ai.triggers.start_trigger.term
        )
        ai.triggers.start_trigger.delay_units = DigitalWidthUnits.SAMPLE_CLOCK_PERIODS
        ai.triggers.start_trigger.delay = 0.5

        ao.write(np.array([x, y]), auto_start=False)

        ao.start()
        z = ai.read(samps, timeout=scan_duration_ms / 1e3)
        ao.wait_until_done(timeout=scan_duration_ms / 1e3)

        ao.write([[0], [0]])

    # Each voltage is written thrice.  Only the middle reading can be considered accurate.
    # Hence, we get an array that is l x l x 3, and we choose the middle frame.
    print(np.shape(z))
    if average:
        z = np.reshape(z, (2 * l, l, frames))[:, :, 1:]
        z = np.average(z, axis=2)
    else:
        z = np.reshape(z, (2 * l, l, frames))[:, :, 1]
    v = np.array([z[2 * i] for i in range(l)])
    return v


def CleanUp():
    with ni.Task() as ao:
        ao.ao_channels.add_ao_voltage_chan("Dev1/ao0:1")
        ao.write([0, 0])
        ao.wait_until_done()
    return


def AlignAPD(channel="0", frequency=1, amplitude=0.2, step=0.002):
    read_rate_hz = 20
    disp_duration_sec = 6
    period = 1 / frequency

    xlim = disp_duration_sec

    ampl = amplitude / 0.8
    step = step / 0.8

    with (
        ni.Task() as apd,
        ni.Task() as gal,
    ):
        apd.ai_channels.add_ai_voltage_chan(
            "Dev1/ai0", terminal_config=TerminalConfiguration.DIFF
        )
        gal.ao_channels.add_ao_voltage_chan(f"Dev1/ao{channel}")

        fig, ax = plt.subplots()
        figManager = plt.get_current_fig_manager()
        figManager.full_screen_toggle()

        val = 0
        add = True
        t_zero = monotonic()

        (line,) = ax.plot([0], [0])

        ax.set_title("Live APD Readout")

        ax.set_xlim(0, xlim)
        ax.set_ylim(0, 1)

        ax.set_xlabel("Time (in seconds)")
        ax.set_ylabel("APD Output (in volts)")

        def update(frame):
            nonlocal line, gal, apd, val, add, t_zero
            t = monotonic() - t_zero

            val = ampl * (abs(2 * (t / period - floor(t / period + 1 / 2))) - 1 / 2)

            try:
                gal.write(val)
                volt = apd.read()
            except EOFError:
                plt.close()

            x, y = line.get_data()

            x = np.append(x, [t])
            y = np.append(y, [volt])

            x = x[-round(disp_duration_sec * read_rate_hz * 1.5) :]
            y = y[-round(disp_duration_sec * read_rate_hz * 1.5) :]

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
                left += 1
                right += 1

                ax.set_xlim(left, right)

            return (line,)

        try:
            anim.FuncAnimation(fig=fig, func=update, interval=10, blit=False)
            plt.show()
        except KeyboardInterrupt:
            exit

    return
