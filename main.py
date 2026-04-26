import argparse
from Config import LoadConf
from LaserScanning import Scan, AlignAPD, CleanUp, plt, np

from ctypes import windll

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", type=str, help="Select mode, scanning or APD alignment."
    )
    parser.add_argument(
        "-a", "--amplitude", type=float, help="Amplitude of the beam, in degrees."
    )
    parser.add_argument(
        "-t",
        "--time_step",
        type=float,
        help="Acquisition time for each pixel, in milliseconds.",
    )
    parser.add_argument(
        "-r",
        "--resolution",
        type=int,
        help="Resolution of the scan, in pixels.",
    )
    parser.add_argument("-c", "--channel", type=str, help="Channel to align to APD.")
    parser.add_argument(
        "-f", "--frequency", type=float, help="Frequency to vibrate mirror (in Hz)."
    )
    parser.add_argument("-o", "--output", help="Filename to save data.")
    parser.add_argument("-s", "--show", help="Show map when done.", action="store_true")
    parser.add_argument(
        "-v",
        "--average",
        type=int,
        default=0,
        help="Choose number of frames to average over.",
    )

    args = parser.parse_args()

    conf = LoadConf()

    try:
        match args.mode:
            case "scan":
                if not (args.show or (args.output is None)):
                    # raise RuntimeError("The output will not be shown or saved, and will be forgotten, for ever…\nDon't.")
                    # TODO: Change to error.
                    input(
                        "The output will not be shown or saved, and will be forgotten, for ever…\nDon't."
                    )

                z = Scan(
                    conf,
                    args.amplitude,
                    resolution=args.resolution,
                    aq_time_ms=args.time_step,
                    average=args.average,
                )
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
                    plt.gca().set_aspect("equal")
                    plt.show()

                average = args.average + 1

                # TODO: Check validity of file.
                if args.output:
                    np.savetxt(
                        args.output,
                        z,
                        delimiter=",",
                        header=f"Amplitude = {args.amplitude}°,\nAcquisition time = {args.time_step}ms\nAngular Resolution = {args.resolution}°\nAverage = {average}",
                    )

            case "align":
                AlignAPD(args.channel, args.frequency, args.amplitude)
                CleanUp()

            case "dry":
                Scan(
                    conf,
                    args.amplitude,
                    resolution=args.resolution,
                    dry=True)

    except Exception as E:
        print(E)
        CleanUp()

if __name__ == "__main__":
    windll.shcore.SetProcessDpiAwareness(1)
    main()
